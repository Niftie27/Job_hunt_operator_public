#!/usr/bin/env python3
"""
JH Operator — Sync config.py SOURCES from JH_Jobs_Sources Google Sheet

The Sheet is the source of truth for what the pipeline fetches.
Sheet must be shared "Anyone with the link → Viewer".

Schema (Sheet columns):
    Company,URL,Type,Category,Notes

Type values (routed to config.py / watchlist / pending log):
    career_page         → SOURCES entry, type=career_page, id=URL
    career_page_jina    → SOURCES entry, type=career_page_jina, id=URL
                          (Notes can contain "default_location=…")
    ats                 → SOURCES entry; URL = "<provider>:<slug>"
                          (greenhouse/ashby/lever)
    aggregator          → SOURCES entry; URL = "<provider>:<slug>"
                          (web3career/cryptojobslist/cryptocurrencyjobs/getro)
    name_only           → data/watchlist.txt
    pending_apify       → output/scans/pending-integrations.md
    pending_parser      → output/scans/pending-integrations.md
    dead                → output/scans/pending-integrations.md (archived)
    (empty/unknown)     → output/scans/needs-classification.md

Safety: refuses to rewrite config.py if the Sheet yields < 10 valid
ats/career_page/career_page_jina/aggregator entries.

Usage (from project root):
    python3 tools/sync_from_JH_Jobs_links.py
"""

import csv
import io
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH        = ROOT / "config.py"
WATCHLIST_PATH     = ROOT / "data" / "watchlist.txt"
PENDING_PATH       = ROOT / "output" / "scans" / "pending-integrations.md"
NEEDS_CLASS_PATH   = ROOT / "output" / "scans" / "needs-classification.md"

SHEET_ID  = "1RL60W_ntgdzHLGHHVcK-vM_5cJhKvXFqKRpxhwVp83A"
SHEET_GID = "0"
# Google's /export endpoint returns 400 for some "Anyone with link" sheets
# (known quirk). The gviz/tq endpoint honors the same sharing scope and
# reliably returns CSV — so we use that.
SHEET_EXPORT_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&gid={SHEET_GID}"
)

BEGIN_MARKER = "    # AUTO-GENERATED SOURCES BEGIN — do not edit manually (sync_from_JH_Jobs_links.py rewrites this block)"
END_MARKER   = "    # AUTO-GENERATED SOURCES END"

MIN_VALID_SOURCES = 10  # safety guard


# ── URL parsing helpers ──────────────────────────────────────────────

_ATS_PROVIDERS        = {"greenhouse", "ashby", "lever"}
_AGGREGATOR_PROVIDERS = {"web3career", "cryptojobslist", "cryptocurrencyjobs", "getro"}

# Patterns for auto-detection when URL is a full https URL instead of "provider:slug"
_URL_DETECTORS = [
    (re.compile(r"boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([\w.-]+)"), "greenhouse"),
    (re.compile(r"job-boards(?:\.eu)?\.greenhouse\.io/([\w.-]+)"),             "greenhouse"),
    (re.compile(r"jobs\.ashbyhq\.com/([\w.-]+)"),                              "ashby"),
    (re.compile(r"api\.ashbyhq\.com/posting-api/job-board/([\w.-]+)"),         "ashby"),
    (re.compile(r"jobs\.lever\.co/([\w.-]+)"),                                 "lever"),
    (re.compile(r"api\.lever\.co/v0/postings/([\w.-]+)"),                      "lever"),
]


def _parse_provider_slug(url: str) -> tuple[str, str] | None:
    """Return (provider, slug) or None. Accepts 'provider:slug' or full URL."""
    if not url:
        return None
    if ":" in url and not url.startswith(("http://", "https://")):
        provider, slug = url.split(":", 1)
        return (provider.strip().lower(), slug.strip())
    for pat, provider in _URL_DETECTORS:
        m = pat.search(url)
        if m:
            return (provider, m.group(1))
    return None


def _parse_default_location(notes: str) -> str:
    if not notes:
        return ""
    m = re.search(r"default_location\s*=\s*(.+)", notes)
    return m.group(1).strip() if m else ""


# ── Sheet download ───────────────────────────────────────────────────

def _download_sheet() -> list[dict]:
    try:
        with urllib.request.urlopen(SHEET_EXPORT_URL, timeout=30) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"⚠ Failed to download sheet: {e}", file=sys.stderr)
        return []

    reader = csv.DictReader(io.StringIO(data))
    return [dict(r) for r in reader if (r.get("Company") or "").strip()]


# ── Row routing ──────────────────────────────────────────────────────

def _row_to_source(row: dict) -> dict | None:
    """Convert a Sheet row to a SOURCES entry, or None if not routable."""
    name     = (row.get("Company") or "").strip()
    url      = (row.get("URL")     or "").strip()
    rtype    = (row.get("Type")    or "").strip().lower()
    category = (row.get("Category") or "crypto").strip() or "crypto"
    notes    = (row.get("Notes")   or "").strip()

    if not name:
        return None

    if rtype == "career_page":
        if not url:
            return None
        entry = {"type": "career_page", "id": url, "name": name, "category": category}
        loc = _parse_default_location(notes)
        if loc:
            entry["default_location"] = loc
        return entry

    if rtype == "career_page_jina":
        if not url:
            return None
        entry = {"type": "career_page_jina", "id": url, "name": name, "category": category}
        loc = _parse_default_location(notes)
        if loc:
            entry["default_location"] = loc
        return entry

    if rtype == "ats":
        ps = _parse_provider_slug(url)
        if not ps or ps[0] not in _ATS_PROVIDERS:
            return None
        provider, slug = ps
        return {"type": provider, "id": slug, "name": name, "category": category}

    if rtype == "aggregator":
        ps = _parse_provider_slug(url)
        if not ps or ps[0] not in _AGGREGATOR_PROVIDERS:
            return None
        provider, slug = ps
        return {"type": provider, "id": slug, "name": name, "category": category}

    return None


def _emit_dict_literal(entry: dict) -> str:
    """Emit a SOURCES entry as a Python dict literal with stable key order."""
    key_order = ["type", "id", "name", "default_location", "category"]
    parts = []
    for k in key_order:
        if k in entry:
            parts.append(f'"{k}": {repr(entry[k])}')
    return "{" + ", ".join(parts) + "}"


# ── config.py rewriting ──────────────────────────────────────────────

def _rewrite_config_sources(entries: list[dict]):
    text = CONFIG_PATH.read_text(encoding="utf-8")
    if BEGIN_MARKER not in text or END_MARKER not in text:
        print(
            "⚠ config.py is missing AUTO-GENERATED markers. Add this block "
            "around the SOURCES list (inside `SOURCES = [` … `]`):\n\n"
            f"{BEGIN_MARKER}\n    {END_MARKER}\n\n"
            "Then re-run.", file=sys.stderr,
        )
        sys.exit(2)

    lines = ["    # ── crypto sources ──"]
    crypto = [e for e in entries if e.get("category") != "general"]
    general = [e for e in entries if e.get("category") == "general"]
    for e in crypto:
        lines.append(f"    {_emit_dict_literal(e)},")
    if general:
        lines.append("")
        lines.append("    # ── general sources (--mode all) ──")
        for e in general:
            lines.append(f"    {_emit_dict_literal(e)},")

    block = "\n".join(lines)
    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    new_text = pattern.sub(BEGIN_MARKER + "\n" + block + "\n" + END_MARKER, text)
    CONFIG_PATH.write_text(new_text, encoding="utf-8")


# ── Outputs ──────────────────────────────────────────────────────────

def _write_watchlist(names: list[str]):
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        for n in sorted(set(names), key=str.lower):
            f.write(n + "\n")


def _write_pending(buckets: dict[str, list[tuple[str, str]]]):
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = ["# Pending Integrations", "",
           "Generated by tools/sync_from_JH_Jobs_links.py", ""]
    for bucket, label in [
        ("pending_apify",  "Pending — Apify scraper needed"),
        ("pending_parser", "Pending — custom parser needed"),
        ("dead",           "Archived (dead/unfit)"),
    ]:
        items = buckets.get(bucket, [])
        out += [f"## {label} ({len(items)})", ""]
        for name, note in sorted(items, key=lambda x: x[0].lower()):
            out.append(f"- **{name}**" + (f" — {note}" if note else ""))
        out.append("")
    PENDING_PATH.write_text("\n".join(out), encoding="utf-8")


def _write_needs_classification(rows: list[dict]):
    NEEDS_CLASS_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = ["# Sources Sheet — Needs Classification", "",
           "Rows with empty or unknown Type. Edit the Sheet, then re-sync.", ""]
    for r in rows:
        out.append(
            f"- **{r.get('Company','?')}** | URL: `{r.get('URL','')}` "
            f"| Type: `{r.get('Type','')}` | Notes: {r.get('Notes','')}"
        )
    NEEDS_CLASS_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("Downloading JH_Jobs_Sources sheet…")
    rows = _download_sheet()
    if not rows:
        print("⚠ Sheet returned no rows. Refusing to overwrite config.py / watchlist.")
        sys.exit(1)

    print(f"  rows: {len(rows)}")

    source_entries: list[dict] = []
    watchlist:      list[str]  = []
    buckets: dict[str, list[tuple[str, str]]] = {
        "pending_apify": [], "pending_parser": [], "dead": [],
    }
    needs_class: list[dict] = []

    for r in rows:
        rtype = (r.get("Type") or "").strip().lower()
        name  = (r.get("Company") or "").strip()
        notes = (r.get("Notes") or "").strip()

        if rtype in {"career_page", "career_page_jina", "ats", "aggregator"}:
            entry = _row_to_source(r)
            if entry:
                source_entries.append(entry)
            else:
                needs_class.append(r)
        elif rtype == "name_only":
            if name:
                watchlist.append(name)
        elif rtype in {"pending_apify", "pending_parser", "dead"}:
            buckets[rtype].append((name, notes))
        else:
            needs_class.append(r)

    if len(source_entries) < MIN_VALID_SOURCES:
        print(
            f"⚠ Only {len(source_entries)} valid source entries — refusing "
            f"to rewrite config.py (need at least {MIN_VALID_SOURCES}). "
            "Check the Sheet has data and Type values are valid."
        )
        sys.exit(1)

    _rewrite_config_sources(source_entries)
    _write_watchlist(watchlist)
    _write_pending(buckets)
    _write_needs_classification(needs_class)

    print()
    print(f"✅ config.py SOURCES rewritten: {len(source_entries)} entries")
    print(f"   crypto: {sum(1 for e in source_entries if e.get('category') != 'general')}")
    print(f"   general: {sum(1 for e in source_entries if e.get('category') == 'general')}")
    print(f"✅ data/watchlist.txt rewritten: {len(set(watchlist))} companies")
    print(f"✅ {PENDING_PATH.relative_to(ROOT)}: "
          f"{sum(len(v) for v in buckets.values())} archived/pending entries")
    if needs_class:
        print(f"⚠  {NEEDS_CLASS_PATH.relative_to(ROOT)}: "
              f"{len(needs_class)} rows need classification in the Sheet")


if __name__ == "__main__":
    main()
