from utils.claude_client import chat
from utils.doc_builder import prepend_section
from utils.writing_standards import WRITING_STANDARDS

ABSTRACT_STANDARDS = """
ABSTRACT — SPECIFIC RULES (apply in addition to universal writing standards):

MANDATORY STRUCTURE (six elements, in this order)
1. One sentence of broad background context — open with a compelling statement of real-world or scientific significance that immediately communicates why this research matters to the broadest possible audience within the discipline.
2. The specific problem or knowledge gap this study addresses.
3. The study objective, stated precisely.
4. Key methods in one to two sentences.
5. Principal quantitative findings — include specific numerical outcomes (effect sizes, p-values, fold-changes, accuracy percentages). Never substitute with "significantly improved" or "better performance."
6. The main conclusion and its significance, stated with appropriate scientific confidence.

SELF-CONTAINMENT
- The abstract must be fully self-contained and interpretable without reading the full paper, accessing figures, tables, or references.
- Include all essential quantitative results; do not rely on the reader having access to any other component.

KEYWORDS
- Embed 3–5 high-priority discipline-specific keywords naturally within the abstract text to maximize discoverability in PubMed, Scopus, and Web of Science.

STRICT PROHIBITIONS
- Do not cite references, figures, tables, supplementary materials, or equations.
- Do not introduce abbreviations or acronyms unless universally recognized in the field (e.g., DNA, RNA, PCR). If used, define at first mention within the abstract itself.
- Do not use overly hedged language ("might suggest," "could possibly indicate," "it appears that"). State findings and conclusions with appropriate scientific confidence.
- Do not use self-congratulatory phrases ("this is the first study to…," "novel breakthrough") unless directly substantiated by comprehensive literature review evidence.
- Do not include background information not directly relevant to motivating this specific study. Every word must contribute essential information.

STYLE & TENSE
- Use past tense for study objectives, methods, and results ("We investigated…", "The model achieved…").
- Use present tense for established facts, general principles, and conclusions ("These results demonstrate…").
- Every adjective and adverb must be defensible by the data. Replace evaluative terms ("excellent," "powerful," "remarkable") with precise quantitative comparisons against a stated benchmark or baseline.
""".strip()

SYSTEM = (
    "You are a scientific manuscript assistant. Write a concise, structured Abstract. "
    "Do not invent content. Use only what is provided in the manuscript sections.\n\n"
    + WRITING_STANDARDS
    + "\n\n"
    + ABSTRACT_STANDARDS
)


def generate_abstract(
    results_text: str,
    intro_text: str,
    discussion_text: str,
    methods_text: str,
    word_count: int = 250,
) -> str:
    prompt = (
        f"Write an Abstract of approximately {word_count} words for a scientific manuscript.\n\n"
        f"Results:\n{results_text[:1500]}\n\n"
        f"Introduction (key points):\n{intro_text[:800]}\n\n"
        f"Discussion (key points):\n{discussion_text[:800]}\n\n"
        f"Methods (brief):\n{methods_text[:500]}\n\n"
        f"Structure strictly as:\n"
        f"1. Background sentence (1-2 sentences)\n"
        f"2. Gap/problem statement (1 sentence)\n"
        f"3. What was done (1-2 sentences)\n"
        f"4. Key results (2-3 sentences)\n"
        f"5. Significance (1 sentence)\n\n"
        f"Target: ~{word_count} words. Do not include citations in the abstract."
    )

    result = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=800)
    prepend_section("manuscript_draft.docx", "Abstract", result)
    return result
