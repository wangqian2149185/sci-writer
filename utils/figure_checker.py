from pathlib import Path
from PIL import Image

FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".gif", ".bmp", ".webp"}


def get_figure_files(figures_dir: Path) -> list[Path]:
    return sorted([f for f in figures_dir.iterdir() if f.suffix.lower() in FIGURE_EXTS])


def get_caption_files(captions_dir: Path) -> list[Path]:
    return sorted([f for f in captions_dir.iterdir() if f.suffix.lower() == ".txt"])


def check_figure_caption_match(figures_dir: Path, captions_dir: Path) -> tuple[list[str], list[str]]:
    """Returns (warnings, errors). Errors block progress; warnings do not."""
    figures = {f.stem.lower(): f for f in get_figure_files(figures_dir)}
    captions = {f.stem.lower(): f for f in get_caption_files(captions_dir)}

    errors = []
    for stem, fig in figures.items():
        if stem not in captions:
            errors.append(f"Figure `{fig.name}` has no matching caption file `{fig.stem}.txt`")
    for stem, cap in captions.items():
        if stem not in figures:
            errors.append(f"Caption `{cap.name}` has no matching figure file")

    return errors


def check_figure_sizes(figures_dir: Path) -> list[str]:
    warnings = []
    for fig_path in get_figure_files(figures_dir):
        if fig_path.suffix.lower() == ".svg":
            continue  # SVG is vector; skip pixel checks
        try:
            with Image.open(fig_path) as img:
                dpi = img.info.get("dpi", (96, 96))
                if isinstance(dpi, (int, float)):
                    dpi = (dpi, dpi)
                dpi_x = dpi[0] if dpi[0] > 0 else 96
                dpi_y = dpi[1] if dpi[1] > 0 else 96
                w_in = img.width / dpi_x
                h_in = img.height / dpi_y

                if w_in > 7:
                    warnings.append(f"`{fig_path.name}`: TOO WIDE ({w_in:.1f} in). Shrinking may make fonts too small.")
                if w_in < 3.2:
                    warnings.append(f"`{fig_path.name}`: TOO NARROW ({w_in:.1f} in). Stretching may make fonts too large.")
                if h_in > 7:
                    warnings.append(f"`{fig_path.name}`: TOO TALL ({h_in:.1f} in).")
        except Exception as e:
            warnings.append(f"`{fig_path.name}`: Could not read image ({e})")
    return warnings


def encode_image_base64(path: Path) -> tuple[str, str]:
    """Returns (base64_data, media_type)."""
    import base64
    suffix = path.suffix.lower()
    media_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".tif": "image/tiff", ".tiff": "image/tiff",
    }
    media_type = media_map.get(suffix, "image/png")
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type
