from pathlib import Path
from utils.claude_client import chat
from utils.doc_builder import save_tone_md, copy_doc

ROOT = Path(__file__).parent.parent
TONE_TEMPLATES_DIR = ROOT / "input" / "tone_templates"
OUTPUT = ROOT / "output"

SYSTEM = (
    "You are a scientific writing style analyst. Analyze writing samples and identify "
    "specific stylistic patterns: sentence length, transition phrases, logic connectors, "
    "hedging language, preferred tense, passive vs. active voice ratio, paragraph structure, "
    "how figures are cited, how conclusions are framed."
)

REWRITE_SYSTEM = (
    "You are a scientific manuscript editor. Rewrite the provided manuscript in the author's "
    "identified tone and style. Preserve ALL scientific content, data, figures references, "
    "and citations exactly. Only change style and phrasing."
)


def extract_text_from_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(path))
            return "\n".join(page.get_text() for page in doc)
        except Exception as e:
            return f"[Could not extract PDF: {e}]"
    elif path.suffix.lower() == ".docx":
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            return f"[Could not extract DOCX: {e}]"
    return path.read_text(errors="ignore")


def analyze_tone() -> str:
    tone_path = OUTPUT / "tone.md"
    if tone_path.exists():
        return tone_path.read_text()

    template_files = list(TONE_TEMPLATES_DIR.glob("*.pdf")) + list(TONE_TEMPLATES_DIR.glob("*.docx"))
    if not template_files:
        return ""

    samples = []
    for f in template_files[:5]:
        text = extract_text_from_file(f)
        samples.append(f"--- Sample from {f.name} ---\n{text[:3000]}")

    combined = "\n\n".join(samples)
    prompt = (
        f"Analyze the writing style of these scientific paper excerpts:\n\n{combined}\n\n"
        "Produce a tone.md document with:\n"
        "1. Sentence length patterns (short/medium/long preference)\n"
        "2. Common transition phrases (with examples)\n"
        "3. Logic connectors used\n"
        "4. Hedging language style\n"
        "5. Tense preference (past/present/mixed)\n"
        "6. Passive vs. active voice ratio\n"
        "7. Paragraph structure pattern\n"
        "8. How figures are cited (e.g., '(Fig. 1)', 'as shown in Figure 1', etc.)\n"
        "9. How conclusions/findings are framed\n"
        "10. Notable vocabulary or phrasing choices\n\n"
        "Include specific examples from the text for each point."
    )

    tone_analysis = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=3000)
    save_tone_md(tone_analysis)
    return tone_analysis


def rewrite_in_tone(tone_analysis: str) -> str:
    draft_path = OUTPUT / "manuscript_draft.docx"
    if not draft_path.exists():
        return "manuscript_draft.docx not found."

    from docx import Document
    doc = Document(str(draft_path))
    draft_text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    prompt = (
        f"Rewrite this manuscript in the author's identified tone and style.\n\n"
        f"Tone/Style Analysis:\n{tone_analysis}\n\n"
        f"Manuscript:\n{draft_text}\n\n"
        "CRITICAL RULES:\n"
        "- Preserve ALL scientific content, data, figure references (Fig. 1, etc.), and citations exactly\n"
        "- Only change style, phrasing, and sentence structure\n"
        "- Match the tone patterns identified in the analysis\n"
        "- Output the full rewritten manuscript"
    )

    result = chat([{"role": "user", "content": prompt}], system=REWRITE_SYSTEM, max_tokens=8192)

    # Save to new docx
    new_doc = Document()
    style = new_doc.styles["Normal"]
    from docx.shared import Pt
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    for para in result.split("\n\n"):
        para = para.strip()
        if para:
            new_doc.add_paragraph(para)

    output_path = OUTPUT / "manuscript_toned.docx"
    new_doc.save(str(output_path))

    return result
