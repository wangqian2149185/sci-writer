from pathlib import Path
from utils.claude_client import chat
from utils.doc_builder import append_section

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "input" / "results"
CAPTIONS_DIR = ROOT / "input" / "captions"

SYSTEM = (
    "You are a scientific manuscript assistant. Write a formal Results section. "
    "Use ONLY the supplied materials. Do not invent data, extrapolate, or add interpretations. "
    "Reference figures as 'Fig. 1', 'Fig. 2', etc. Use past tense and passive voice where appropriate."
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
        f"Figure captions:\n{caption_summary}\n\n"
        f"Results/significance notes supplied by the author:\n"
        + "\n\n---\n\n".join(results_texts)
        + "\n\nWrite the Results section using ONLY the above materials. "
        "Reference figures as 'Fig. 1', 'Fig. 2', etc. "
        "Do not invent data or add interpretations beyond what is stated."
    )

    result = chat([{"role": "user", "content": prompt}], system=SYSTEM, max_tokens=3000)
    append_section("manuscript_draft.docx", "Results", result)
    return result
