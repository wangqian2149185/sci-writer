from pathlib import Path
from utils.claude_client import chat
from utils.doc_builder import append_section, save_references_md, replace_references_section
from utils.entity_registry import audit_and_save, format_entity_constraints
from utils.reference_manager import (
    bibliography_from_table,
    format_sources_for_prompt,
    load_reference_table,
    merge_reference_records,
    parse_reference_bullets,
    save_reference_table,
)
from utils.writing_standards import WRITING_STANDARDS
from docx import Document

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "output"

DISCUSSION_STANDARDS = """
DISCUSSION SECTION — SPECIFIC RULES (apply in addition to universal writing standards):

OPENING
- The first one to two sentences must directly answer the research question(s) stated in the introduction — state clearly whether and how each hypothesis was supported or refuted by the data.
- Do not open with a summary of what was done; open with what was found and what it means.

INTERPRETATION & LITERATURE ENGAGEMENT
- For each major finding, explain whether it confirms, extends, contradicts, or nuances what was previously known; cite and engage critically with the most relevant prior work.
- Where the data permit, propose mechanistic explanations for the observed phenomena.
- Distinguish clearly between what the data directly demonstrate and what is being inferred or speculated, using appropriately calibrated epistemic hedges: "These data suggest…" (moderate confidence), "Our findings are consistent with the hypothesis that…" (tentative), "This demonstrates that…" (direct evidence). Match the hedge precisely to the strength of the evidence.
- When findings conflict with prior literature, engage with the discrepancy intellectually: propose plausible explanations (methodological differences, population differences, analytical choices) rather than dismissing or ignoring the contradiction.

LIMITATIONS
- Dedicate a clearly structured paragraph to an honest, specific, and complete discussion of limitations: methodological constraints, sample limitations, potential confounders, and scope of generalizability. Vague or partial limitation statements are insufficient.

FUTURE DIRECTIONS
- Propose specific, feasible, and intellectually compelling directions for future research, directly linked to the limitations identified and the open questions raised by the current findings. Generic suggestions are prohibited.

SIGNIFICANCE
- Articulate clearly the broader scientific, translational, or applied significance of the findings. Explain what new understanding this work contributes and why it matters for the field or beyond.
- Convey the intellectual significance with disciplined enthusiasm — why does this advance the field? What new questions does it open?

CITATION DENSITY & FORMAT
- Every interpretive claim, comparison to prior literature, or statement of established knowledge must be supported by a minimum of 2 references drawn from the same thematic category of the literature pool.
- Single-reference support is permitted only for a finding uniquely attributable to one study with no independent replication; this exception must be rare and deliberate.
- Place citation superscripts at the end of the citing sentence, immediately before the full stop, numbered in strict order of first appearance throughout the manuscript (continuing the sequence begun in the Introduction).
- Format: ¹²  ³⁴⁵  etc. (no spaces between superscript digits within the same cluster).
- Do not cluster all citations at the end of a paragraph — attach each superscript to the specific sentence whose claim it supports.

STRICT PROHIBITIONS
- Do not re-describe numerical results in the same form as in the Results section. Brief reference to anchor an interpretive point is permitted; restating data is not.
- Do not claim more than the data can support. Match the scope of claims precisely to the strength and reach of the evidence; avoid sweeping generalizations.
- Do not construct circular reasoning (e.g., "Our results are significant because they are statistically significant"). Significance must be argued in terms of scientific meaning, not statistical thresholds alone.
- Do not introduce new data, results, or analyses that were not presented in the Results section. Every factual claim must be anchored in already-reported results.
""".strip()

CONCLUSION_STANDARDS = """
CONCLUSION SECTION — SPECIFIC RULES (apply in addition to universal writing standards):

PURPOSE
- Synthesize — do not merely summarize — the principal findings. Distill the collective meaning of the results into a coherent, unified message that captures the overall contribution of the work.
- Explicitly return to the research question or hypothesis stated in the introduction and provide a direct, definitive answer based on the evidence. Close the narrative loop opened in the introduction.

CONTENT (concise — 150–300 words maximum)
- One or two sentences on the broader impact, translational potential, or field-level significance of the work. This is the statement reviewers, editors, and readers will cite when referencing the contribution.
- End with a single, forward-looking sentence gesturing toward the most important next step or unanswered question — without being redundant with the future directions discussed in the Discussion.

STRICT PROHIBITIONS
- Do not introduce any new data, citations, analyses, or arguments. Every claim must have been established in the preceding sections. The conclusion consolidates; it does not extend.
- Do not copy or paraphrase sentences directly from the Abstract or Discussion. Reframe findings from a higher-level perspective; the conclusion must feel like an earned culmination, not a repetition.
- Do not undercut principal conclusions with excessive caveats. Limitations have been addressed in the Discussion; the conclusion should project confidence appropriate to the assembled evidence.
- Do not allow the conclusion to become a third Discussion section. Every sentence must be a distillation, not an elaboration.
- Do not open with clichéd phrases such as "In summary, this study has shown that…" or "In conclusion, our results demonstrate…" Lead with the substance, not the announcement.
""".strip()

SYSTEM = (
    "You are a scientific manuscript assistant. Write a formal Discussion section. "
    "Connect results with published literature objectively and with evidential support. "
    "Do not invent citations. Only cite sources explicitly provided in the literature bullets.\n\n"
    + WRITING_STANDARDS
    + "\n\n"
    + DISCUSSION_STANDARDS
)

CONCLUSION_SYSTEM = (
    "You are a scientific manuscript assistant. Write a concise, standalone Conclusion section. "
    "Do not introduce new data, citations, or arguments not already established in the manuscript.\n\n"
    + WRITING_STANDARDS
    + "\n\n"
    + CONCLUSION_STANDARDS
)


def generate_conclusion(
    discussion_text: str,
    results_text: str,
    intro_text: str,
) -> str:
    prompt = (
        "Write a Conclusion section (150–300 words) for a scientific manuscript.\n\n"
        f"Introduction (research question/hypothesis):\n{intro_text[:800]}\n\n"
        f"Results (key findings):\n{results_text[:1000]}\n\n"
        f"Discussion (interpretation, limitations, future directions):\n{discussion_text[:1500]}\n\n"
        "The Conclusion must:\n"
        "1. Synthesize — not summarize — the principal findings into a unified message\n"
        "2. Directly answer the research question or hypothesis from the Introduction\n"
        "3. State the broader impact or field-level significance in one to two sentences\n"
        "4. Close with one forward-looking sentence on the most important next step\n\n"
        "Do NOT open with 'In summary,' 'In conclusion,' or any equivalent announcement phrase. "
        "Do NOT copy sentences from the Abstract or Discussion. "
        "Do NOT introduce new data, citations, or arguments."
    )
    return chat([{"role": "user", "content": prompt}], system=CONCLUSION_SYSTEM, max_tokens=600)


def generate_discussion(
    results_text: str,
    intro_text: str,
    selected_bullets: list[str],
    references: list[str],
    merge: bool = False,
) -> tuple[str, list[str]]:
    source_records = parse_reference_bullets(selected_bullets)
    reference_table = merge_reference_records(load_reference_table(), references)
    reference_table = merge_reference_records(reference_table, source_records)
    save_reference_table(reference_table)
    bullets_text = format_sources_for_prompt(source_records)

    prompt = (
        f"Write a Discussion section for a scientific manuscript.\n\n"
        f"{format_entity_constraints()}\n\n"
        f"Results:\n{results_text[:2000]}\n\n"
        f"Introduction context:\n{intro_text[:1000]}\n\n"
        f"Canonical literature sources (cite using superscript numbers):\n{bullets_text}\n\n"
        "The Discussion must include:\n"
        "1. Direct answer to the research question, stating whether each hypothesis was supported or refuted\n"
        "2. Interpretation of each major finding relative to published literature\n"
        "3. Mechanistic explanations where the data permit\n"
        "4. A dedicated limitations paragraph (methodological, sample, confounders, generalizability)\n"
        "5. Specific, feasible future directions linked to current limitations\n"
        "6. Broader scientific or translational significance of the work\n\n"
        "CITATION RULES (mandatory):\n"
        "- Every interpretive claim or comparison to prior literature must carry a minimum of 2 superscript "
        "citations from the same thematic category. Single-reference exceptions only for uniquely "
        "attributable findings — use sparingly.\n"
        "- Superscripts go at the end of the citing sentence immediately before the full stop, numbered "
        "in order of first appearance continuing from the Introduction sequence. "
        "Example: '...consistent with previous observations in animal models.¹⁵¹⁶'\n"
        "- Do not cluster citations at paragraph ends — attach each to its specific sentence.\n"
        "- Only cite canonical sources above. Never fabricate references.\n"
        "- Treat each SOURCE_ID as one unique paper even if a citation appears in variant forms."
    )

    discussion = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=5000)
    audit_and_save(discussion, label="entity_audit_discussion")

    if merge:
        draft_path = OUTPUT / "manuscript_draft.docx"
        if draft_path.exists():
            import shutil
            shutil.copy2(str(draft_path), str(OUTPUT / "manuscript_draft_backup.docx"))
        merged_text = f"[Results portion]\n\n{results_text}\n\n[Discussion portion]\n\n{discussion}"
        append_section("manuscript_draft.docx", "Results and Discussion", merged_text)
    else:
        append_section("manuscript_draft.docx", "Discussion", discussion)

    conclusion = generate_conclusion(discussion, results_text, intro_text)
    audit_and_save("\n\n".join([discussion, conclusion]), label="entity_audit_discussion_conclusion")
    append_section("manuscript_draft.docx", "Conclusion", conclusion)

    # Append References section after Conclusion, unified manuscript numbering
    canonical_refs = bibliography_from_table(load_reference_table())
    if canonical_refs:
        replace_references_section("manuscript_draft.docx", canonical_refs)
        save_references_md(canonical_refs)

    return discussion, canonical_refs
