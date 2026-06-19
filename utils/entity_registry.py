import csv
import difflib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"


def _split_terms(value: str) -> list[str]:
    if not value:
        return []
    return [t.strip() for t in re.split(r"[|;,]\s*", value) if t.strip()]


def load_entity_registry() -> list[dict]:
    """
    Load controlled vocabulary from input/entity_registry.csv or .json.

    CSV columns:
    entity_type, canonical_name, allowed_aliases, forbidden_names, source
    """
    csv_path = INPUT_DIR / "entity_registry.csv"
    json_path = INPUT_DIR / "entity_registry.json"
    rows: list[dict] = []

    if csv_path.exists():
        with csv_path.open(newline="") as f:
            for row in csv.DictReader(f):
                rows.append({
                    "entity_type": (row.get("entity_type") or "").strip(),
                    "canonical_name": (row.get("canonical_name") or "").strip(),
                    "allowed_aliases": _split_terms(row.get("allowed_aliases") or ""),
                    "forbidden_names": _split_terms(row.get("forbidden_names") or ""),
                    "source": (row.get("source") or "").strip(),
                })
    elif json_path.exists():
        data = json.loads(json_path.read_text())
        for row in data if isinstance(data, list) else []:
            rows.append({
                "entity_type": str(row.get("entity_type", "")).strip(),
                "canonical_name": str(row.get("canonical_name", "")).strip(),
                "allowed_aliases": list(row.get("allowed_aliases") or []),
                "forbidden_names": list(row.get("forbidden_names") or []),
                "source": str(row.get("source", "")).strip(),
            })

    return [r for r in rows if r.get("canonical_name")]


def _term_present(text: str, term: str) -> bool:
    if not term:
        return False
    if re.search(r"[A-Za-z0-9]", term):
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None
    return term in text


def _candidate_terms(text: str) -> set[str]:
    candidates = set()
    for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9\-]{2,}\b", text):
        token = match.group(0)
        if any(c.isdigit() for c in token) or token.isupper() or "-" in token:
            candidates.add(token)
    return candidates


def audit_text(text: str, registry: list[dict] | None = None) -> list[dict]:
    registry = registry if registry is not None else load_entity_registry()
    if not registry:
        return []

    rows: list[dict] = []
    candidates = _candidate_terms(text)

    for entry in registry:
        canonical = entry["canonical_name"]
        aliases = entry.get("allowed_aliases", [])
        forbidden = entry.get("forbidden_names", [])

        if _term_present(text, canonical):
            rows.append({
                "keyword_in_draft": canonical,
                "canonical_term": canonical,
                "entity_type": entry.get("entity_type", ""),
                "status": "correct",
                "risk": "low",
                "action": "keep",
                "source": entry.get("source", ""),
            })

        for alias in aliases:
            if _term_present(text, alias):
                rows.append({
                    "keyword_in_draft": alias,
                    "canonical_term": canonical,
                    "entity_type": entry.get("entity_type", ""),
                    "status": "allowed_alias",
                    "risk": "low",
                    "action": "keep or normalize if journal requires canonical names",
                    "source": entry.get("source", ""),
                })

        for bad in forbidden:
            if _term_present(text, bad):
                rows.append({
                    "keyword_in_draft": bad,
                    "canonical_term": canonical,
                    "entity_type": entry.get("entity_type", ""),
                    "status": "forbidden_or_confusing",
                    "risk": "high",
                    "action": "human check; replace or explicitly distinguish",
                    "source": entry.get("source", ""),
                })

        watch_terms = [canonical] + aliases + forbidden
        for token in candidates:
            if token.lower() in {t.lower() for t in watch_terms}:
                continue
            for known in watch_terms:
                if len(known) < 5:
                    continue
                score = difflib.SequenceMatcher(None, token.lower(), known.lower()).ratio()
                if score >= 0.86:
                    rows.append({
                        "keyword_in_draft": token,
                        "canonical_term": canonical,
                        "entity_type": entry.get("entity_type", ""),
                        "status": f"near_miss_to:{known}",
                        "risk": "medium",
                        "action": "human check spelling/entity identity",
                        "source": entry.get("source", ""),
                    })
                    break

    seen = set()
    unique_rows = []
    for row in rows:
        key = (row["keyword_in_draft"].lower(), row["canonical_term"].lower(), row["status"])
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
    return unique_rows


def save_audit_report(rows: list[dict], label: str = "entity_audit") -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{label}.md"
    lines = [
        "# Entity Audit",
        "",
        "| Keyword in draft | Canonical term | Entity type | Status | Risk | Action | Source |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            "| {keyword_in_draft} | {canonical_term} | {entity_type} | {status} | {risk} | {action} | {source} |".format(
                **{k: str(v).replace("|", "/") for k, v in r.items()}
            )
        )
    if not rows:
        lines.append("| No registry-backed entity risks detected |  |  |  | low | keep |  |")
    path.write_text("\n".join(lines))
    return path


def audit_and_save(text: str, label: str = "entity_audit") -> list[dict]:
    rows = audit_text(text)
    save_audit_report(rows, label=label)
    return rows


def format_entity_constraints() -> str:
    registry = load_entity_registry()
    if not registry:
        return ""

    lines = [
        "CONTROLLED ENTITY REGISTRY — mandatory constraints:",
        "- Use canonical names or allowed aliases exactly as listed.",
        "- Do not invent synonyms for registered entities.",
        "- Do not use forbidden/confusing names unless explicitly distinguishing them as non-target entities.",
    ]
    for row in registry:
        aliases = "; ".join(row.get("allowed_aliases", [])) or "none"
        forbidden = "; ".join(row.get("forbidden_names", [])) or "none"
        source = row.get("source", "") or "unspecified source"
        lines.append(
            f"- {row.get('entity_type', 'Entity')}: canonical='{row['canonical_name']}'; "
            f"allowed_aliases='{aliases}'; forbidden_or_confusing='{forbidden}'; source='{source}'"
        )
    return "\n".join(lines)
