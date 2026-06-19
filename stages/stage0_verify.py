from pathlib import Path
from utils.figure_checker import (
    check_figure_caption_match,
    check_figure_sizes,
    get_figure_files,
    get_caption_files,
)

ROOT = Path(__file__).parent.parent
INPUT = ROOT / "input"


def run_verification() -> tuple[list[str], list[str], bool]:
    """
    Returns (errors, warnings, ok).
    errors block progress; warnings are informational.
    ok=True means all required folders have content and no errors.
    """
    errors: list[str] = []
    warnings: list[str] = []

    figures_dir = INPUT / "figures"
    captions_dir = INPUT / "captions"
    results_dir = INPUT / "results"
    methods_dir = INPUT / "methods"
    registry_path = INPUT / "entity_registry.csv"

    # Check folder existence
    for d in [figures_dir, captions_dir, results_dir, methods_dir]:
        if not d.exists():
            errors.append(f"Folder `{d.relative_to(ROOT)}` does not exist.")

    if errors:
        return errors, warnings, False

    # Check minimum content
    figs = get_figure_files(figures_dir)
    caps = get_caption_files(captions_dir)
    results_files = list(results_dir.glob("*.txt"))
    methods_files = list(methods_dir.glob("*.txt"))

    if not figs:
        errors.append("No figure files found in `input/figures/`.")
    if not caps:
        errors.append("No caption `.txt` files found in `input/captions/`.")
    if not results_files:
        errors.append("No `.txt` files found in `input/results/`.")
    if not methods_files:
        errors.append("No `.txt` files found in `input/methods/`.")

    if errors:
        return errors, warnings, False

    # Figure ↔ caption matching
    match_errors = check_figure_caption_match(figures_dir, captions_dir)
    errors.extend(match_errors)

    # Figure size warnings
    size_warnings = check_figure_sizes(figures_dir)
    warnings.extend(size_warnings)

    if registry_path.exists():
        try:
            from utils.entity_registry import load_entity_registry
            n_entities = len(load_entity_registry())
            warnings.append(
                f"Entity registry enabled with {n_entities} controlled term(s) from `input/entity_registry.csv`."
            )
        except Exception as e:
            warnings.append(f"Entity registry found but could not be parsed: {e}")
    else:
        warnings.append(
            "No active `input/entity_registry.csv` found. "
            "Entity grounding audit is optional but recommended; see `input/entity_registry.example.csv`."
        )

    ok = len(errors) == 0
    return errors, warnings, ok


def format_verification_report(errors: list[str], warnings: list[str], ok: bool) -> str:
    lines = ["## File Verification Report\n"]

    if ok:
        lines.append("✅ All required files are present and matched.\n")
    else:
        lines.append("❌ Errors found — please fix before continuing:\n")
        for e in errors:
            lines.append(f"  - ⛔ {e}")
        lines.append("")

    if warnings:
        lines.append("⚠️ Warnings (do not block progress):\n")
        for w in warnings:
            lines.append(f"  - ⚠️ {w}")
        lines.append("")

    if ok and warnings:
        lines.append("Files verified with warnings. Type `confirm` to continue.")
    elif ok:
        lines.append("Type `confirm` to proceed to Stage 1.")

    return "\n".join(lines)
