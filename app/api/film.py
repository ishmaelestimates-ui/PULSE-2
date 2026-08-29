"""
Film feature endpoints. See app/services/film_service.py for the honesty
framing on acts/festivals/trailer cuts/sync licensing.
"""
import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.campaign import CampaignPack
from app.models.editorial_review import EditorialReview, ReviewStatus
from app.models.episode import Episode
from app.models.film import FestivalMatch, FilmAct, TerritoryRelease, TrailerCut
from app.schemas.film import (
    ActsResponse,
    ExportTrailerRequest,
    FestivalMatchesResponse,
    FestivalMatchOut,
    FestivalMatchUpdate,
    FestivalSubmissionResponse,
    SyncLicensingReportResponse,
    TerritoryReleaseCreate,
    TerritoryReleaseOut,
    TerritoryScheduleResponse,
    TrailerCutListResponse,
    TrailerCutOut,
)
from app.services import film_service

router = APIRouter(prefix="/api/v1/episodes", tags=["film"])

SCENE_COLOR = {"Action": "Red", "Dialogue": "Blue", "Emotional": "Green", "Climax": "Yellow"}
DEFAULT_TERRITORIES = ["US", "UK", "EU", "Canada", "Australia", "Other"]


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Episode {episode_id} not found.")
    return episode


def _require_transcript(episode: Episode):
    if not episode.transcript or not episode.transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Episode has no transcript yet — transcribe it before using film features.",
        )


def _seconds_to_timecode(total_seconds: float, frame_rate: float) -> str:
    if total_seconds < 0:
        total_seconds = 0.0
    total_frames = round(total_seconds * frame_rate)
    frames_per_hour = round(frame_rate * 3600)
    frames_per_minute = round(frame_rate * 60)
    frame_rate_int = round(frame_rate)
    hours, remainder = divmod(total_frames, frames_per_hour)
    minutes, remainder = divmod(remainder, frames_per_minute)
    seconds, frames = divmod(remainder, frame_rate_int)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


@router.get("/{episode_id}/acts", response_model=ActsResponse)
def get_acts(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    _require_transcript(episode)

    acts_data = film_service.detect_acts(episode.transcript)

    db.query(FilmAct).filter(FilmAct.episode_id == episode_id).delete()
    acts = []
    for a in acts_data:
        act = FilmAct(
            episode_id=episode_id,
            act_number=a["act_number"],
            title=a["title"],
            start_time=a["start_time"],
            end_time=a["end_time"],
            description=a["description"],
            confidence=a["confidence"],
        )
        db.add(act)
        acts.append(act)
    db.commit()
    for a in acts:
        db.refresh(a)

    return ActsResponse(episode_id=episode_id, acts=acts)


@router.get("/{episode_id}/trailer-cut-list", response_model=TrailerCutListResponse)
def get_trailer_cut_list(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)

    accepted_reviews = (
        db.query(EditorialReview)
        .filter(EditorialReview.episode_id == episode_id, EditorialReview.status == ReviewStatus.ACCEPTED)
        .all()
    )
    if not accepted_reviews:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No accepted strong moments or clips yet — accept some in the Review tab first.",
        )

    campaign = db.query(CampaignPack).filter(CampaignPack.episode_id == episode_id).first()
    hype_map = {h["review_id"]: h for h in (campaign.hype_scores if campaign else [])}

    db.query(TrailerCut).filter(TrailerCut.episode_id == episode_id).delete()

    all_labels = []
    cuts_by_version: dict[int, list[dict]] = {}
    for version in (30, 60, 90):
        clips = film_service.build_trailer_cut(accepted_reviews, hype_map, target_seconds=version)
        cuts_by_version[version] = clips
        all_labels.extend(c["label"] for c in clips)

    # One batched Gemini call for scene-type tone labels across every
    # clip in every version (duplicates across versions are fine — cheap
    # and simpler than de-duplicating).
    scene_types = film_service.classify_scene_types(all_labels)
    label_iter = iter(scene_types)

    result: dict[str, list[TrailerCutOut]] = {}
    for version, clips in cuts_by_version.items():
        rows = []
        for i, clip in enumerate(clips):
            scene_type = next(label_iter, "Dialogue")
            cut = TrailerCut(
                episode_id=episode_id,
                version=version,
                clip_order=i,
                start_time=clip["start"],
                end_time=clip["end"],
                description=clip["label"],
                scene_type=scene_type,
                review_id=clip["review_id"],
            )
            db.add(cut)
            rows.append(cut)
        result[str(version)] = rows

    db.commit()
    for rows in result.values():
        for r in rows:
            db.refresh(r)

    return TrailerCutListResponse(episode_id=episode_id, cuts=result)


@router.post("/{episode_id}/export-trailer")
def export_trailer(episode_id: int, payload: ExportTrailerRequest, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    if payload.version not in (30, 60, 90):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version must be 30, 60, or 90.")

    cuts = (
        db.query(TrailerCut)
        .filter(TrailerCut.episode_id == episode_id, TrailerCut.version == payload.version)
        .order_by(TrailerCut.clip_order)
        .all()
    )
    if not cuts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {payload.version}s trailer cut list generated yet. Run GET .../trailer-cut-list first.",
        )

    settings = get_settings()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Start TC", "End TC", "Name", "Note", "Color"])
    for cut in cuts:
        writer.writerow(
            [
                _seconds_to_timecode(cut.start_time, settings.resolve_frame_rate),
                _seconds_to_timecode(cut.end_time, settings.resolve_frame_rate),
                f"Trailer {payload.version}s — {cut.scene_type}",
                cut.description,
                SCENE_COLOR.get(cut.scene_type, "Blue"),
            ]
        )
    buffer.seek(0)
    filename = f"episode_{episode_id}_trailer_{payload.version}s.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{episode_id}/festival-matches", response_model=FestivalMatchesResponse)
def get_festival_matches(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    _require_transcript(episode)

    suggestions = film_service.suggest_festivals(episode.title, episode.transcript)

    # Preserve anything the user has already started tracking/verifying;
    # only clear out never-touched suggestions before adding fresh ones.
    db.query(FestivalMatch).filter(
        FestivalMatch.episode_id == episode_id, FestivalMatch.verified.is_(False), FestivalMatch.status == "suggested"
    ).delete(synchronize_session=False)

    matches = []
    for s in suggestions:
        deadline = None  # deliberately not parsed from the fuzzy "deadline_guess" text — see note below
        match = FestivalMatch(
            episode_id=episode_id,
            festival_name=s.get("festival_name", "Unknown"),
            tier=s.get("tier", 3),
            why_relevant=s.get("why_relevant"),
            deadline=deadline,
            entry_fee=s.get("entry_fee_guess"),
            notes=s.get("deadline_guess"),  # fuzzy guess stored as a note, not a real date field
        )
        db.add(match)
        matches.append(match)

    db.commit()
    for m in matches:
        db.refresh(m)

    all_matches = db.query(FestivalMatch).filter(FestivalMatch.episode_id == episode_id).all()
    return FestivalMatchesResponse(episode_id=episode_id, matches=all_matches)


@router.patch("/{episode_id}/festival-matches/{match_id}", response_model=FestivalMatchOut)
def update_festival_match(episode_id: int, match_id: int, payload: FestivalMatchUpdate, db: Session = Depends(get_db)):
    match = db.query(FestivalMatch).filter(FestivalMatch.id == match_id, FestivalMatch.episode_id == episode_id).first()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival match not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(match, field, value)
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.post("/{episode_id}/festival-submission", response_model=FestivalSubmissionResponse)
def generate_festival_submission(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    _require_transcript(episode)
    content = film_service.generate_festival_submission(episode.title, episode.transcript)
    try:
        return FestivalSubmissionResponse(
            episode_id=episode_id,
            logline=content["logline"],
            synopsis=content["synopsis"],
            directors_statement=content["directors_statement"],
            key_art_brief=content["key_art_brief"],
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini response was missing an expected field: {exc}"
        ) from exc


@router.get("/{episode_id}/territory-schedule", response_model=TerritoryScheduleResponse)
def get_territory_schedule(episode_id: int, db: Session = Depends(get_db)):
    """Generates a default staggered planning schedule the first time
    it's called (if none exists), otherwise returns what's tracked."""
    _get_episode_or_404(db, episode_id)
    existing = db.query(TerritoryRelease).filter(TerritoryRelease.episode_id == episode_id).all()
    if not existing:
        today = date.today()
        for i, territory in enumerate(DEFAULT_TERRITORIES):
            db.add(TerritoryRelease(episode_id=episode_id, territory=territory, release_date=today + timedelta(days=i * 7)))
        db.commit()
        existing = db.query(TerritoryRelease).filter(TerritoryRelease.episode_id == episode_id).all()
    return TerritoryScheduleResponse(episode_id=episode_id, releases=existing)


@router.post("/{episode_id}/territory-schedule", response_model=TerritoryReleaseOut, status_code=status.HTTP_201_CREATED)
def add_territory_release(episode_id: int, payload: TerritoryReleaseCreate, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    release = TerritoryRelease(episode_id=episode_id, **payload.model_dump())
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


@router.get("/{episode_id}/sync-licensing-report", response_model=SyncLicensingReportResponse)
def sync_licensing_report(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    _require_transcript(episode)
    flags = film_service.scan_sync_licensing(episode.transcript)
    return SyncLicensingReportResponse(
        episode_id=episode_id,
        flags=[{**f, "timestamp": None} for f in flags],
    )
