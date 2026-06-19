from pathlib import Path
from utils.claude_client import chat
from utils.doc_builder import append_section
from utils.entity_registry import audit_and_save, format_entity_constraints
from utils.writing_standards import WRITING_STANDARDS

ROOT = Path(__file__).parent.parent
METHODS_DIR = ROOT / "input" / "methods"

METHODS_STANDARDS = """
MATERIALS AND METHODS SECTION — SPECIFIC RULES (apply in addition to universal writing standards):

PRIMARY QUALITY CRITERION
- Provide sufficient detail that an independent researcher with equivalent expertise could replicate every experiment and analysis exactly as performed. Every procedural step must meet this standard.

MATERIALS SPECIFICATION
- Report all materials with full specificity: manufacturer name, catalog number, concentration, purity grade, lot number (if relevant), and supplier location (city, country).
- Report all instruments with model number and manufacturer.
- Never use vague quantity descriptors. Replace "a small amount," "briefly," "at low temperature," or "standard conditions" with exact numerical values, durations, temperatures, concentrations, and parameter settings.

STATISTICAL METHODS
- Specify all statistical methods completely: the name of each test, the software package and version, sample sizes (n), the α level defining statistical significance, how multiple comparisons were corrected, and how data are expressed (mean ± SD, median [IQR], etc.).

STRUCTURE
- Organize under clearly labeled subheadings matching the logical sequence of the experimental workflow (e.g., "2.1 Study participants," "2.2 Sample collection," "2.3 Analytical procedures," "2.4 Statistical analysis").
- Consolidate repeated procedural steps across multiple conditions into a table rather than restating them in prose.

ETHICS & ALLOCATION
- Include a dedicated paragraph on ethical approvals: name of the institutional review board, approval number, and confirmation of informed written consent (human studies) or institutional animal care compliance.
- Explicitly state how subjects, samples, or experimental units were allocated to groups; whether randomization and blinding were applied; and at which experimental stages.

STRICT PROHIBITIONS
- Do not present, interpret, or discuss results. If an optimization step was performed to determine a parameter, state only the final value chosen — not the optimization outcome.
- Do not justify methodological choices in the methods section; justifications belong in the Discussion.
- Do not cite a prior publication as the sole description of a critical method without providing at least a brief protocol summary, particularly if that publication is not open-access.
- Do not use ambiguous pronouns or implied referents. Every procedural action must have an unambiguous grammatical subject or object.

STYLE
- Write in past tense throughout ("Samples were homogenized at…", "Statistical analyses were performed using…").
- Use passive voice as the default; switch to active only when the agent performing the action is scientifically meaningful.
- Use SI units consistently. Always include a space between the numerical value and the unit (e.g., "37 °C," "15 mL," "2.5 μM").
- Write in a dense, technical style with minimal prose padding. Precise, economical sentences only.
""".strip()

SYSTEM = (
    "You are a scientific manuscript assistant. Write a Materials and Methods section. "
    "Use ONLY the supplied content. Do not invent procedures, reagents, equipment, or conditions. "
    "The section must be written with sufficient detail to allow independent replication.\n\n"
    + WRITING_STANDARDS
    + "\n\n"
    + METHODS_STANDARDS
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
        f"{format_entity_constraints()}\n\n"
        "Requirements:\n"
        "- Use past tense and passive voice\n"
        "- Be precise and reproducible\n"
        "- Organize into logical subsections if needed\n"
        "- Do not add steps, reagents, or procedures not mentioned in the input"
    )

    result = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=4000)
    append_section("manuscript_draft.docx", "Materials and Methods", result)
    audit_and_save(result, label="entity_audit_methods")

    display = "## Materials and Methods (Stage 5)\n\n"
    if warnings:
        display += "\n".join(warnings) + "\n\n"
    display += result

    return result, warnings, display
