#!/usr/bin/env python3
"""
JH Operator — Find Career Pages for Tracker + Watchlist Companies
==================================================================
Reads data/tracker.csv AND data/watchlist.txt, extracts unique
company names, and discovers career page URLs / ATS types for
companies not already in config.py.

Usage (run from project root):
    python3 tools/find_tracker_careers.py

Output:
    - Console: summary + ready-to-paste config.py entries
    - output/scans/watchlist-careers-discovery.json
"""

import csv
import json
import os
import re
import sys
import time
import ssl
import urllib.request
import urllib.error
from pathlib import Path

# ─── Skip lists ───────────────────────────────────────────────────────
# Substring match (case-insensitive): skip if any token appears in name.

SKIP_AGENCIES = {
    "blockchain headhunter", "spectrum search", "hyphen connect",
    "jobited", "mcg talent", "weplacedyou", "blue whales agency",
    "nula advisory",
    # Watchlist additions
    "jersey road talent", "hays", "axiom recruit", "dada consultants",
    "career renew", "consol partners", "talentsync",
    "skillfinder international", "crossing hurdles", "jobgether",
    "radley james", "archon", "talentiq", "coolpeople",
    "fullstack talents", "techinborn", "ascendion", "zoolatech",
    "citadelo", "itmatch", "jobs contact", "collibra nv",
    "itis holding", "natek", "xevos", "nexer group", "elite chain",
    "saint-gobain", "red hat", "hcltech", "y soft", "bairesdev",
    "deel", "epam systems", "avenga",
}

SKIP_JOB_BOARDS = {
    "jooble (job board)",
}

SKIP_NON_REAL = {
    "project upwork", "contract",
}

# Big generic corps — would flood pipeline, not crypto-focused
SKIP_BIG_CORPS = {
    "microsoft", "google", "apple", "accenture", "deloitte", "pwc",
    "siemens", "vodafone", "honeywell", "barclays", "citi", "nvidia",
    "hewlett packard enterprise", "jetbrains", "intel", "ibm", "sap",
    "oracle", "rockwell", "thales",
}

# Czech banks / corporates rarely have crypto roles
SKIP_CZECH_BANKS = {
    "ceska sporitelna", "česká spořitelna", "komercni banka",
    "komerční banka", "csob", "čsob", "raiffeisenbank", "air bank",
    "moneta money bank", "czech national bank", "e.on", "eon",
    "commerzbank", "prima", "eset", "avast",
}

# Portfolio / umbrella entities (not a single hiring company)
SKIP_PORTFOLIO = {
    "ycombinator", "y combinator", "asteroid", "black dragon capital",
}

# All companies already tracked in config.py SOURCES (lowercased)
SKIP_IN_CONFIG = {
    "nethermind", "wormhole labs", "moonpay", "immutable",
    "anchorage digital", "injective", "ava labs", "chainalysis",
    "consensys", "offchain labs", "phantom", "layerzero",
    "satoshilabs", "alchemy", "chainlink", "kraken", "dydx",
    "opensea", "quicknode", "gemini", "dfinity", "zerion",
    "arkham", "falconx", "blockchain.com", "token terminal",
    "taiko", "frax", "blaize", "zircuit", "plume network",
    "woofi", "nansen", "bcb group", "ssv labs", "wormhole foundation",
    "dapper labs", "modular", "improbable", "devbrother",
    "paxos", "actis", "somnia", "make",
    # Tracker-specific aliases of the above
    "bcb",                     # BCB Group
    "wormhole",                # Wormhole Foundation / Labs
    "moonpay",                 # also "Moonpay" capitalisation variant
    "invity/trezor",           # SatoshiLabs product family
    "trezor",                  # SatoshiLabs product
    "invity",                  # SatoshiLabs product
    "kraken digital asset",    # Kraken
    "input output group",      # IOG (Cardano) — duplicate of Cardano-related, treat as in config
    "tether.io", "tether",
}

TRACKER_PATH   = Path("data/tracker.csv")
WATCHLIST_PATH = Path("data/watchlist.txt")
OUTPUT_PATH    = Path("output/scans/watchlist-careers-discovery.json")
ARCHIVED_PATH  = Path("data/watchlist-archived.txt")

# Map verbose reasons → short tag codes for archived file
REASON_TAGS = {
    "recruitment agency":   "agency",
    "big generic corp":     "corp",
    "czech bank/corp":      "bank",
    "already in config.py": "in_config",
    "portfolio/umbrella":   "umbrella",
    "rejected":             "unfit",
    "non-real company":     "unfit",
    "job board":            "unfit",
}

REQUEST_DELAY    = 0.5   # between companies
INTER_REQ_DELAY  = 0.2   # between individual HTTP probes
TIMEOUT          = 10


# ─── HTTP utilities ───────────────────────────────────────────────────

def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _fetch(url: str) -> tuple[int, str, str]:
    """Returns (status_code, final_url, body[:64k]). status=0 on network error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JH-Operator/0.1 (career-finder)"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_ctx()) as resp:
            body = resp.read(65536).decode("utf-8", errors="replace")
            return resp.status, resp.url, body
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        return 0, url, str(e)


# ─── Slug generation ─────────────────────────────────────────────────

def _slugs(name: str) -> list[str]:
    """Return candidate URL slugs for a company name (deduped, ordered)."""
    base = name.lower()
    # Strip common suffixes unlikely to appear in URLs
    for suffix in (" dao", " labs", " network", " protocol", " finance",
                   " capital", " digital", " systems", " group"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    clean   = re.sub(r"[^\w\s-]", "", base)          # drop punctuation
    nospace = re.sub(r"[\s_-]+", "", clean)           # "cowdao"
    hyphen  = re.sub(r"[\s_]+", "-", clean.strip())   # "cow-dao"
    return list(dict.fromkeys(s for s in [nospace, hyphen] if s))


# ─── Strategy A: URL guessing ─────────────────────────────────────────

_URL_TEMPLATES = [
    "https://{s}.com/careers",
    "https://{s}.com/jobs",
    "https://{s}.io/careers",
    "https://{s}.io/jobs",
    "https://{s}.xyz/careers",
    "https://www.{s}.com/careers",
    "https://careers.{s}.com",
    "https://jobs.{s}.com",
]


def _is_real_career_page(status: int, final_url: str, body: str) -> bool:
    """Return True only if the response looks like an actual career page, not homepage."""
    if status != 200:
        return False
    if "<html" not in body.lower():
        return False
    # If we were redirected back to a bare domain (e.g. example.com/ or example.com),
    # it's a homepage redirect — not a real career page.
    path = re.sub(r"https?://[^/]+", "", final_url).rstrip("/")
    if not path:
        return False
    return True


def try_url_guess(company: str) -> str | None:
    """Return the first plausible career-page URL (200 HTML, non-homepage), or None."""
    for slug in _slugs(company):
        for tmpl in _URL_TEMPLATES:
            url = tmpl.format(s=slug)
            status, final_url, body = _fetch(url)
            time.sleep(INTER_REQ_DELAY)
            if _is_real_career_page(status, final_url, body):
                return final_url
    return None


# ─── Strategy B: ATS API probing ─────────────────────────────────────

_ATS_ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{s}/jobs",
    "ashby":      "https://api.ashbyhq.com/posting-api/job-board/{s}",
    "lever":      "https://api.lever.co/v0/postings/{s}?mode=json",
}


def _ats_response_valid(ats_type: str, body: str) -> bool:
    try:
        data = json.loads(body)
        if ats_type == "lever":
            return isinstance(data, list)
        return isinstance(data, dict) and "jobs" in data
    except Exception:
        return False


def try_ats(company: str) -> tuple[str | None, str | None]:
    """Return (ats_type, slug) if a live ATS board is found, else (None, None)."""
    for slug in _slugs(company):
        for ats_type, tmpl in _ATS_ENDPOINTS.items():
            url = tmpl.format(s=slug)
            status, _, body = _fetch(url)
            time.sleep(INTER_REQ_DELAY)
            if status == 200 and _ats_response_valid(ats_type, body):
                return ats_type, slug
    return None, None


# ─── Source loading ──────────────────────────────────────────────────

def load_tracker_companies(path: Path) -> list[str]:
    seen: set[str] = set()
    companies: list[str] = []
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("company") or "").strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                companies.append(name)
    return companies


def load_watchlist_companies(path: Path) -> list[str]:
    seen: set[str] = set()
    companies: list[str] = []
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if not name or name.startswith("#"):
                continue
            if name.lower() not in seen:
                seen.add(name.lower())
                companies.append(name)
    return companies


def _has_token(haystack: str, needles: set[str]) -> bool:
    """Substring match: True if any needle appears anywhere in haystack."""
    return any(n in haystack for n in needles)


def skip_reason(name: str) -> str | None:
    nl = name.lower()
    if "(rejected)" in nl:
        return "rejected"
    if _has_token(nl, SKIP_IN_CONFIG):
        return "already in config.py"
    if _has_token(nl, SKIP_AGENCIES):
        return "recruitment agency"
    if _has_token(nl, SKIP_BIG_CORPS):
        return "big generic corp"
    if _has_token(nl, SKIP_CZECH_BANKS):
        return "czech bank/corp"
    if _has_token(nl, SKIP_PORTFOLIO):
        return "portfolio/umbrella"
    if nl in SKIP_JOB_BOARDS:
        return "job board"
    if nl in SKIP_NON_REAL:
        return "non-real company"
    return None


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    if not TRACKER_PATH.exists() and not WATCHLIST_PATH.exists():
        print(f"Error: neither {TRACKER_PATH} nor {WATCHLIST_PATH} found. "
              f"Run from project root.", file=sys.stderr)
        sys.exit(1)

    print("=" * 55)
    print("  WATCHLIST + TRACKER CAREER DISCOVERY")
    print("=" * 55)
    print()

    tracker_names   = load_tracker_companies(TRACKER_PATH)
    watchlist_names = load_watchlist_companies(WATCHLIST_PATH)

    # Merge, dedupe by lowercase name, preserve order (tracker first)
    seen_norm: set[str] = set()
    all_companies: list[str] = []
    for name in tracker_names + watchlist_names:
        nl = name.lower()
        if nl not in seen_norm:
            seen_norm.add(nl)
            all_companies.append(name)

    print(f"Total companies input: {len(all_companies)} "
          f"(tracker {len(tracker_names)} + watchlist {len(watchlist_names)})")

    to_check: list[str] = []
    skipped:  list[tuple[str, str]] = []
    for name in all_companies:
        reason = skip_reason(name)
        if reason:
            skipped.append((name, reason))
        else:
            to_check.append(name)

    print(f"Skipped (agencies/corps/duplicates): {len(skipped)}")
    print(f"Checking: {len(to_check)}")
    print()

    results: list[dict] = []

    for name in to_check:
        print(f"  {name:<30} ... ", end="", flush=True)
        time.sleep(REQUEST_DELAY)

        # ATS first — more authoritative than URL guess
        ats_type, slug = try_ats(name)
        if ats_type and slug:
            entry = f'{{"type": "{ats_type}", "id": "{slug}", "name": "{name}"}}'
            print(f"✅ {ats_type}/{slug}")
            results.append({
                "company": name, "status": "ready_ats",
                "ats_type": ats_type, "slug": slug,
                "url": _ATS_ENDPOINTS[ats_type].format(s=slug),
                "config_entry": entry,
            })
            continue

        career_url = try_url_guess(name)
        if career_url:
            entry = f'{{"type": "career_page", "id": "{career_url}", "name": "{name}"}}'
            print(f"⚠️  playwright → {career_url}")
            results.append({
                "company": name, "status": "ready_playwright",
                "ats_type": None, "slug": None,
                "url": career_url,
                "config_entry": entry,
            })
            continue

        print("❌ not found")
        results.append({
            "company": name, "status": "not_found",
            "ats_type": None, "slug": None, "url": None, "config_entry": None,
        })

    # ── Summary ──────────────────────────────────────────────────────
    ready_ats = [r for r in results if r["status"] == "ready_ats"]
    ready_pw  = [r for r in results if r["status"] == "ready_playwright"]
    not_found = [r for r in results if r["status"] == "not_found"]

    print()
    print("=" * 55)
    print("  RESULTS")
    print("=" * 55)
    print()
    print(f"Total companies in tracker: {len(all_companies)}")
    print(f"Skipped (agencies/rejected/duplicates): {len(skipped)}")
    print(f"Checked: {len(to_check)}")
    print()

    if ready_ats:
        print(f"✅ READY ATS ({len(ready_ats)}):")
        for r in ready_ats:
            print(f"  {r['company']} → {r['ats_type']}/{r['slug']}")
        print()

    if ready_pw:
        print(f"⚠️  READY PLAYWRIGHT ({len(ready_pw)}):")
        for r in ready_pw:
            print(f"  {r['company']} → {r['url']}")
        print()

    if not_found:
        print(f"❌ NOT FOUND ({len(not_found)}):")
        for r in not_found:
            print(f"  {r['company']}")
        print()

    print(f"⏭  SKIPPED ({len(skipped)}):")
    for name, reason in skipped:
        print(f"  {name} ({reason})")
    print()

    # ── Copy-paste block ──────────────────────────────────────────────
    print()
    print("=== Copy-paste for config.py ===")
    print()
    if ready_ats:
        print("# ── New ATS sources from tracker ──")
        for r in ready_ats:
            print(f"    {r['config_entry']},")
        print()
    if ready_pw:
        print("# ── New career_page sources from tracker ──")
        for r in ready_pw:
            print(f"    {r['config_entry']},")
        print()

    # ── Save JSON ─────────────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "summary": {
            "total_in_tracker": len(all_companies),
            "skipped": len(skipped),
            "checked": len(to_check),
            "ready_ats": len(ready_ats),
            "ready_playwright": len(ready_pw),
            "not_found": len(not_found),
        },
        "results": results,
        "skipped": [{"company": n, "reason": r} for n, r in skipped],
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Saved to {OUTPUT_PATH}")

    # ── Save archived watchlist ───────────────────────────────────────
    ARCHIVED_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Group by tag for stable, scannable output
    by_tag: dict[str, list[str]] = {}
    for name, reason in skipped:
        tag = REASON_TAGS.get(reason, "unfit")
        by_tag.setdefault(tag, []).append(name)
    tag_order = ["corp", "bank", "agency", "in_config", "umbrella", "unfit"]
    lines = [
        "# Companies from watchlist/tracker that were skipped from career discovery",
        "# Reason codes: agency, corp, bank, in_config, umbrella, unfit",
        "",
    ]
    for tag in tag_order:
        names = sorted(by_tag.get(tag, []), key=str.lower)
        for name in names:
            lines.append(f"{name:<32}# {tag}")
        if names:
            lines.append("")
    with open(ARCHIVED_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    print(f"Saved to {ARCHIVED_PATH}")


if __name__ == "__main__":
    main()
