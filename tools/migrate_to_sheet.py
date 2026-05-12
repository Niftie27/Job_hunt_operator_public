#!/usr/bin/env python3
"""
JH Operator — One-time migration helper

Reads current config.py SOURCES + data/watchlist.txt + data/watchlist-archived.txt
and prints CSV rows ready to paste into the JH_Jobs_Sources Google Sheet.

Sheet columns: Company,URL,Type,Category,Notes

Usage (from project root):
    python3 tools/migrate_to_sheet.py > /tmp/jh_jobs_sources_seed.csv
    # then open /tmp/jh_jobs_sources_seed.csv and paste rows into the sheet
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

WATCHLIST_PATH          = ROOT / "data" / "watchlist.txt"
WATCHLIST_ARCHIVED_PATH = ROOT / "data" / "watchlist-archived.txt"


def _config_entry_to_row(src: dict) -> tuple[str, str, str, str, str]:
    """Map a config.py SOURCES entry → (Company, URL, Type, Category, Notes)."""
    name     = src.get("name", "")
    category = src.get("category", "crypto")
    t        = src["type"]
    sid      = src["id"]
    notes    = ""

    if t == "greenhouse":
        return (name, f"greenhouse:{sid}", "ats", category, notes)
    if t == "ashby":
        return (name, f"ashby:{sid}", "ats", category, notes)
    if t == "lever":
        return (name, f"lever:{sid}", "ats", category, notes)
    if t == "career_page":
        loc = src.get("default_location", "")
        if loc:
            notes = f"default_location={loc}"
        return (name, sid, "career_page", category, notes)
    if t == "career_page_jina":
        loc = src.get("default_location", "")
        if loc:
            notes = f"default_location={loc}"
        return (name, sid, "career_page_jina", category, notes)
    if t == "career_page_llm":
        return (name, sid, "career_page_llm", category, "inactive (v0.9.16 pilot)")
    if t == "web3career":
        return (name, f"web3career:{sid}", "aggregator", category, notes)
    if t == "cryptojobslist":
        return (name, f"cryptojobslist:{sid}", "aggregator", category, notes)
    if t == "cryptocurrencyjobs":
        return (name, f"cryptocurrencyjobs:{sid}", "aggregator", category, notes)
    if t == "getro":
        return (name, f"getro:{sid}", "aggregator", category, notes)

    return (name, sid, t, category, notes)


def _load_watchlist() -> list[str]:
    if not WATCHLIST_PATH.exists():
        return []
    out: list[str] = []
    with open(WATCHLIST_PATH, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out


def _load_watchlist_archived() -> list[tuple[str, str]]:
    """Return [(Company, reason_tag)] from watchlist-archived.txt."""
    out: list[tuple[str, str]] = []
    if not WATCHLIST_ARCHIVED_PATH.exists():
        return out
    with open(WATCHLIST_ARCHIVED_PATH, encoding="utf-8") as f:
        for line in f:
            s = line.rstrip()
            if not s or s.startswith("#"):
                continue
            m = re.match(r"^(.+?)\s+#\s*(\S+)\s*$", s)
            if m:
                out.append((m.group(1).strip(), m.group(2).strip()))
            else:
                out.append((s.strip(), ""))
    return out


def main():
    from config import SOURCES

    writer = csv.writer(sys.stdout)
    writer.writerow(["Company", "URL", "Type", "Category", "Notes"])

    seen: set[str] = set()
    for src in SOURCES:
        row = _config_entry_to_row(src)
        key = (row[0].lower(), row[1].lower())
        if key in seen:
            continue
        seen.add(key)
        writer.writerow(row)

    # Watchlist (active) → name_only
    for company in _load_watchlist():
        key = (company.lower(), "")
        if key in seen:
            continue
        seen.add(key)
        writer.writerow([company, "", "name_only", "crypto", ""])

    # Watchlist (archived) → excluded (we consciously chose not to monitor).
    # Reserve `dead` for URLs that 404 / domain expired.
    for company, reason in _load_watchlist_archived():
        key = (company.lower(), "")
        if key in seen:
            continue
        seen.add(key)
        writer.writerow([company, "", "excluded", "general", f"archived: {reason}"])


if __name__ == "__main__":
    main()
