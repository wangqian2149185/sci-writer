from utils.claude_client import chat
from utils.doc_builder import set_title

SYSTEM = (
    "You are a scientific manuscript assistant. Generate specific, informative manuscript titles "
    "that match conventions of the scientific field. Avoid vague or overly broad titles."
)


def generate_titles(abstract: str, results_text: str) -> tuple[list[str], str]:
    prompt = (
        f"Generate 7 title suggestions for a scientific manuscript.\n\n"
        f"Abstract:\n{abstract}\n\n"
        f"Key results:\n{results_text[:1000]}\n\n"
        "Requirements for each title:\n"
        "- Specific and informative (not vague)\n"
        "- Matches scientific journal conventions\n"
        "- 10–20 words preferred\n"
        "- May use colons for two-part titles\n\n"
        "Output as a numbered list, one title per line."
    )

    result = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=800)

    import re
    titles = []
    for line in result.split("\n"):
        line = line.strip()
        clean = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
        if clean and len(clean) > 10:
            titles.append(clean)

    display = "## Title Suggestions (Stage 7)\n\n"
    for i, t in enumerate(titles, 1):
        display += f"{i}. {t}\n"
    display += "\nEnter the number of your chosen title, or paste a custom title:"

    return titles, display


def apply_title(title: str, use_toned: bool = False) -> None:
    filename = "manuscript_toned.docx" if use_toned else "manuscript_draft.docx"
    set_title(filename, title)
