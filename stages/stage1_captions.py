from pathlib import Path
from utils.figure_checker import get_figure_files, encode_image_base64
from utils.claude_client import chat_with_vision
from utils.doc_builder import write_captions_doc
from utils.entity_registry import audit_and_save, format_entity_constraints
from utils.writing_standards import WRITING_STANDARDS

ROOT = Path(__file__).parent.parent
FIGURES_DIR = ROOT / "input" / "figures"
CAPTIONS_DIR = ROOT / "input" / "captions"

SYSTEM = (
    "You are a scientific manuscript assistant specializing in figure captions. "
    "Write professional, journal-style figure captions. "
    "Base your caption ONLY on the image content and the user-supplied caption text. "
    "Never invent data, values, or interpretations not visible in the image or stated in the caption text.\n\n"
    + WRITING_STANDARDS
)


def generate_captions(figure_order: list[str] | None = None) -> tuple[list[tuple[int, str]], str]:
    """
    Returns (captions_list, display_text).
    captions_list: [(fig_num, caption_text), ...]
    """
    figs = get_figure_files(FIGURES_DIR)
    if figure_order:
        stem_to_fig = {f.stem.lower(): f for f in figs}
        ordered = [stem_to_fig[s.lower()] for s in figure_order if s.lower() in stem_to_fig]
        # Append any not in user order
        ordered_stems = {s.lower() for s in figure_order}
        for f in figs:
            if f.stem.lower() not in ordered_stems:
                ordered.append(f)
        figs = ordered

    captions = []
    for i, fig_path in enumerate(figs, 1):
        caption_path = CAPTIONS_DIR / (fig_path.stem + ".txt")
        raw_caption = caption_path.read_text().strip() if caption_path.exists() else ""

        # Skip SVG — Claude Vision can't handle them
        if fig_path.suffix.lower() == ".svg":
            prompt = (
                f"The following is an SVG figure (vector format, cannot be displayed as image). "
                f"{format_entity_constraints()}\n\n"
                f"User-supplied caption text: {raw_caption}\n\n"
                f"Write a professional, journal-style figure caption for Figure {i} based ONLY on the supplied caption text."
            )
            from utils.claude_client import chat
            result = chat(
                [{"role": "user", "content": prompt}],
                system=SYSTEM,
                max_tokens=512,
            )
        else:
            b64, mtype = encode_image_base64(fig_path)
            prompt = (
                f"{format_entity_constraints()}\n\n"
                f"User-supplied caption text for Figure {i}: {raw_caption}\n\n"
                f"Write a professional, journal-style figure caption based ONLY on what you see in this image "
                f"and the supplied caption text. Do not invent data or interpretations."
            )
            result = chat_with_vision(prompt, [(b64, mtype)], system=SYSTEM, max_tokens=512)

        captions.append((i, result.strip()))

    # Save to docx
    write_captions_doc(captions)
    audit_and_save("\n\n".join(text for _, text in captions), label="entity_audit_captions")

    # Build display text
    display_lines = ["## Figure Captions (Stage 1)\n"]
    for num, text in captions:
        display_lines.append(f"**Figure {num}.** {text}\n")

    return captions, "\n".join(display_lines)
