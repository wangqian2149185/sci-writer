from pathlib import Path
from utils.claude_client import chat
from utils.doc_builder import save_tone_md
from utils.writing_standards import WRITING_STANDARDS

ROOT = Path(__file__).parent.parent
TONE_TEMPLATES_DIR = ROOT / "input" / "tone_templates"
OUTPUT = ROOT / "output"

# ─── Analyst role ─────────────────────────────────────────────────────────────

ANALYST_SYSTEM = """
ROLE: Authorship Style Analyst — Computational Stylometrist

You are an expert computational stylometrist and linguistic analyst specializing in authorship profiling. Your function is to extract a complete, evidence-based, quantitatively grounded Style Profile from a provided text corpus attributed to a single author. You operate with the rigor of a forensic linguist and the sensitivity of a literary critic.

OPERATING RULES
- You do not generalize, assume, or improvise. Every claim about the author's style must be supported by specific textual evidence quoted verbatim from the corpus.
- You do not produce impressionistic adjective descriptions ("the author writes clearly"). Every feature must be traceable to specific quoted examples with quantitative support.
- You analyze writing across six mandatory dimensions in strict sequence: D1 Lexical → D2 Syntactic → D3 Discourse → D4 Rhetorical → D5 Cognitive/Epistemic → D6 Pragmatic.
- For each feature, you assign a reliability rating: HIGH (>70% of documents, consistent across contexts), MEDIUM (40–70%, context-dependent), LOW (<40%, possibly situational).
- Only HIGH-rated features become mandatory reproduction targets. MEDIUM features are applied with contextual judgment. LOW features are noted but not actively reproduced.
- Your deliverable is a structured Style Profile document — not a prose essay — with six labeled sections, verbatim examples, quantitative data, and one executable reproduction instruction per feature cluster.
- You do not begin any generation task until the Style Profile is complete and confirmed.

CORPUS REQUIREMENTS
- Minimum 5,000 words of first-person original writing spanning at least 3 distinct writing occasions or document types.
- Do not include co-authored documents, heavily edited documents, or template-constrained formats (legal contracts, standardized forms) in the primary analysis. Flag these as secondary-tier if present.
- Style features that appear consistently across diverse contexts are the most reliable signature elements.

DIMENSION ANALYSIS DIRECTIVES

D1 — LEXICAL
- Extract top-50 content words (excluding stop words): raw frequency per 1,000 words, field-standard vs. idiosyncratic, consistent collocations. Flag the 10 words whose frequency most deviates from general written language norms.
- Compute function word profile: first- vs. third-person pronoun ratios; coordinating vs. subordinating conjunctions; hedging adverbs (perhaps, possibly, arguably) vs. assertive adverbs (clearly, certainly); demonstrative frequency.
- Compute type-token ratio (TTR) in rolling 500-word windows: does the author favor cohesive repetition (low TTR) or synonymy-based elegance (high TTR)? Note density of rare vocabulary and any idiosyncratic coinages.

D2 — SYNTACTIC
- Measure sentence length for every sentence: mean, standard deviation, short (<12 words) to long (>30 words) ratio. Identify rhythm type: uniform-short, uniform-long, variable-rhythmic, front-loaded. Do NOT report the mean as the pattern — the variance and sequencing pattern is the pattern.
- Analyze subordination: initial / medial / final subordinate clause positioning; left-branching vs. right-branching preference; frequency of parenthetical insertions, em-dash interruptions, appositive phrases.
- Catalog sentence-opening categories: subject-initial, adverbial-initial, participial-initial, nominal-initial, conjunction-initial. Compute frequency of each. This distribution is one of the hardest-to-fake syntactic fingerprints.
- Measure active vs. passive voice ratio; modal verb distribution (certainty vs. possibility); nominalization density; impersonal construction frequency.

D3 — DISCOURSE
- Analyze paragraph architecture: mean paragraph length; deductive (topic-sentence-first) vs. inductive (conclusion-last) structure; transition handling (explicit connector, lexical repetition, pronoun reference, abrupt shift); ratio of single-sentence paragraphs to multi-sentence paragraphs.
- Catalog cohesion devices with exact connector words: additive, adversative, causal, temporal/sequential, lexical chain. Identify which specific words are distinctively preferred over functional synonyms — this is highly individual. Do not substitute synonyms in generation.
- Identify macro-level information sequencing pattern: problem-solution, claim-evidence-elaboration, general-specific, chronological, compare-contrast, question-answer. Note whether the author uses Bottom Line Up Front or progressive build.

D4 — RHETORICAL
- Identify all figurative language: record source domain (spatial, mechanical, biological, economic, etc.), novelty (conventional vs. original), and introduction signal. Source domain preference is a deep individual signature.
- Document emphasis and contrast strategies: syntactic inversion, cleft sentences, fronting, typographic emphasis, repetition structures (anaphora, parallelism), rhetorical questions, explicit contrast pairs. Note absent devices — absence is as diagnostic as presence.
- Analyze exemplification habits: signal phrases used, example source type (personal experience, published research, hypothetical, historical), example length relative to claim, whether examples are commented on or left to stand alone.

D5 — COGNITIVE / EPISTEMIC
- Map argument structure per text: deductive vs. inductive; counterargument handling (steelmanning vs. ignoring); treatment of logical gaps (explicit, hedged inference, implicit); evidence hierarchy (empirical data, expert authority, analogy, personal observation).
- Measure epistemic stance: ratio of facts vs. opinions vs. possibilities; specific epistemic boundary signals; over-hedge vs. under-hedge tendency; response to complexity (simplification, nuance, irresolvable tension noted).
- Identify conceptual association patterns: recurring cross-domain bridges; habitual micro-to-macro linkages; recurring intellectual preoccupations or tensions across documents.

D6 — PRAGMATIC
- Analyze reader relationship: inclusive vs. exclusive "we"; direct vs. indirect reader address; assumed knowledge calibration; politeness strategies (formal/distanced, collegial, conversational).
- Construct tonal signature: default emotional register; within-document tonal shifts; presence and signaling of humor, irony, sarcasm; evaluative language density; formality markers.
- Identify identity markers: how the author references own prior work; insider vs. outsider positioning; self-deprecating vs. authoritative moves; handling of named disagreement.
""".strip()

# ─── Generator role ───────────────────────────────────────────────────────────

GENERATOR_SYSTEM = (
    """
ROLE: Style-Faithful Generator

You have been provided with a validated six-dimension Style Profile for a specific author. Your sole task is to generate new text that is indistinguishable in style from that author's authentic writing.

OPERATING RULES
- You do not generate from your own default voice.
- You do not introduce vocabulary, syntactic structures, rhetorical devices, argument patterns, or tonal registers that are absent from the Style Profile.
- Before drafting, internalize all six dimensions of the profile.
- After drafting each paragraph, conduct a mandatory six-point compliance check:
  (D1) Are lexical choices within the author's documented vocabulary range and function-word ratios?
  (D2) Does sentence rhythm, length variance, and clause structure match the profile?
  (D3) Does paragraph architecture match the documented deductive/inductive pattern and cohesion devices?
  (D4) Are rhetorical devices consistent with the profile — and are absent devices absent here too?
  (D5) Does argument structure and epistemic calibration match the documented reasoning pattern?
  (D6) Does tonal register, reader relationship, and self-positioning match?
- Any paragraph failing two or more checks must be rewritten before proceeding.
- Do not declare text complete until all paragraphs pass the compliance check.
- Do not adjust the author's certainty level. Epistemic calibration is a core identity feature.
- Do not neutralize tonal extremes. Tonal flattening is the most immediately detectable form of inauthenticity.
- Do not substitute the author's documented connector words with generic synonyms.
- Do not invent figurative language or rhetorical devices absent from the corpus profile.
- Do not reproduce sentence rhythm by averaging — reproduce the variance and sequencing pattern.

CONTENT PRESERVATION
- Preserve ALL scientific content, data, figure references, and citations exactly.
- Change only style, phrasing, and sentence structure — never alter facts, values, or scientific claims.
""".strip()
    + "\n\n"
    + WRITING_STANDARDS
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def extract_text_from_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(path))
            return "\n".join(page.get_text() for page in doc)
        except Exception as e:
            return f"[Could not extract PDF: {e}]"
    elif path.suffix.lower() == ".docx":
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            return f"[Could not extract DOCX: {e}]"
    return path.read_text(errors="ignore")


def _corpus_audit(files: list[Path], samples: list[tuple[str, str]]) -> str:
    """Step 1 — Corpus audit. Returns audit summary."""
    doc_list = "\n".join(
        f"- {name}: ~{len(text.split())} words"
        for name, text in samples
    )
    total_words = sum(len(t.split()) for _, t in samples)
    audit_prompt = (
        f"STEP 1 — CORPUS AUDIT\n\n"
        f"Documents provided ({len(samples)} files, ~{total_words} total words):\n{doc_list}\n\n"
        "Produce a concise corpus audit report covering:\n"
        "1. Total word count and whether the 5,000-word minimum is met\n"
        "2. Document type, approximate date, and intended audience for each file\n"
        "3. Proportion of corpus from each document type\n"
        "4. Flag any documents suspected of heavy external editing, template constraints, or co-authorship\n"
        "5. Whether the corpus meets minimum quantity AND diversity thresholds\n"
        "6. Recommendation: proceed / request additional material / proceed with caveats\n\n"
        "Be specific. Do not generalize."
    )
    return chat([{"role": "user", "content": audit_prompt}], system=ANALYST_SYSTEM, max_tokens=1000)


def _run_six_dimension_analysis(combined_corpus: str) -> str:
    """Steps 2–4 — Sequential D1→D6 analysis producing the Style Profile document."""
    analysis_prompt = (
        f"STEPS 2–4 — SIX-DIMENSION SEQUENTIAL ANALYSIS → STYLE PROFILE\n\n"
        f"Full corpus:\n{combined_corpus}\n\n"
        "Conduct the six-dimension analysis in strict order: D1 → D2 → D3 → D4 → D5 → D6.\n"
        "Do not skip dimensions or combine them.\n\n"
        "For each dimension produce a labeled section containing:\n"
        "(a) Prose description of the feature cluster with quantitative data\n"
        "(b) 3–5 verbatim quoted examples from the corpus (with exact wording)\n"
        "(c) Reliability rating for each feature: HIGH / MEDIUM / LOW\n"
        "(d) One concise executable reproduction instruction\n\n"
        "DIMENSION CHECKLIST:\n"
        "D1 LEXICAL: top-50 content words (freq/1000w), top-10 deviants, function-word ratios "
        "(pronoun, conjunction, hedging/assertive adverb, demonstrative), TTR characterization, "
        "rare vocabulary density, idiosyncratic terms\n"
        "D2 SYNTACTIC: sentence length (mean, SD, short/long ratio), rhythm type, subordination "
        "positioning (initial/medial/final), branching preference, parenthetical/em-dash frequency, "
        "sentence-opening category distribution, active/passive ratio, modal distribution, "
        "nominalization density\n"
        "D3 DISCOURSE: paragraph length (sentences + words), deductive vs. inductive structure, "
        "transition mechanism, single-sentence paragraph ratio, cohesion device inventory with "
        "exact connector words and frequency, macro information sequencing pattern\n"
        "D4 RHETORICAL: figurative language inventory (source domains, novelty, introduction signals), "
        "emphasis/contrast strategy inventory, exemplification habits (signal phrases, source types, "
        "length, post-example commentary), explicitly note absent devices\n"
        "D5 COGNITIVE/EPISTEMIC: argument structure (deductive/inductive), counterargument handling, "
        "logical gap treatment, evidence hierarchy, epistemic stance profile (fact/opinion/possibility "
        "ratios, boundary signals, over/under-hedge tendency), conceptual association patterns\n"
        "D6 PRAGMATIC: pronoun reader-positioning (inclusive/exclusive we, direct/indirect address), "
        "assumed knowledge calibration, politeness strategy, tonal signature (default register, "
        "shifts, humor/irony presence and signals, evaluative density, formality markers), "
        "identity and self-positioning moves\n\n"
        "End with a one-paragraph PROFILE SUMMARY: the author's most distinctive cross-dimensional "
        "features and the three highest-priority reproduction targets."
    )
    return chat(
        [{"role": "user", "content": analysis_prompt}],
        system=ANALYST_SYSTEM,
        max_tokens=8000,
    )


def analyze_tone() -> str:
    """
    Run the full 5-step style extraction workflow.
    Returns the complete Style Profile text (saved to output/tone.md).
    """
    tone_path = OUTPUT / "tone.md"
    if tone_path.exists():
        return tone_path.read_text()

    template_files = (
        list(TONE_TEMPLATES_DIR.glob("*.pdf"))
        + list(TONE_TEMPLATES_DIR.glob("*.docx"))
        + list(TONE_TEMPLATES_DIR.glob("*.txt"))
    )
    if not template_files:
        return ""

    # Extract text from all files (no 5-file cap — use all provided)
    samples = []
    for f in template_files:
        text = extract_text_from_file(f)
        if text.strip():
            samples.append((f.name, text))

    combined_corpus = "\n\n".join(
        f"=== DOCUMENT: {name} ===\n{text}" for name, text in samples
    )

    # Step 1 — Corpus audit
    audit = _corpus_audit(template_files, samples)

    # Steps 2–4 — Six-dimension analysis → Style Profile
    profile = _run_six_dimension_analysis(combined_corpus)

    # Assemble full output
    full_output = (
        "# Style Profile — Authorship Analysis\n\n"
        "## STEP 1 — CORPUS AUDIT\n\n"
        + audit
        + "\n\n---\n\n"
        "## STEPS 2–4 — SIX-DIMENSION STYLE PROFILE\n\n"
        + profile
    )

    save_tone_md(full_output)
    return full_output


# ─── ORCID / web helpers ──────────────────────────────────────────────────────

def search_orcid_by_name(name: str, institution: str = "") -> list[dict]:
    """
    Search ORCID expanded-search API.
    Returns up to 5 candidate dicts: {orcid_id, name, institution}.
    """
    import urllib.request
    import urllib.parse
    import json

    if "," in name:
        family, given = name.split(",", 1)
    else:
        parts = name.strip().split()
        family = parts[-1] if parts else name
        given = " ".join(parts[:-1])

    q_parts = []
    if family.strip():
        q_parts.append(f"family-name:{urllib.parse.quote(family.strip())}")
    if given.strip():
        first_given = given.strip().split()[0]
        q_parts.append(f"given-names:{urllib.parse.quote(first_given)}")
    if institution.strip():
        q_parts.append(f"affiliation-org-name:{urllib.parse.quote(institution.strip())}")

    if not q_parts:
        return []

    q = "+AND+".join(q_parts)
    url = f"https://pub.orcid.org/v3.0/expanded-search/?q={q}&rows=5"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "sci-writer/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        candidates = []
        for r in data.get("expanded-result") or []:
            oid = r.get("orcid-id", "")
            if not oid:
                continue
            aff_list = r.get("current-institution-affiliation-name") or []
            candidates.append({
                "orcid_id": oid,
                "name": f"{r.get('given-names', '')} {r.get('family-names', '')}".strip(),
                "institution": aff_list[0] if aff_list else "",
            })
        return candidates
    except Exception:
        return []


def search_orcid_web(name: str) -> tuple[str, str]:
    """
    Use web search to find an author's ORCID when the registry API returns nothing.
    Returns (orcid_id, context_snippet) or ("", "").
    """
    from utils.claude_client import chat_with_web_search
    import re

    prompt = (
        f"Find the ORCID iD for researcher '{name}'. "
        "Search orcid.org or academic databases for their verified ORCID profile. "
        "Return ONLY the ORCID iD in the exact format XXXX-XXXX-XXXX-XXXX followed by a space "
        "and the researcher's confirmed full name. "
        "Example: 0000-0001-8593-9998 Feng Zhang\n"
        "If no verified ORCID can be found, return exactly: NOT_FOUND"
    )
    try:
        result, _ = chat_with_web_search(prompt, max_tokens=150)
        match = re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", result)
        if match:
            return match.group(0), result.strip()
    except Exception:
        pass
    return "", ""


def fetch_orcid_works(orcid_id: str, max_papers: int = 10) -> list[dict]:
    """
    Fetch work summaries from an ORCID profile.
    Returns list of {title, doi, year} dicts.
    """
    import urllib.request
    import json

    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "sci-writer/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        works = []
        for group in data.get("group") or []:
            summary_list = group.get("work-summary") or [{}]
            summary = summary_list[0]
            title_data = (summary.get("title") or {})
            title = (title_data.get("title") or {}).get("value", "")
            year_data = summary.get("publication-date") or {}
            year = (year_data.get("year") or {}).get("value", "")

            # Check group-level external-ids first, then work-summary level
            doi = ""
            for src in (group, summary):
                for eid in (src.get("external-ids") or {}).get("external-id") or []:
                    if eid.get("external-id-type") == "doi":
                        doi = eid.get("external-id-value", "").strip()
                        break
                if doi:
                    break

            if title:
                works.append({"title": title, "doi": doi, "year": year})
            if len(works) >= max_papers:
                break
        return works
    except Exception:
        return []


def fetch_paper_abstract(doi: str, title: str = "") -> str:
    """
    Fetch abstract via Semantic Scholar (primary) then Crossref (fallback).
    Returns formatted text or "" if nothing found.
    """
    import urllib.request
    import urllib.parse
    import json
    import re

    if doi:
        # Semantic Scholar
        ss_url = (
            f"https://api.semanticscholar.org/graph/v1/paper/"
            f"DOI:{urllib.parse.quote(doi)}?fields=title,abstract,year,venue"
        )
        try:
            req = urllib.request.Request(ss_url, headers={"User-Agent": "sci-writer/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode())
            abstract = data.get("abstract") or ""
            if abstract:
                t = data.get("title") or title or doi
                venue = data.get("venue") or ""
                year = data.get("year") or ""
                return f"TITLE: {t}\nVENUE: {venue} ({year})\n\nABSTRACT:\n{abstract}"
        except Exception:
            pass

        # Crossref fallback
        cr_url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
        try:
            req = urllib.request.Request(
                cr_url,
                headers={"User-Agent": "sci-writer/1.0 (mailto:contact@example.com)"},
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode())
            abstract = (data.get("message") or {}).get("abstract") or ""
            if abstract:
                abstract = re.sub(r"<[^>]+>", "", abstract).strip()
                titles = (data.get("message") or {}).get("title") or []
                t = " ".join(titles) if titles else (title or doi)
                return f"TITLE: {t}\n\nABSTRACT:\n{abstract}"
        except Exception:
            pass

    return ""


def analyze_tone_from_orcid(orcid_id: str, author_display_name: str = "") -> str:
    """
    Fetch works via ORCID, retrieve abstracts, and run the full 6-dimension style analysis.
    Returns the Style Profile text and saves it to output/tone.md.
    """
    works = fetch_orcid_works(orcid_id, max_papers=10)
    if not works:
        return ""

    samples = []
    for w in works:
        text = fetch_paper_abstract(w["doi"], w["title"])
        if text and len(text.split()) > 30:
            label = f"{w['title'][:70]} ({w.get('year', '')})"
            samples.append((label, text))

    if not samples:
        return ""

    combined_corpus = "\n\n".join(
        f"=== PAPER: {name} ===\n{text}" for name, text in samples
    )

    audit = _corpus_audit([], samples)
    profile = _run_six_dimension_analysis(combined_corpus)

    label = author_display_name or orcid_id
    full_output = (
        f"# Style Profile — {label} (ORCID: {orcid_id})\n\n"
        "## STEP 1 — CORPUS AUDIT\n\n"
        + audit
        + "\n\n---\n\n"
        "## STEPS 2–4 — SIX-DIMENSION STYLE PROFILE\n\n"
        + profile
    )

    save_tone_md(full_output)
    return full_output


# ─── Public API ───────────────────────────────────────────────────────────────

def rewrite_in_tone(style_profile: str) -> str:
    """
    Rewrite manuscript_draft.docx using the validated Style Profile.
    Applies six-point per-paragraph compliance check.
    Returns rewritten text and saves to output/manuscript_toned.docx.
    """
    draft_path = OUTPUT / "manuscript_draft.docx"
    if not draft_path.exists():
        return "manuscript_draft.docx not found."

    from docx import Document
    doc = Document(str(draft_path))
    draft_text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    prompt = (
        "SKILL: generate_in_author_style\n\n"
        f"VALIDATED STYLE PROFILE:\n{style_profile}\n\n"
        f"MANUSCRIPT TO REWRITE:\n{draft_text}\n\n"
        "EXECUTION INSTRUCTIONS:\n"
        "1. Load and internalize all six profile dimensions before drafting.\n"
        "2. Apply all HIGH-reliability features mandatorily; MEDIUM-reliability features contextually.\n"
        "3. After drafting each paragraph, run the six-point compliance check:\n"
        "   D1: lexical choices within documented vocabulary range and function-word ratios?\n"
        "   D2: sentence rhythm, length variance, and clause structure match profile?\n"
        "   D3: paragraph architecture matches documented pattern and cohesion devices?\n"
        "   D4: rhetorical devices consistent with profile; absent devices remain absent?\n"
        "   D5: argument structure and epistemic calibration match documented pattern?\n"
        "   D6: tonal register, reader relationship, and self-positioning match?\n"
        "4. Rewrite any paragraph failing two or more checks before proceeding to the next.\n"
        "5. After the full rewritten manuscript, append a brief COMPLIANCE REPORT listing "
        "which profile features were applied, which required rewrite iterations, and any "
        "dimension where corpus evidence was insufficient to guide generation.\n\n"
        "CONTENT RULES:\n"
        "- Preserve ALL scientific content, data, figure references (Fig. 1, etc.), and citations exactly.\n"
        "- Change only style, phrasing, and sentence structure — never alter facts or values.\n"
        "- Do not introduce vocabulary, devices, or structures absent from the profile.\n"
        "- Do not substitute documented connector words with synonyms.\n"
        "- Reproduce sentence length variance and sequencing — not just the mean length."
    )

    result = chat(
        [{"role": "user", "content": prompt}],
        system=GENERATOR_SYSTEM,
        max_tokens=8192,
    )

    # Separate compliance report from manuscript body if present
    manuscript_text = result
    if "COMPLIANCE REPORT" in result.upper():
        idx = result.upper().rfind("COMPLIANCE REPORT")
        manuscript_text = result[:idx].strip()

    # Save toned manuscript to docx
    new_doc = Document()
    style = new_doc.styles["Normal"]
    from docx.shared import Pt
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    for para in manuscript_text.split("\n\n"):
        para = para.strip()
        if para:
            new_doc.add_paragraph(para)

    output_path = OUTPUT / "manuscript_toned.docx"
    new_doc.save(str(output_path))

    # Save compliance report separately
    compliance_path = OUTPUT / "style_compliance_report.md"
    if "COMPLIANCE REPORT" in result.upper():
        compliance_path.write_text(result[idx:])

    return result
