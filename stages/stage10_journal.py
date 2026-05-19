from pathlib import Path
from utils.claude_client import chat, chat_with_web_search
from utils.doc_builder import save_references_md, replace_references_section
from utils.writing_standards import WRITING_STANDARDS
import shutil

OUTPUT = Path(__file__).parent.parent / "output"

SYSTEM = (
    "You are a scientific manuscript formatter. Reformat references and verify manuscript structure "
    "to match a specified journal's requirements exactly. "
    "Apply the correct citation style, reference list format, DOI conventions, and abbreviations. "
    "Never alter scientific content during formatting.\n\n"
    + WRITING_STANDARDS
)


def get_journal_requirements(journal_name: str) -> str:
    prompt = (
        f"What are the reference formatting requirements for '{journal_name}'? "
        "Describe: citation style (numbered/author-year), reference list format, "
        "DOI inclusion, journal name abbreviations, and any other key formatting rules. "
        "Be specific with examples."
    )
    result, _ = chat_with_web_search(prompt, system=SYSTEM, max_tokens=2000)
    return result


def reformat_references(references: list[str], journal_name: str, journal_requirements: str) -> list[str]:
    if not references:
        return references

    refs_text = "\n".join(f"{i+1}. {r}" for i, r in enumerate(references))
    prompt = (
        f"Reformat these references according to {journal_name} style:\n\n"
        f"Journal requirements:\n{journal_requirements}\n\n"
        f"References:\n{refs_text}\n\n"
        "Output the reformatted numbered reference list only. "
        "Preserve the original numbering order exactly — do not renumber."
    )

    result = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=4000)

    import re
    new_refs = []
    for line in result.split("\n"):
        clean = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
        if clean:
            new_refs.append(clean)

    # Sync reformatted references back into all manuscript docx files
    for docx_name in ("manuscript_draft.docx", "manuscript_toned.docx"):
        if (OUTPUT / docx_name).exists():
            replace_references_section(docx_name, new_refs)

    save_references_md(new_refs)
    return new_refs


def finalize_manuscript(src_filename: str) -> Path:
    src = OUTPUT / src_filename
    dst = OUTPUT / "manuscript_final.docx"
    if src.exists():
        shutil.copy2(str(src), str(dst))
    return dst
