"""
One-off generator for the built-in .cube 3D LUTs shipped with PULSE.

Not imported at runtime — this produces the static .cube files under
app/assets/luts/. Re-run it if you want to regenerate or add LUTs:

    python scripts/generate_luts.py

Each LUT is a genuine 17x17x17 3D lookup table (the common size for
.cube files) computed from simple, explainable per-channel curves, not
placeholders. They're intentionally modest/tasteful rather than
aggressive, since they're meant to demonstrate the pipeline (ffmpeg's
lut3d filter) on real data.
"""
import os

import numpy as np

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "assets", "luts")
SIZE = 17  # grid resolution per axis (17^3 = 4913 entries) — standard for .cube


def write_cube(name: str, title: str, transform):
    """transform(r, g, b) -> (r, g, b), each in [0, 1], vectorized over
    numpy arrays."""
    axis = np.linspace(0.0, 1.0, SIZE)
    r, g, b = np.meshgrid(axis, axis, axis, indexing="ij")

    # .cube files iterate with the RED index fastest, matching the
    # meshgrid axes swapped into (b, g, r) iteration order below.
    r_out, g_out, b_out = transform(r, g, b)
    r_out = np.clip(r_out, 0.0, 1.0)
    g_out = np.clip(g_out, 0.0, 1.0)
    b_out = np.clip(b_out, 0.0, 1.0)

    path = os.path.join(OUT_DIR, f"{name}.cube")
    with open(path, "w") as f:
        f.write(f"TITLE \"{title}\"\n")
        f.write(f"LUT_3D_SIZE {SIZE}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        for bi in range(SIZE):
            for gi in range(SIZE):
                for ri in range(SIZE):
                    f.write(
                        f"{r_out[ri, gi, bi]:.6f} "
                        f"{g_out[ri, gi, bi]:.6f} "
                        f"{b_out[ri, gi, bi]:.6f}\n"
                    )
    print(f"wrote {path}")


def identity(r, g, b):
    return r, g, b


def warm(r, g, b):
    # Lift reds/yellows, gently pull down blue — a classic "golden hour" push.
    return np.clip(r * 1.08 + 0.02, 0, 1), np.clip(g * 1.02, 0, 1), b * 0.90


def cool(r, g, b):
    # Push blue/cyan, pull back red — a clean, slightly clinical look.
    return r * 0.92, np.clip(g * 1.0, 0, 1), np.clip(b * 1.10 + 0.02, 0, 1)


def teal_orange(r, g, b):
    # Shadows toward teal, highlights toward orange — the classic
    # blockbuster grade, implemented as a luminance-weighted split-tone.
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    shadow_w = np.clip(1.0 - luma * 1.4, 0, 1)  # stronger in shadows
    highlight_w = np.clip((luma - 0.4) * 1.6, 0, 1)  # stronger in highlights

    r_out = r + highlight_w * 0.12 - shadow_w * 0.03
    g_out = g + highlight_w * 0.02 + shadow_w * 0.02
    b_out = b - highlight_w * 0.08 + shadow_w * 0.10
    return r_out, g_out, b_out


def high_contrast_bw(r, g, b):
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # S-curve for punch
    contrasted = 0.5 + (luma - 0.5) * 1.35
    contrasted = np.clip(contrasted, 0, 1)
    return contrasted, contrasted, contrasted


def flat_log_look(r, g, b):
    # Lift blacks, compress highlights — a "flat" desaturated look often
    # used as a grading starting point.
    def curve(x):
        return 0.08 + x * 0.84

    return curve(r), curve(g), curve(b)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    write_cube("identity", "Identity (no change)", identity)
    write_cube("warm", "Warm / Golden Hour", warm)
    write_cube("cool", "Cool / Clinical", cool)
    write_cube("teal_orange", "Teal & Orange", teal_orange)
    write_cube("high_contrast_bw", "High Contrast B&W", high_contrast_bw)
    write_cube("flat_log_look", "Flat / Log-ish", flat_log_look)
