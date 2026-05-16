from pathlib import Path
from utils.claude_client import chat
from utils.doc_builder import append_section

ROOT = Path(__file__).parent.parent
METHODS_DIR = ROOT / "input" / "methods"

SYSTEM = (
    "You are a scientific manuscript assistant. Write a Materials and Methods section. "
    "Use ONLY the supplied content. Do not invent procedures, reagents, or equipment. "
    "Use past tense and passive voice. Be precise and reproducible."
)

SANITY_CHECKS = [
    ("kelvin", "Temperature in Kelvin detected — verify if Celsius was intended"),
    ("°k", "Temperature in Kelvin detected — verify if Celsius was intended"),
    ("1000 mg/ml", "Unusually high concentration (1000 mg/mL) — please verify"),
    ("1000mg/ml", "Unusually high concentration (1000 mg/mL) — please verify"),
    ("duplicate", "Possible duplicate step — please verify"),
    ("repeat step", "Possible duplicate step — please verify"),
]


def check_methods_text(text: str) -> list[str]:
    warnings = []
    lower = text.lower()
    for trigger, msg in SANITY_CHECKS:
        if trigger in lower:
            warnings.append(f"⚠️ Possible issue: {msg}. Please verify.")
    return warnings


def generate_methods() -> tuple[str, list[str], str]:
    """Returns (methods_text, warnings, display_text)."""
    method_files = sorted(METHODS_DIR.glob("*.txt"))
    raw_texts = [f.read_text().strip() for f in method_files]
    combined = "\n\n---\n\n".join(raw_texts)

    warnings = check_methods_text(combined)

    prompt = (
        f"Write a Materials and Methods section based ONLY on the following content:\n\n{combined}\n\n"
        "Requirements:\n"
        "- Use past tense and passive voice\n"
        "- Be precise and reproducible\n"
        "- Organize into logical subsections if needed\n"
        "- Do not add steps, reagents, or procedures not mentioned in the input"
    )

    result = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=4000)
    append_section("manuscript_draft.docx", "Materials and Methods", result)

    display = "## Materials and Methods (Stage 5)\n\n"
    if warnings:
        display += "\n".join(warnings) + "\n\n"
    display += result

    return result, warnings, display
