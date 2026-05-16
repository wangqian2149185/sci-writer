from pathlib import Path
from utils.claude_client import chat
from utils.doc_builder import append_section, save_references_md
from docx import Document

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "output"

SYSTEM = (
    "You are a scientific manuscript assistant. Write a formal Discussion section. "
    "Connect results with published literature. Be objective, cite evidence, and use formal scientific language. "
    "Do not invent citations. Only cite sources provided in the literature bullets."
)


def generate_discussion(
    results_text: str,
    intro_text: str,
    selected_bullets: list[str],
    references: list[str],
    merge: bool = False,
) -> tuple[str, list[str]]:
    bullets_text = "\n".join(f"{i+1}. {b}" for i, b in enumerate(selected_bullets))

    prompt = (
        f"Write a Discussion section for a scientific manuscript.\n\n"
        f"Results:\n{results_text[:2000]}\n\n"
        f"Introduction context:\n{intro_text[:1000]}\n\n"
        f"Available literature (cite using superscript numbers):\n{bullets_text}\n\n"
        "The Discussion must include:\n"
        "1. What the results + published reports together indicate\n"
        "2. The significance/benefit of this study for the field\n"
        "3. A narrative connecting what the manuscript did\n"
        "4. Highlight the key discovery and why it warrants further study\n"
        "5. Known limitations or areas needing more work\n"
        "6. Suggested next steps / future directions\n\n"
        "Use superscript numbers for citations. Only cite sources from the bullets above."
    )

    result = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=5000)

    if merge:
        # Read current draft and replace Results + add Results & Discussion merged
        draft_path = OUTPUT / "manuscript_draft.docx"
        if draft_path.exists():
            import shutil
            shutil.copy2(str(draft_path), str(OUTPUT / "manuscript_draft_backup.docx"))

        # Append merged section
        merged_text = f"[Results portion]\n\n{results_text}\n\n[Discussion portion]\n\n{result}"
        append_section("manuscript_draft.docx", "Results and Discussion", merged_text)
    else:
        append_section("manuscript_draft.docx", "Discussion", result)

    # Add any new citations to references
    import re
    new_refs = []
    for line in result.split("\n"):
        m = re.search(r"\(([^)]+\d{4}[^)]*)\)", line)
        if m:
            new_refs.append(m.group(1))

    return result, references
