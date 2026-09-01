"""
Color grading service.

Two grading paths, both implemented as real FFmpeg operations (not
stubs):

  - LUT application: ffmpeg's `lut3d` filter against a genuine .cube
    3D lookup table (see app/assets/luts/ and scripts/generate_luts.py
    for the built-ins; users can also upload their own .cube files).
  - "Style transfer": NOT literal neural style transfer. Gemini's vision
    model looks at a reference image + a frame from the episode and
    returns suggested grading parameters (brightness/contrast/
    saturation/gamma/temperature/tint) as structured JSON. Those
    parameters are then mechanically applied with ffmpeg's `eq` and
    `colorbalance` filters. This is an honest, inspectable pipeline —
    "AI-suggested settings, applied by a deterministic filter" — not a
    black-box pixel transform.

Also includes a real loudness measurement (ffmpeg's `loudnorm` filter in
single-pass analysis mode) used by the delivery-spec compliance check.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException, status

from app.config import get_settings


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ffmpeg not found on PATH. Install FFmpeg to use color grading.",
        )


def _lut_dirs() -> list[Path]:
    settings = get_settings()
    dirs = [Path(settings.luts_dir), Path(settings.user_luts_dir)]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def list_luts() -> list[dict]:
    """Return every available .cube LUT, built-in and user-uploaded."""
    settings = get_settings()
    builtin_dir = Path(settings.luts_dir).resolve()
    results = []
    for directory in _lut_dirs():
        is_builtin = directory.resolve() == builtin_dir
        for cube_file in sorted(directory.glob("*.cube")):
            title = cube_file.stem.replace("_", " ").title()
            try:
                with open(cube_file) as f:
                    for line in f:
                        if line.strip().upper().startswith("TITLE"):
                            title = line.split('"')[1] if '"' in line else title
                            break
            except OSError:
                pass
            results.append(
                {
                    "name": cube_file.stem,
                    "title": title,
                    "builtin": is_builtin,
                }
            )
    return results


def get_lut_path(name: str) -> Path:
    for directory in _lut_dirs():
        candidate = directory / f"{name}.cube"
        if candidate.exists():
            return candidate
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"LUT '{name}' not found. See GET /api/v1/luts for available names.",
    )


def save_uploaded_lut(name: str, contents: bytes) -> Path:
    settings = get_settings()
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    directory = Path(settings.user_luts_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{safe_name}.cube"
    path.write_bytes(contents)
    return path


def extract_frame(video_path: Path, out_path: Path, at_seconds: float = 1.0) -> Path:
    """Grab a single frame as a JPEG for fast color-grading previews."""
    _require_ffmpeg()
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(at_seconds),
        "-i",
        str(video_path),
        "-vframes",
        "1",
        "-v",
        "error",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not out_path.exists():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ffmpeg failed to extract a preview frame: {result.stderr.decode(errors='replace')[:400]}",
        )
    return out_path


def _run_ffmpeg_filter(
    input_path: Path, output_path: Path, filter_str: str, frame_only: bool
) -> None:
    _require_ffmpeg()
    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-vf", filter_str]
    if frame_only:
        cmd += ["-vframes", "1"]
    else:
        cmd += ["-c:a", "copy"]
    cmd += ["-v", "error", str(output_path)]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ffmpeg filter application failed: {result.stderr.decode(errors='replace')[:500]}",
        )


def apply_lut(
    source_path: Path, lut_path: Path, output_path: Path, frame_only: bool
) -> None:
    # ffmpeg needs escaped colons on Windows-style paths; on POSIX this
    # is a no-op. lut3d expects a path expression, not a URL.
    lut_expr = str(lut_path).replace("\\", "/").replace(":", "\\:")
    _run_ffmpeg_filter(source_path, output_path, f"lut3d='{lut_expr}'", frame_only)


def style_params_to_filter(params: dict) -> str:
    """Translate Gemini's suggested grading parameters into an ffmpeg
    filter expression. Values are expected in these ranges (clamped
    defensively since they come from an LLM, not a trusted client):
      brightness: -1.0..1.0 (eq default 0)
      contrast:    0.0..2.0 (eq default 1)
      saturation:  0.0..3.0 (eq default 1)
      gamma:       0.1..3.0 (eq default 1)
      temperature: -1.0..1.0 (negative=cooler/blue, positive=warmer/orange)
      tint:        -1.0..1.0 (negative=green, positive=magenta)
    """
    def clamp(v, lo, hi, default):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return default
        return max(lo, min(hi, v))

    brightness = clamp(params.get("brightness"), -1.0, 1.0, 0.0)
    contrast = clamp(params.get("contrast"), 0.0, 2.0, 1.0)
    saturation = clamp(params.get("saturation"), 0.0, 3.0, 1.0)
    gamma = clamp(params.get("gamma"), 0.1, 3.0, 1.0)
    temperature = clamp(params.get("temperature"), -1.0, 1.0, 0.0)
    tint = clamp(params.get("tint"), -1.0, 1.0, 0.0)

    eq = f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}:gamma={gamma}"

    # colorbalance takes shadows/midtones/highlights red-cyan shifts
    # (rs/rm/rh), green-magenta (gs/gm/gh), blue-yellow (bs/bm/bh), each
    # roughly -1..1. Apply temperature/tint uniformly across midtones.
    rm = temperature * 0.3
    bm = -temperature * 0.3
    gm = -tint * 0.2
    colorbalance = f"colorbalance=rm={rm}:gm={gm}:bm={bm}"

    return f"{eq},{colorbalance}"


def apply_style_params(
    source_path: Path, params: dict, output_path: Path, frame_only: bool
) -> None:
    filter_str = style_params_to_filter(params)
    _run_ffmpeg_filter(source_path, output_path, filter_str, frame_only)


def measure_loudness(audio_path: Path) -> dict:
    """Single-pass loudness analysis via ffmpeg's loudnorm filter.
    Returns integrated loudness (LUFS), true peak (dBTP), and loudness
    range (LU) as measured — real numbers from the actual audio, not
    estimates."""
    _require_ffmpeg()
    cmd = [
        "ffmpeg",
        "-i",
        str(audio_path),
        "-af",
        "loudnorm=print_format=json",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True)
    stderr = result.stderr.decode(errors="replace")

    # loudnorm prints a JSON block near the end of stderr output.
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, re.S)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ffmpeg loudnorm analysis did not return measurements.",
        )
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to parse ffmpeg loudnorm output.",
        ) from exc

    return {
        "integrated_lufs": float(data.get("input_i", 0.0)),
        "true_peak_dbtp": float(data.get("input_tp", 0.0)),
        "loudness_range_lu": float(data.get("input_lra", 0.0)),
    }
