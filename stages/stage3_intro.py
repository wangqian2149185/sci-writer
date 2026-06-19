from pathlib import Path
from utils.claude_client import chat_with_web_search, chat
from utils.doc_builder import save_intro_bullets, append_section, save_references_md
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

ROOT = Path(__file__).parent.parent

EXTRACT_SYSTEM = (
    "You are a scientific manuscript analyst. Your sole task at this stage is to extract "
    "and list the principal findings from a Results section with full quantitative precision. "
    "Do not interpret, evaluate, rank, or add any commentary beyond what is explicitly stated in the text. "
    "Extract ALL findings — positive, null, unexpected, and secondary — without selection bias. "
    "Never paraphrase vaguely; preserve all numerical values, units, and statistical measures exactly as they appear."
)

SEARCH_SYSTEM = (
    "You are a scientific literature researcher. Search for peer-reviewed publications "
    "relevant to the provided keywords. For each finding, state the fact/claim precisely, "
    "the citation (Author, Journal, Year, DOI), and a one-sentence relevance note. "
    "Only report real, verifiable published literature. "
    "Never fabricate authors, titles, journals, years, or DOIs."
)

INTRO_STANDARDS = """
INTRODUCTION SECTION — SPECIFIC RULES (apply in addition to universal writing standards):

STRUCTURE (inverted funnel — mandatory)
- Paragraph 1: Broad disciplinary context — open with a striking, evidence-based statement of the problem's real-world importance, scale, or urgency. The first sentence must compel the reader to continue; generic openings are prohibited.
- Paragraph 2: Narrow to the specific research area, synthesizing what the field collectively understands.
- Paragraph 3: Explicitly and unmistakably articulate the knowledge gap, unresolved contradiction, or unmet need. This gap statement is the intellectual justification for the entire paper.
- Final paragraph: Concise, explicit statement of the study's aims, hypotheses, or research questions using action verbs ("to determine," "to quantify," "to characterize"). If structurally complex, include one "map" sentence (e.g., "Section 2 describes…; Section 3 presents…").

LITERATURE CITATION
- Cite a representative but focused body of literature; prioritize high-impact, recent primary research articles.
- For each citation cluster, synthesize what the literature collectively shows rather than listing individual findings sequentially. Use integrative phrases: "Collectively, these studies suggest…", "Across diverse experimental systems, a consistent pattern emerges…"
- Do not provide an exhaustive review — comprehensive literature surveys belong in review articles, not empirical introductions.

GAP STATEMENT
- Use contrastive language to highlight the gap with logical sharpness: "Although X has been extensively characterized, the mechanisms underlying Y remain poorly understood."
- The contrast must be directly relevant to the specific contribution of this paper.

LOGICAL FLOW
- Use explicit logical connectors between paragraphs ("However," "Despite this," "Building on these findings,") to create a continuous argumentative thread that leads inevitably to the research question.
- Do not allow paragraphs to stand as disconnected units.

TONE
- Convey authentic scientific curiosity and intellectual excitement about the open question. Avoid bureaucratic tone; write to inspire engagement.
- Calibrate background depth to the knowledge level of the target journal's readership — omit textbook-level material the audience already knows.

STRICT PROHIBITIONS
- Do not describe methods, present data, or discuss results. Background, context, and rationale only.
- Do not state objectives in vague terms ("to explore," "to look at," "to study"). Every objective must be operationally specific and linked to a measurable outcome or testable prediction.

CITATION DENSITY & FORMAT
- Every claim, assertion, or statement of established fact must be supported by a minimum of 2 references drawn from the same thematic category of the literature pool.
- Single-reference support is permitted only for a finding that is uniquely attributable to one study and has not been independently replicated; this exception must be rare.
- Place citation superscripts at the end of the citing sentence, immediately before the full stop, in order of first appearance throughout the manuscript. Format: ¹²  ³⁴⁵  etc. (no spaces between superscript digits within the same citation cluster).
- Do not cluster all citations at the end of a paragraph. Attach each superscript to the specific sentence whose claim it supports.
- After the Introduction text, append a numbered References list in the exact order the superscripts appear, matching each superscript number to its full bibliographic entry.

TENSE
- Use present tense for established facts and current states of knowledge ("It is well established that…").
- Use past tense for specific completed studies ("Smith et al. demonstrated that…").
""".strip()

INTRO_SYSTEM = (
    "You are a scientific manuscript assistant. Write a formal, peer-reviewed Introduction section. "
    "Use ONLY the bullet points and results provided. "
    "Use superscript numbers [¹ ² ³] for in-text citations. "
    "Target 800–2000 words. Never hallucinate citations.\n\n"
    + WRITING_STANDARDS
    + "\n\n"
    + INTRO_STANDARDS
)


def extract_results_findings(results_text: str) -> tuple[list[str], str]:
    """
    Parses the Results section and returns (findings_list, display_text).
    Each finding uses the format:
      [N]. [What was done] → [Quantitative outcome] — [One-sentence interpretation].
    """
    prompt = (
        "Parse the following Results section in full. "
        "Extract every principal finding as a discrete, self-contained item.\n\n"
        "For each item use EXACTLY this format:\n"
        "[N]. [What was measured or tested] → [Direction and magnitude of outcome, "
        "with units and statistical values where available] — [One-sentence scientific meaning].\n\n"
        "Rules:\n"
        "- Include ALL findings: positive, null, unexpected, and secondary.\n"
        "- Preserve quantitative precision (numbers, units, p-values, confidence intervals) exactly.\n"
        "- Group related findings under a shared sub-label if the Results contains multiple "
        "experiments or datasets (e.g., 'Experiment 1 — Protein expression:').\n"
        "- Do NOT interpret, evaluate, rank, or add commentary beyond what is stated.\n"
        "- Do NOT begin drafting any introduction sentence.\n\n"
        f"Results section:\n{results_text}"
    )
    response = chat([{"role": "user", "content": prompt}], system=EXTRACT_SYSTEM, max_tokens=3000)

    import re
    findings = []
    for line in response.split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
            clean = re.sub(r"^[\d\.\-\•\*]+\s*", "", line).strip()
            if clean:
                findings.append(clean)
        elif line and not findings:
            # Capture sub-labels (e.g., group headers) before numbered items
            findings.append(line)

    display = (
        "## Key findings from Results section (please review and confirm)\n\n"
        + response
        + "\n\n---\n"
        "Please review the findings above. You may:\n"
        "1. Type `confirm` if the list is complete and accurate\n"
        "2. Edit any item directly and paste the corrected list\n"
        "3. Add findings that are missing\n"
        "4. Remove items that should not anchor the Introduction\n\n"
        "**I will not proceed until you confirm.**"
    )
    return findings, display


def research_intro(keywords: str, results_text: str) -> tuple[list[str], str]:
    """
    Performs web search and returns (papers_list, display_text).
    Each entry in papers_list is a multi-line string: Title / Authors / DOI / Relevance.
    """
    prompt = (
        f"Search for peer-reviewed literature relevant to these keywords: {keywords}\n\n"
        f"Context from the manuscript's Results section:\n{results_text[:1500]}\n\n"
        "For EACH paper found, use EXACTLY this 4-line block format:\n"
        "[N]. <Full paper title>\n"
        "Authors: <First author surname> ... <Corresponding/last author surname>\n"
        "DOI: <DOI or N/A>\n"
        "Relevance: <One sentence on why this paper is relevant to this manuscript>\n\n"
        "Aim for 30–60 papers across diverse sub-topics. "
        "You may insert a thematic sub-label line between groups (e.g., '### Molecular mechanisms:') "
        "but do NOT insert any other text between the 4 lines of a single entry."
    )

    response, _ = chat_with_web_search(prompt, system=SEARCH_SYSTEM, max_tokens=8192)

    import re

    papers = []
    current: dict = {}
    for line in response.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[?(\d+)\]?[.\)]\s+(.+)", line)
        if m:
            if current.get("title"):
                papers.append(current)
            current = {"title": m.group(2).strip(), "authors": "", "doi": "", "relevance": ""}
        elif re.match(r"^[Aa]uthors?:", line):
            current["authors"] = re.sub(r"^[Aa]uthors?:\s*", "", line).strip()
        elif re.match(r"^DOI:", line, re.IGNORECASE):
            current["doi"] = re.sub(r"^DOI:\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^[Rr]elevance:", line):
            current["relevance"] = re.sub(r"^[Rr]elevance:\s*", "", line).strip()
    if current.get("title"):
        papers.append(current)

    # Fallback: if structured parsing failed, take substantive lines as plain bullets
    if not papers:
        plain = [l.strip() for l in response.split("\n") if len(l.strip()) > 30 and not l.strip().startswith("#")]
        save_intro_bullets(plain)
        records = merge_reference_records(load_reference_table(), parse_reference_bullets(plain))
        save_reference_table(records)
        if not plain:
            display = (
                "## Introduction Research Papers (Stage 3)\n\n"
                "⚠️ Could not parse response. Raw output:\n\n"
                f"{response}\n\n"
                "Please paste the relevant items as a numbered list."
            )
        else:
            display = "## Introduction Research Papers (Stage 3)\n\n"
            for i, b in enumerate(plain, 1):
                display += f"{i}. {b}\n"
            display += "\n\nReply with numbers to include, e.g.: `1,3,5` or `all`"
        return plain, display

    # Store each paper as a multi-line string (used downstream by write_introduction)
    bullets = []
    for p in papers:
        entry = p["title"]
        if p["authors"]:
            entry += f"\nAuthors: {p['authors']}"
        if p["doi"]:
            entry += f"\nDOI: {p['doi']}"
        if p["relevance"]:
            entry += f"\nRelevance: {p['relevance']}"
        bullets.append(entry)

    save_intro_bullets(bullets)
    records = merge_reference_records(load_reference_table(), parse_reference_bullets(bullets))
    save_reference_table(records)

    display = "## Introduction Research Papers (Stage 3)\n\n"
    for i, p in enumerate(papers, 1):
        display += f"**{i}. {p['title']}**\n"
        if p["authors"]:
            display += f"   {p['authors']}\n"
        if p["doi"]:
            display += f"   DOI: {p['doi']}\n"
        if p["relevance"]:
            display += f"   *{p['relevance']}*\n"
        display += "\n"
    display += "Reply with the numbers you want to include, e.g.: `1,3,5` or `all`"

    return bullets, display


def write_introduction(
    selected_bullets: list[str],
    results_text: str,
    references: list[str],
    confirmed_findings: list[str] | None = None,
) -> tuple[str, list[str]]:
    """
    Writes Introduction from selected bullets, anchored to confirmed Results findings.
    Returns (intro_text, updated_references).
    """
    source_records = parse_reference_bullets(selected_bullets)
    existing_records = merge_reference_records(load_reference_table(), references)
    reference_table = merge_reference_records(existing_records, source_records)
    save_reference_table(reference_table)
    bullets_text = format_sources_for_prompt(source_records)

    findings_block = ""
    if confirmed_findings:
        findings_text = "\n".join(f"{i+1}. {f}" for i, f in enumerate(confirmed_findings))
        findings_block = (
            f"CONFIRMED KEY FINDINGS FROM THE RESULTS SECTION "
            f"(these are the fixed anchors of the Introduction — the entire argumentative "
            f"chain must lead the reader to understand why exactly these findings needed to be made):\n"
            f"{findings_text}\n\n"
        )

    prompt = (
        f"Write an Introduction for a scientific manuscript.\n\n"
        f"{format_entity_constraints()}\n\n"
        f"{findings_block}"
        f"Canonical literature sources (use as citation source material):\n{bullets_text}\n\n"
        f"Results section (full context):\n{results_text[:1500]}\n\n"
        "Requirements:\n"
        "- 800–2000 words\n"
        "- CITATION RULE: every claim or statement of established fact must carry a minimum of "
        "2 superscript citations from the same thematic category. Single-reference exceptions are "
        "permitted only for uniquely attributable findings with no independent replication — use sparingly.\n"
        "- CITATION FORMAT: superscripts placed at the end of the citing sentence immediately before "
        "the full stop, numbered in order of first appearance throughout the manuscript. "
        "Example: '...has been implicated in disease progression.¹²' or '...remains contested.³⁴⁵'\n"
        "- Do not cluster citations at paragraph ends — attach each superscript to its specific sentence.\n"
        "- Structure: (a) broad field background, (b) specific research area, "
        "(c) knowledge gap that makes the confirmed findings necessary, "
        "(d) explicit statement of study objectives using action verbs\n"
        "- The gap statement in paragraph 3 must be constructed so that the confirmed "
        "findings above represent the direct, logical answer to that gap\n"
        "- After the Introduction text, append a 'References' section listing all cited sources "
        "in strict order of first appearance, each entry numbered to match its superscript\n"
        "- Only cite the canonical sources provided above\n"
        "- Treat each SOURCE_ID as a unique paper. If the same DOI, PMID, arXiv ID, or title hash "
        "appears in multiple forms, it is still one source, not independent supporting evidence\n"
        "- Do not create new references, invented short citations, or duplicate bibliography entries"
    )

    result = chat([{"role": "user", "content": prompt}], system=INTRO_SYSTEM, max_tokens=6000)

    # Extract references block if present
    import re
    ref_match = re.search(r"References\s*\n(.*)", result, re.DOTALL | re.IGNORECASE)
    new_refs = []
    intro_text = result
    if ref_match:
        ref_block = ref_match.group(1).strip()
        intro_text = result[: ref_match.start()].strip()
        for line in ref_block.split("\n"):
            line = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            if line:
                new_refs.append(line)

    all_records = merge_reference_records(reference_table, new_refs)
    save_reference_table(all_records)
    all_refs = bibliography_from_table(all_records)
    save_references_md(all_refs)
    append_section("manuscript_draft.docx", "Introduction", intro_text)
    audit_and_save(intro_text, label="entity_audit_introduction")

    return intro_text, all_refs
