import hashlib
import json
import re
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"


DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
PMID_RE = re.compile(r"\bPMID\s*:?\s*(\d{5,12})\b", re.IGNORECASE)
ARXIV_RE = re.compile(r"\barXiv\s*:?\s*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _clean(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_doi(raw: str) -> str:
    doi = _clean(raw)
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi\s*:\s*", "", doi, flags=re.IGNORECASE)
    return doi.rstrip(".,;").lower()


def extract_doi(text: str) -> str:
    match = DOI_RE.search(text or "")
    return normalize_doi(match.group(0)) if match else ""


def extract_pmid(text: str) -> str:
    match = PMID_RE.search(text or "")
    return match.group(1) if match else ""


def extract_arxiv(text: str) -> str:
    match = ARXIV_RE.search(text or "")
    return match.group(1).lower() if match else ""


def normalize_title(title: str) -> str:
    title = re.sub(r"<[^>]+>", "", title or "")
    title = re.sub(r"[*_`#]", "", title)
    title = re.sub(r"[^a-zA-Z0-9]+", " ", title).lower()
    return re.sub(r"\s+", " ", title).strip()


def _hash(value: str, length: int = 14) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def _field_from_lines(lines: list[str], label: str) -> str:
    prefix = label.lower() + ":"
    for line in lines:
        if line.lower().startswith(prefix):
            return _clean(line.split(":", 1)[1])
    return ""


def _title_from_raw(raw: str) -> str:
    lines = [_clean(l) for l in raw.splitlines() if _clean(l)]
    if not lines:
        return ""
    for line in lines:
        if re.match(r"^(authors?|doi|pmid|relevance|source|journal|year)\s*:", line, re.I):
            continue
        line = re.sub(r"^\[?\d+\]?[\.\)]\s*", "", line)
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        if len(line) > 6:
            return line
    return lines[0]


def canonicalize_reference(ref: str | dict) -> dict:
    """Turn a free-text or structured reference into a stable reference record."""
    if isinstance(ref, dict):
        raw = _clean(ref.get("raw") or ref.get("reference") or "")
        title = _clean(ref.get("title"))
        authors = _clean(ref.get("authors"))
        journal = _clean(ref.get("journal"))
        year = _clean(ref.get("year"))
        doi = normalize_doi(ref.get("doi", ""))
        pmid = _clean(ref.get("pmid"))
        arxiv_id = _clean(ref.get("arxiv_id") or ref.get("arxiv"))
        source_url = _clean(ref.get("source_url"))
        if not raw:
            raw = " ".join(v for v in [title, authors, journal, year, doi, pmid, source_url] if v)
    else:
        raw = _clean(ref)
        lines = [_clean(l) for l in raw.splitlines() if _clean(l)]
        title = _title_from_raw(raw)
        authors = _field_from_lines(lines, "Authors")
        journal = _field_from_lines(lines, "Journal")
        year = _field_from_lines(lines, "Year")
        doi = extract_doi(raw)
        pmid = extract_pmid(raw)
        arxiv_id = extract_arxiv(raw)
        source_url = _field_from_lines(lines, "Source")

    if not year:
        match = YEAR_RE.search(raw)
        year = match.group(0) if match else ""

    title_norm = normalize_title(title)
    if doi:
        canonical_id = f"doi:{doi}"
        confidence = "high"
        needs_review = False
        review_reason = ""
    elif pmid:
        canonical_id = f"pmid:{pmid}"
        confidence = "high"
        needs_review = False
        review_reason = ""
    elif arxiv_id:
        canonical_id = f"arxiv:{arxiv_id}"
        confidence = "high"
        needs_review = False
        review_reason = ""
    elif title_norm:
        canonical_id = f"title:{_hash(title_norm)}"
        confidence = "medium" if year else "low"
        needs_review = True
        review_reason = "No DOI/PMID/arXiv ID; deduped by normalized title hash."
    else:
        canonical_id = f"raw:{_hash(raw)}"
        confidence = "low"
        needs_review = True
        review_reason = "Could not identify a title or persistent identifier."

    short_bits = []
    if authors:
        short_bits.append(authors.split(";")[0].split(",")[0])
    if year:
        short_bits.append(year)
    short_citation = ", ".join(short_bits) if short_bits else title[:80]

    return {
        "canonical_reference_id": canonical_id,
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "doi": doi,
        "pmid": pmid,
        "arxiv_id": arxiv_id,
        "source_url": source_url,
        "short_citation": short_citation,
        "raw": raw,
        "confidence": confidence,
        "needs_review": needs_review,
        "review_reason": review_reason,
        "aliases": [],
    }


def parse_reference_bullets(bullets: list[str]) -> list[dict]:
    records = []
    for bullet in bullets:
        lines = [_clean(l) for l in str(bullet).splitlines() if _clean(l)]
        data = {
            "title": _title_from_raw(str(bullet)),
            "authors": _field_from_lines(lines, "Authors"),
            "doi": _field_from_lines(lines, "DOI"),
            "raw": str(bullet),
        }
        records.append(canonicalize_reference(data))
    return records


def merge_reference_records(existing: list[dict | str] | None, new_items: list[dict | str]) -> list[dict]:
    table: dict[str, dict] = {}
    for item in (existing or []) + (new_items or []):
        record = item if isinstance(item, dict) else canonicalize_reference(item)
        if "canonical_reference_id" not in record:
            record = canonicalize_reference(record)
        key = record["canonical_reference_id"]
        if key in table:
            old = table[key]
            raw = record.get("raw", "")
            if raw and raw != old.get("raw", "") and raw not in old.get("aliases", []):
                old.setdefault("aliases", []).append(raw)
            for field in ("title", "authors", "year", "journal", "doi", "pmid", "arxiv_id", "source_url", "short_citation"):
                if not old.get(field) and record.get(field):
                    old[field] = record[field]
            old["needs_review"] = old.get("needs_review", False) or record.get("needs_review", False)
            if record.get("review_reason") and record["review_reason"] not in old.get("review_reason", ""):
                old["review_reason"] = "; ".join(x for x in [old.get("review_reason", ""), record["review_reason"]] if x)
        else:
            table[key] = record
    return list(table.values())


def load_reference_table() -> list[dict]:
    path = OUTPUT_DIR / "canonical_references.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_reference_table(records: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "canonical_references.json"
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False))

    md = ["# Canonical References\n"]
    uncertain = ["# Uncertain References\n"]
    for i, r in enumerate(records, 1):
        ident = r.get("canonical_reference_id", "")
        display = reference_display(r)
        md.append(f"{i}. `{ident}` — {display}")
        if r.get("needs_review"):
            uncertain.append(
                f"{i}. `{ident}` — {display}\n"
                f"   - Review reason: {r.get('review_reason', 'Manual review required.')}"
            )
    (OUTPUT_DIR / "canonical_references.md").write_text("\n".join(md))
    (OUTPUT_DIR / "uncertain_references.md").write_text("\n".join(uncertain))


def reference_display(record: dict) -> str:
    if record.get("raw"):
        return _clean(record["raw"])
    parts = [record.get("authors"), record.get("title"), record.get("journal"), record.get("year")]
    if record.get("doi"):
        parts.append(f"DOI: {record['doi']}")
    if record.get("pmid"):
        parts.append(f"PMID: {record['pmid']}")
    return ". ".join(_clean(p).rstrip(".") for p in parts if _clean(p))


def bibliography_from_table(records: list[dict]) -> list[str]:
    return [reference_display(r) for r in records]


def format_sources_for_prompt(records: list[dict]) -> str:
    lines = []
    for i, record in enumerate(records, 1):
        lines.append(
            f"[SOURCE {i}] {record.get('canonical_reference_id')}\n"
            f"Title: {record.get('title') or '[unknown title]'}\n"
            f"Authors: {record.get('authors') or '[unknown authors]'}\n"
            f"Year: {record.get('year') or '[unknown year]'}\n"
            f"Journal: {record.get('journal') or '[unknown journal]'}\n"
            f"DOI: {record.get('doi') or 'N/A'}\n"
            f"Raw source note: {record.get('raw')}"
        )
    return "\n\n".join(lines)
