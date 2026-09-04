"""
CampaignPack model.

One row per episode (unique on episode_id — regenerating overwrites the
previous pack rather than accumulating history, since there's no version
UI for it). Holds every artifact generate-campaign produces: Gemini-
written copy (social posts, hooks, press blurb, newsletter, show notes)
plus two deterministically-computed pieces (schedule heat map, trailer
cut list) and two explicitly-labeled AI *estimates* (hype scores, viral
predictions) that are the model's qualitative read of the content, not
measurements of real audience behavior — see
app/services/campaign_service.py for the honesty framing.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.db_compat import JSONB_COMPAT



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CampaignPack(Base):
    __tablename__ = "campaign_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # {platform: {text, hashtags}} for tiktok/youtube/linkedin/x/instagram/facebook
    social_posts: Mapped[dict] = mapped_column(JSONB_COMPAT, nullable=False)

    # [{review_id, text, curiosity_gap_score}]
    hooks: Mapped[list] = mapped_column(JSONB_COMPAT, nullable=False)

    # {generic_best_times: {platform: [...]}, suggested_dates: [{platform, datetime}]}
    schedule: Mapped[dict] = mapped_column(JSONB_COMPAT, nullable=False)

    press_blurb: Mapped[str] = mapped_column(Text, nullable=False)

    # {subject, preview, body}
    newsletter: Mapped[dict] = mapped_column(JSONB_COMPAT, nullable=False)

    show_notes: Mapped[str] = mapped_column(Text, nullable=False)

    # [{review_id, start, end, label}] summing to ~60s
    trailer_cutlist: Mapped[list] = mapped_column(JSONB_COMPAT, nullable=False)

    # [{review_id, score, rationale}] — AI ESTIMATE, see campaign_service
    hype_scores: Mapped[list] = mapped_column(JSONB_COMPAT, nullable=False)

    # [{review_id, platform, label, rationale}] — AI ESTIMATE
    viral_predictions: Mapped[list] = mapped_column(JSONB_COMPAT, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="campaign_pack")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CampaignPack episode_id={self.episode_id}>"
