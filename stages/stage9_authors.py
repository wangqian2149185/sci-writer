import re
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUTPUT = Path(__file__).parent.parent / "output"


def parse_author_input(raw: str) -> list[dict]:
    """
    Parse lines like:
      First Last | Affiliation 1 | Affiliation 2*
    The * after a name or at the end marks corresponding author.
    """
    authors = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        is_corresponding = "*" in line
        line_clean = line.replace("*", "").strip()
        parts = [p.strip() for p in line_clean.split("|")]
        name = parts[0]
        affiliations = parts[1:] if len(parts) > 1 else []
        authors.append({
            "name": name,
            "affiliations": affiliations,
            "corresponding": is_corresponding,
        })
    return authors


def format_author_block(authors: list[dict], corresponding_email: str = "") -> tuple[str, str]:
    """Returns (author_line, affiliation_block)."""
    # Build affiliation index
    aff_index: dict[str, int] = {}
    aff_counter = 1
    for a in authors:
        for aff in a["affiliations"]:
            if aff not in aff_index:
                aff_index[aff] = aff_counter
                aff_counter += 1

    author_parts = []
    for a in authors:
        nums = ",".join(str(aff_index[aff]) for aff in a["affiliations"] if aff in aff_index)
        sup = f"^{nums}^" if nums else ""
        corr = "*" if a["corresponding"] else ""
        author_parts.append(f"{a['name']}{sup}{corr}")

    author_line = ", ".join(author_parts)

    aff_lines = [f"^{num}^ {aff}" for aff, num in sorted(aff_index.items(), key=lambda x: x[1])]
    if corresponding_email:
        corr_authors = [a["name"] for a in authors if a["corresponding"]]
        aff_lines.append(f"*Corresponding author: {', '.join(corr_authors)}. Email: {corresponding_email}")

    return author_line, "\n".join(aff_lines)


def insert_authors_into_doc(filename: str, author_line: str, affiliation_block: str) -> Path:
    doc_path = OUTPUT / filename
    if not doc_path.exists():
        raise FileNotFoundError(f"{filename} not found in output/")

    doc = Document(str(doc_path))

    # Build new author paragraphs
    new_doc = Document()
    style = new_doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    # Copy existing title (first paragraph) if it exists
    existing_paragraphs = list(doc.paragraphs)
    if existing_paragraphs:
        p = new_doc.add_paragraph(existing_paragraphs[0].text)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if existing_paragraphs[0].runs:
            p.runs[0].bold = True

    # Add author line
    auth_para = new_doc.add_paragraph(author_line)
    auth_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    new_doc.add_paragraph(affiliation_block)
    new_doc.add_paragraph()

    # Copy remaining content
    for para in existing_paragraphs[1:]:
        new_doc.add_paragraph(para.text)

    new_doc.save(str(doc_path))
    return doc_path
