from utils.claude_client import chat
from utils.doc_builder import prepend_section

SYSTEM = (
    "You are a scientific manuscript assistant. Write a concise, structured Abstract. "
    "Structure: Background → gap/problem → what was done → key results → significance. "
    "Do not invent content. Use only what is provided."
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
