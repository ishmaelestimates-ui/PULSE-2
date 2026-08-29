"""
Color grading endpoints: LUT listing/upload/application, Gemini-suggested
style transfer, and delivery-spec compliance checking.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.color_grade import ColorGrade, ColorGradeSource
from app.models.episode import Episode
from app.models.media_file import MediaFile, MediaType
from app.schemas.color import (
    ApplyLutRequest,
    ColorGradeOut,
    ColorSpecsResponse,
    DeliverySpecsResponse,
    LutOut,
    PlatformSpecCheck,
)
from app.services import color_service, delivery_specs_service, media_service, style_transfer_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["coloring"])


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found.",
        )
    return episode


def _primary_video_file(db: Session, episode_id: int) -> MediaFile:
    media_file = (
        db.query(MediaFile)
        .filter(MediaFile.episode_id == episode_id, MediaFile.media_type == MediaType.VIDEO)
        .order_by(MediaFile.id.desc())
        .first()
    )
    if media_file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Color grading requires an uploaded video file. This episode "
                "has no video media (audio-only episodes have nothing to "
                "color-grade)."
            ),
        )
    return media_file


def _to_color_grade_out(grade: ColorGrade) -> ColorGradeOut:
    out = ColorGradeOut.model_validate(grade)
    out.preview_url = media_service.build_media_url(Path(grade.preview_path))
    if grade.graded_media_path:
        out.graded_media_url = media_service.build_media_url(Path(grade.graded_media_path))
    return out


@router.get("/luts", response_model=list[LutOut])
def list_luts():
    """List built-in and user-uploaded .cube LUTs available for grading."""
    return color_service.list_luts()


@router.post("/luts", response_model=LutOut, status_code=status.HTTP_201_CREATED)
async def upload_lut(name: str, file: UploadFile = File(...)):
    """Upload a custom .cube 3D LUT file, made available under `name`."""
    if not file.filename or not file.filename.lower().endswith(".cube"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .cube 3D LUT files are supported.",
        )
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    color_service.save_uploaded_lut(name, contents)
    return {"name": name, "title": name.replace("_", " ").title(), "builtin": False}


@router.post("/episodes/{episode_id}/apply-lut", response_model=ColorGradeOut)
def apply_lut(episode_id: int, payload: ApplyLutRequest, db: Session = Depends(get_db)):
    """Apply a 3D LUT to the episode's primary video via ffmpeg's lut3d
    filter. By default only a fast single-frame preview is generated;
    pass render_full=true to also render the complete graded video
    (slow — this runs synchronously, there's no background job queue)."""
    _get_episode_or_404(db, episode_id)
    media_file = _primary_video_file(db, episode_id)
    lut_path = color_service.get_lut_path(payload.lut_name)

    source_path = Path(media_file.file_path)
    out_dir = media_service.derived_media_dir(episode_id)
    preview_path = out_dir / f"lut_{payload.lut_name}_preview.jpg"

    frame_path = out_dir / f"frame_for_lut_{payload.lut_name}.jpg"
    color_service.extract_frame(source_path, frame_path)
    color_service.apply_lut(frame_path, lut_path, preview_path, frame_only=True)

    graded_media_path = None
    if payload.render_full:
        graded_media_path = out_dir / f"graded_{payload.lut_name}{source_path.suffix}"
        color_service.apply_lut(source_path, lut_path, graded_media_path, frame_only=False)

    grade = ColorGrade(
        episode_id=episode_id,
        source=ColorGradeSource.LUT,
        lut_name=payload.lut_name,
        preview_path=str(preview_path),
        graded_media_path=str(graded_media_path) if graded_media_path else None,
    )
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return _to_color_grade_out(grade)


@router.post("/episodes/{episode_id}/style-transfer", response_model=ColorGradeOut)
async def style_transfer(
    episode_id: int,
    render_full: bool = False,
    reference_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Gemini compares a reference image against a frame from the
    episode and suggests grading parameters (brightness/contrast/
    saturation/gamma/temperature/tint), which are then applied via
    ffmpeg. This is AI-suggested settings applied by a deterministic
    filter, not literal neural style transfer — see
    app/services/style_transfer_service.py for the full explanation."""
    _get_episode_or_404(db, episode_id)
    media_file = _primary_video_file(db, episode_id)
    source_path = Path(media_file.file_path)
    out_dir = media_service.derived_media_dir(episode_id)

    if not reference_image.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No reference image provided.")
    ref_bytes = await reference_image.read()
    if not ref_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reference image is empty.")

    ref_ext = Path(reference_image.filename).suffix or ".jpg"
    reference_path = out_dir / f"style_ref_{episode_id}{ref_ext}"
    reference_path.write_bytes(ref_bytes)

    frame_path = out_dir / "frame_for_style_transfer.jpg"
    color_service.extract_frame(source_path, frame_path)

    params = style_transfer_service.suggest_grading_params(reference_path, frame_path)

    preview_path = out_dir / "style_transfer_preview.jpg"
    color_service.apply_style_params(frame_path, params, preview_path, frame_only=True)

    graded_media_path = None
    if render_full:
        graded_media_path = out_dir / f"graded_style_transfer{source_path.suffix}"
        color_service.apply_style_params(source_path, params, graded_media_path, frame_only=False)

    grade = ColorGrade(
        episode_id=episode_id,
        source=ColorGradeSource.STYLE_TRANSFER,
        style_transfer_params=params,
        reference_image_path=str(reference_path),
        preview_path=str(preview_path),
        graded_media_path=str(graded_media_path) if graded_media_path else None,
    )
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return _to_color_grade_out(grade)


@router.get("/episodes/{episode_id}/color-specs", response_model=ColorSpecsResponse)
def color_specs(episode_id: int, db: Session = Depends(get_db)):
    """Compliance checklist for Netflix/Amazon/Apple, computed from the
    episode's actual measured media metadata (resolution, frame rate,
    codec, loudness, true peak) — not a static checklist."""
    _get_episode_or_404(db, episode_id)
    media_file = (
        db.query(MediaFile)
        .filter(MediaFile.episode_id == episode_id)
        .order_by(MediaFile.id.desc())
        .first()
    )
    if media_file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No media uploaded for this episode yet.",
        )

    results = delivery_specs_service.check_compliance(media_file.media_metadata or {})
    platforms = [PlatformSpecCheck.model_validate(r) for r in results]
    return ColorSpecsResponse(episode_id=episode_id, platforms=platforms)


@router.get("/episodes/{episode_id}/delivery-specs", response_model=ColorSpecsResponse)
def delivery_specs_alias(episode_id: int, db: Session = Depends(get_db)):
    """Sprint 7 asked for GET .../delivery-specs as a per-episode
    compliance checklist — that's exactly what Night 4's /color-specs
    already does (same Netflix/Amazon/Apple check against real measured
    metadata). Rather than duplicate the logic under a second path, this
    is a thin alias to the same implementation."""
    return color_specs(episode_id, db)


@router.get("/delivery-specs", response_model=DeliverySpecsResponse)
def delivery_specs():
    """Static reference target specs for Netflix/Amazon/Apple delivery
    (simplified baseline — see service docstring for sourcing/caveats)."""
    specs = delivery_specs_service.get_delivery_specs()
    platforms = [
        {
            "platform": s["platform"],
            "resolution": s["resolution"],
            "frame_rates": [str(f) for f in s["frame_rates"]],
            "color_space": s["color_space"],
            "video_codec": s["video_codec"],
            "audio_codec": s["audio_codec"],
            "audio_sample_rate": f"{s['audio_sample_rate']} Hz",
            "loudness_target": (
                f"{s['loudness_target_lkfs']} LKFS ± {s['loudness_tolerance']}"
                if s["loudness_tolerance"] is not None
                else f"≤ {s['loudness_target_lkfs']} LKFS"
            ),
            "true_peak_max": (
                f"≤ {s['true_peak_max_dbtp']} dBTP" if s["true_peak_max_dbtp"] is not None else "not specified"
            ),
            "source": s["source"],
        }
        for s in specs
    ]
    return DeliverySpecsResponse(platforms=platforms)
