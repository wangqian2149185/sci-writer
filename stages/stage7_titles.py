from utils.claude_client import chat
from utils.doc_builder import set_title, append_section
from utils.writing_standards import WRITING_STANDARDS

SYSTEM = (
    "You are a scientific manuscript assistant. Generate specific, informative manuscript titles "
    "that match the conventions of the scientific field. "
    "Each title must be precise, contain the key finding or subject, and avoid vague or overly broad phrasing. "
    "Titles should be 10–20 words. Use a colon for two-part titles when appropriate.\n\n"
    + WRITING_STANDARDS
)

ACKNOWLEDGEMENT_STANDARDS = """
ACKNOWLEDGEMENTS SECTION — SPECIFIC RULES (apply in addition to universal writing standards):

MANDATORY CONTENT
- List all sources of funding with full precision: the full name of the funding agency (not abbreviated), the exact grant number or award identifier, and the name of the principal investigator to whom the grant was awarded.
- Acknowledge specific, meaningful individual contributions that do not meet authorship criteria: technical assistance, reagent provision, data collection support, statistical consultation, animal care, or editing services. State the nature of each contribution explicitly.
- If AI tools were used in manuscript preparation, data analysis, or figure generation, disclose this explicitly and specify how each tool was used.
- If applicable, include a data availability statement with the repository URL and DOI.

STRICT PROHIBITIONS
- Do not credit individuals who meet authorship criteria (substantial contributions to conception, design, data collection, or analysis, AND drafting or critically revising the manuscript, AND final approval) — they must be authors, not acknowledgees.
- Do not use effusive or informal language ("We are deeply indebted to," "Words cannot express our thanks"). Use a professional, straightforward tone.
- Do not include individuals merely for professional seniority, departmental affiliation, or personal relationships. Only genuine intellectual or material contributions to this specific work.
- Do not omit any funding source, even partial or in-kind support. Incomplete funding disclosure is a form of editorial non-compliance.

STYLE
- Structure as a single paragraph with clearly delimited sentences for each category (funding, personal contributions, infrastructure, data availability).
- Keep total length under 150 words.
- Obtain explicit written permission from each named individual before inclusion, as it implies endorsement of the work's content and conclusions.
""".strip()

ACKNOWLEDGEMENT_SYSTEM = (
    "You are a scientific manuscript assistant. Write a concise, professional Acknowledgements section. "
    "Use only the information explicitly provided by the user. Do not invent funding sources, names, or grant numbers.\n\n"
    + WRITING_STANDARDS
    + "\n\n"
    + ACKNOWLEDGEMENT_STANDARDS
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


def generate_acknowledgements(user_info: str) -> str:
    prompt = (
        "Write an Acknowledgements section (under 150 words, single paragraph) "
        "based strictly on the following information provided by the author:\n\n"
        f"{user_info}\n\n"
        "Structure the paragraph with clearly delimited sentences for each category present "
        "(funding, individual contributions, AI tool disclosure, data availability). "
        "Do not invent, assume, or embellish any detail not explicitly stated above."
    )
    result = chat([{"role": "user", "content": prompt}], system=ACKNOWLEDGEMENT_SYSTEM, max_tokens=400)
    append_section("manuscript_draft.docx", "Acknowledgements", result)
    return result


def apply_title(title: str, use_toned: bool = False) -> None:
    filename = "manuscript_toned.docx" if use_toned else "manuscript_draft.docx"
    set_title(filename, title)
