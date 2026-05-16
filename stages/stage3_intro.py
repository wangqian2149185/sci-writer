from pathlib import Path
from utils.claude_client import chat_with_web_search, chat
from utils.doc_builder import save_intro_bullets, append_section, save_references_md

ROOT = Path(__file__).parent.parent

SEARCH_SYSTEM = (
    "You are a scientific literature researcher. Search for peer-reviewed publications "
    "relevant to the provided keywords. For each finding, state the fact/claim, "
    "the citation (Author, Journal, Year, DOI), and a one-sentence relevance note. "
    "Only report real, verifiable published literature."
)

INTRO_SYSTEM = (
    "You are a scientific manuscript assistant. Write a formal, peer-reviewed Introduction section. "
    "Use ONLY the bullet points and results provided. Structure: "
    "(a) field background, (b) existing gaps/problems, (c) what this paper does. "
    "Use superscript numbers [¹ ² ³] for citations. "
    "Target 800–2000 words. Never hallucinate citations."
)


def research_intro(keywords: str, results_text: str) -> tuple[list[str], str]:
    """
    Performs web search and returns (bullets_list, display_text).
    """
    prompt = (
        f"Search for peer-reviewed literature relevant to these keywords: {keywords}\n\n"
        f"Context from the manuscript's Results section:\n{results_text[:1500]}\n\n"
        "Generate a numbered bullet list. Each bullet:\n"
        "1. States one finding or fact from published literature\n"
        "2. Includes citation: (Author et al., Journal, Year, DOI if available)\n"
        "3. Is drawn ONLY from real peer-reviewed sources found via search\n\n"
        "Aim for at least 40 bullets to give the author plenty to choose from."
    )

    response, _ = chat_with_web_search(prompt, system=SEARCH_SYSTEM, max_tokens=8192)

    # Parse bullets from response
    bullets = []
    for line in response.split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
            # Strip leading number/bullet
            import re
            clean = re.sub(r"^[\d\.\-\•\*]+\s*", "", line).strip()
            if clean:
                bullets.append(clean)

    save_intro_bullets(bullets)

    display = "## Introduction Research Bullets (Stage 3)\n\n"
    for i, b in enumerate(bullets, 1):
        display += f"{i}. {b}\n"
    display += "\n\nPlease review these bullets. Reply with the numbers you want to include, e.g.: `1,3,5,7,12`"

    return bullets, display


def write_introduction(
    selected_bullets: list[str],
    results_text: str,
    references: list[str],
) -> tuple[str, list[str]]:
    """
    Writes Introduction from selected bullets.
    Returns (intro_text, updated_references).
    """
    bullets_text = "\n".join(f"{i+1}. {b}" for i, b in enumerate(selected_bullets))

    prompt = (
        f"Write an Introduction for a scientific manuscript.\n\n"
        f"Use these literature bullets as your source material:\n{bullets_text}\n\n"
        f"Results section context:\n{results_text[:1500]}\n\n"
        "Requirements:\n"
        "- 800–2000 words\n"
        "- At least 30 in-text citations using superscript numbers ¹ ² ³\n"
        "- Structure: (a) field background, (b) existing gaps/problems, "
        "(c) what this paper does (tie to Results)\n"
        "- After the Introduction text, add a 'References' section listing all cited sources "
        "in numbered format matching the superscript numbers\n"
        "- Only cite the sources provided in the bullets above"
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

    all_refs = references + new_refs
    save_references_md(all_refs)
    append_section("manuscript_draft.docx", "Introduction", intro_text)

    return intro_text, all_refs
