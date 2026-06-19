from pathlib import Path
from utils.claude_client import chat
from utils.doc_builder import append_section
from utils.entity_registry import audit_and_save, format_entity_constraints
from utils.writing_standards import WRITING_STANDARDS

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "input" / "results"
CAPTIONS_DIR = ROOT / "input" / "captions"

RESULTS_STANDARDS = """
RESULTS SECTION — SPECIFIC RULES (apply in addition to universal writing standards):

NARRATIVE STRUCTURE
- Present results in a logical sequence: begin with descriptive or characterization data, progress through hypothesis-testing or comparative analyses, and end with the most compelling or complex findings that directly answer the research question.
- Begin each paragraph or subsection with a topic sentence stating what the analysis was designed to test or determine, before presenting the outcome.
- Use transition sentences between subsections to signal logical progression (e.g., "Having established that X occurred under condition A, we next examined whether this effect persisted under condition B").
- Use clear, informative subheadings corresponding to distinct research questions or experimental phases (e.g., "3.2 CD4+ T cell proliferation is enhanced by treatment X"), not generic labels (e.g., "3.2 T cell data").

QUANTITATIVE PRECISION
- Report all results with full quantitative precision: effect sizes, confidence intervals, p-values, sample sizes, and units.
- Never describe a finding as merely "significant" — always provide the test statistic, degrees of freedom, and exact p-value.
- Report negative, null, and unexpected results with the same rigor and completeness as positive findings. Selective reporting is a form of research misconduct.

FIGURES AND TABLES
- Design figures and tables as the primary vehicle for complex data. Prose should direct attention to the most important patterns, not duplicate information already visible in figures.
- Use phrases such as "As shown in Figure 2A…" or "Table 1 summarizes…" to direct the reader.
- Do not restate in prose what is already shown in a figure or table in equivalent numerical detail.

STRICT PROHIBITIONS
- Do not interpret, compare to prior literature, or discuss the implications of findings — all interpretive commentary belongs exclusively in the Discussion.
- Do not re-describe methods within the results section; if a brief methodological reminder is needed, limit it to one clause (e.g., "Using the classifier trained in Section 2.3…").
- Do not use evaluative adjectives ("impressive," "excellent," "surprising") to characterize findings. Let precise data speak; evaluative framing is the reader's role.
- Do not use language that strategically emphasizes only favorable results or downplays non-significant but scientifically relevant findings.

TENSE
- Use past tense throughout to describe specific experimental outcomes ("Treatment X reduced Y by 34%").
- Use present tense when referring to figures and tables as existing objects ("Figure 3 shows the distribution of…").
""".strip()

SYSTEM = (
    "You are a scientific manuscript assistant. Write a formal Results section. "
    "Use ONLY the supplied materials. Do not invent data, extrapolate, or add interpretations. "
    "Reference figures as 'Fig. 1', 'Fig. 2', etc.\n\n"
    + WRITING_STANDARDS
    + "\n\n"
    + RESULTS_STANDARDS
)


def generate_results(captions: list[tuple[int, str]]) -> str:
    results_texts = []
    for f in sorted(RESULTS_DIR.glob("*.txt")):
        results_texts.append(f.read_text().strip())

    caption_summary = "\n".join(
        [f"Fig. {num}: {text[:300]}..." if len(text) > 300 else f"Fig. {num}: {text}"
         for num, text in captions]
    )

    prompt = (
        f"Write a Results section for a scientific manuscript.\n\n"
        f"{format_entity_constraints()}\n\n"
        f"Figure captions:\n{caption_summary}\n\n"
        f"Results/significance notes supplied by the author:\n"
        + "\n\n---\n\n".join(results_texts)
        + "\n\nWrite the Results section using ONLY the above materials. "
        "Reference figures as 'Fig. 1', 'Fig. 2', etc. "
        "Do not invent data or add interpretations beyond what is stated."
    )

    result = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=3000)
    append_section("manuscript_draft.docx", "Results", result)
    audit_and_save(result, label="entity_audit_results")
    return result
