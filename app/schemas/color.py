"""
Pydantic schemas for color grading, delivery-spec compliance, and brand
settings.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.color_grade import ColorGradeSource


class LutOut(BaseModel):
    name: str
    title: str
    builtin: bool


class ApplyLutRequest(BaseModel):
    lut_name: str
    render_full: bool = Field(
        default=False,
        description=(
            "If true, renders the full video (slow, synchronous — no job "
            "queue yet). If false (default), only a fast single-frame "
            "preview is generated."
        ),
    )


class ColorGradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    source: ColorGradeSource
    lut_name: Optional[str] = None
    style_transfer_params: Optional[dict[str, Any]] = None
    preview_url: Optional[str] = None
    graded_media_url: Optional[str] = None
    applied_at: datetime


class SpecCheckItem(BaseModel):
    label: str
    target: str
    actual: Optional[str] = None
    status: str  # "pass" | "fail" | "unknown"


class PlatformSpecCheck(BaseModel):
    platform: str
    checks: list[SpecCheckItem]


class ColorSpecsResponse(BaseModel):
    episode_id: int
    platforms: list[PlatformSpecCheck]
    note: str = (
        "Baseline reference figures compiled from each platform's publicly "
        "documented delivery guides as of mid-2026. These are simplified "
        "checkpoints for a rough go/no-go read, not the full official "
        "delivery specification (which covers IMF packaging, captions, "
        "metadata, and more). Confirm against the platform's current "
        "partner documentation before actual delivery."
    )


class DeliveryPlatformSpec(BaseModel):
    platform: str
    resolution: list[str]
    frame_rates: list[str]
    color_space: list[str]
    video_codec: list[str]
    audio_codec: list[str]
    audio_sample_rate: str
    loudness_target: str
    true_peak_max: str
    source: str


class DeliverySpecsResponse(BaseModel):
    platforms: list[DeliveryPlatformSpec]
    note: str = (
        "Reference only — simplified from public delivery guides. Always "
        "confirm against the platform's current official documentation "
        "before final delivery."
    )


class BrandSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    primary_color: str
    secondary_color: str
    tertiary_color: Optional[str] = None
    font: str
    logo_url: Optional[str] = None
    intro_music_url: Optional[str] = None
    outro_music_url: Optional[str] = None
    updated_at: datetime


class BrandSettingsUpdate(BaseModel):
    primary_color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    tertiary_color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    font: Optional[str] = None
