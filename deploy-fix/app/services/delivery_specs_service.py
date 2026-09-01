"""
Delivery-spec reference data + compliance checking.

The reference figures below are simplified baselines compiled from each
platform's publicly published delivery guides (Netflix Partner Help
Center, Amazon Prime Video / Video Central delivery requirements, and
Apple's Video and Audio Asset Guide) as of mid-2026. Full official specs
run to dozens of pages (IMF packaging, captions, metadata schemas,
territory-specific requirements, etc.) — this is a rough go/no-go
checkpoint, not a substitute for the platform's current partner
documentation, which every one of these sources explicitly says to
consult before actual delivery.

The compliance check (`check_compliance`) compares these targets against
REAL measured data from the episode's primary media file: resolution,
frame rate, and codec from ffprobe (see media_service.probe_metadata),
and integrated loudness / true peak from ffmpeg's loudnorm analysis (see
color_service.measure_loudness). Where PULSE doesn't measure something
(e.g. bit depth, HDR metadata), the check reports "unknown" rather than
guessing.
"""
import re

PLATFORM_SPECS = [
    {
        "platform": "Netflix",
        "resolution": ["1920x1080", "3840x2160"],
        "frame_rates": [23.976, 24, 25, 29.97, 59.94],
        "color_space": ["Rec.709 (HD)", "Rec.2020 (UHD)"],
        "video_codec": ["prores", "jpeg2000"],
        "audio_codec": ["pcm_s16le", "pcm_s24le"],
        "audio_sample_rate": 48000,
        "loudness_target_lkfs": -24.0,
        "loudness_tolerance": 2.0,
        "true_peak_max_dbtp": None,  # not clearly published in baseline sources
        "source": "Netflix Partner Help Center delivery guides",
    },
    {
        "platform": "Amazon Prime Video",
        "resolution": ["1280x720", "3840x2160", "1920x1080"],
        "frame_rates": [23.976, 24, 25, 29.97, 59.94],
        "color_space": ["Rec.709 (HD)", "Rec.2020 (UHD)"],
        "video_codec": ["prores", "h264", "hevc"],
        "audio_codec": ["pcm_s16le", "pcm_s24le", "aac", "ac3", "eac3"],
        "audio_sample_rate": 48000,
        "loudness_target_lkfs": -24.0,
        "loudness_tolerance": 2.0,
        "true_peak_max_dbtp": -2.0,
        "source": "Amazon Prime Video / Video Central delivery requirements",
    },
    {
        "platform": "Apple (TV+ / Video Partner Program)",
        "resolution": ["1920x1080", "3840x2160"],
        "frame_rates": [23.976, 24, 25, 29.97, 59.94],
        "color_space": ["Rec.709 (HD)", "Rec.2020 / P3 (UHD)"],
        "video_codec": ["prores"],
        "audio_codec": ["pcm_s16le", "pcm_s24le"],
        "audio_sample_rate": 48000,
        "loudness_target_lkfs": -18.0,
        "loudness_tolerance": None,  # spec is a ceiling ("should not exceed"), not a ±range
        "true_peak_max_dbtp": -1.0,
        "source": "Apple Video and Audio Asset Guide (help.apple.com)",
    },
]


def get_delivery_specs() -> list[dict]:
    return PLATFORM_SPECS


def _check_resolution(actual: str | None, targets: list[str]) -> dict:
    if not actual:
        return {"actual": None, "status": "unknown"}
    return {"actual": actual, "status": "pass" if actual in targets else "fail"}


def _check_frame_rate(actual: float | None, targets: list[float]) -> dict:
    if actual is None:
        return {"actual": None, "status": "unknown"}
    ok = any(abs(actual - t) < 0.05 for t in targets)
    return {"actual": f"{actual:.3f}", "status": "pass" if ok else "fail"}


def _check_codec(actual: str | None, targets: list[str]) -> dict:
    if not actual:
        return {"actual": None, "status": "unknown"}
    normalized = actual.lower()
    ok = any(t in normalized or normalized in t for t in targets)
    return {"actual": actual, "status": "pass" if ok else "fail"}


def _check_sample_rate(actual, target: int) -> dict:
    if not actual:
        return {"actual": None, "status": "unknown"}
    try:
        actual_int = int(actual)
    except (TypeError, ValueError):
        return {"actual": str(actual), "status": "unknown"}
    return {"actual": f"{actual_int} Hz", "status": "pass" if actual_int == target else "fail"}


def _check_loudness(actual_lufs: float | None, target: float, tolerance: float | None) -> dict:
    if actual_lufs is None:
        return {"actual": None, "status": "unknown"}
    if tolerance is not None:
        ok = abs(actual_lufs - target) <= tolerance
    else:
        # ceiling spec (e.g. Apple: "should not exceed")
        ok = actual_lufs <= target
    return {"actual": f"{actual_lufs:.1f} LUFS", "status": "pass" if ok else "fail"}


def _check_true_peak(actual_dbtp: float | None, target: float | None) -> dict:
    if target is None:
        return {"actual": f"{actual_dbtp:.1f} dBTP" if actual_dbtp is not None else None, "status": "unknown"}
    if actual_dbtp is None:
        return {"actual": None, "status": "unknown"}
    return {"actual": f"{actual_dbtp:.1f} dBTP", "status": "pass" if actual_dbtp <= target else "fail"}


def check_compliance(media_metadata: dict) -> list[dict]:
    """Build a pass/fail checklist per platform from a MediaFile's
    media_metadata (ffprobe fields + loudnorm measurements, if present)."""
    resolution = media_metadata.get("resolution")
    frame_rate = media_metadata.get("frame_rate")
    video_codec = media_metadata.get("video_codec")
    sample_rate = media_metadata.get("sample_rate")
    integrated_lufs = media_metadata.get("integrated_lufs")
    true_peak_dbtp = media_metadata.get("true_peak_dbtp")

    results = []
    for spec in PLATFORM_SPECS:
        res_check = _check_resolution(resolution, spec["resolution"])
        fps_check = _check_frame_rate(frame_rate, spec["frame_rates"])
        codec_check = _check_codec(video_codec, spec["video_codec"])
        rate_check = _check_sample_rate(sample_rate, spec["audio_sample_rate"])
        loud_check = _check_loudness(
            integrated_lufs, spec["loudness_target_lkfs"], spec["loudness_tolerance"]
        )
        peak_check = _check_true_peak(true_peak_dbtp, spec["true_peak_max_dbtp"])

        checks = [
            {
                "label": "Resolution",
                "target": " or ".join(spec["resolution"]),
                **res_check,
            },
            {
                "label": "Frame rate",
                "target": " / ".join(str(f) for f in spec["frame_rates"]),
                **fps_check,
            },
            {
                "label": "Video codec",
                "target": " / ".join(spec["video_codec"]),
                **codec_check,
            },
            {
                "label": "Audio sample rate",
                "target": f"{spec['audio_sample_rate']} Hz",
                **rate_check,
            },
            {
                "label": "Integrated loudness",
                "target": (
                    f"{spec['loudness_target_lkfs']} LKFS ± {spec['loudness_tolerance']}"
                    if spec["loudness_tolerance"] is not None
                    else f"≤ {spec['loudness_target_lkfs']} LKFS"
                ),
                **loud_check,
            },
            {
                "label": "True peak",
                "target": (
                    f"≤ {spec['true_peak_max_dbtp']} dBTP"
                    if spec["true_peak_max_dbtp"] is not None
                    else "not specified in baseline reference"
                ),
                **peak_check,
            },
        ]
        results.append({"platform": spec["platform"], "checks": checks})

    return results
