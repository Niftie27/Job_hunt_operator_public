#!/usr/bin/env python3
"""
JH Operator — ATS detector for quiet career_page sources
==========================================================
For every company in the QUIET_COMPANIES list (career_page sources
that returned 0 jobs in the last crypto run), probe Greenhouse,
Ashby, and Lever APIs with a few slug variants.

Usage (from project root):
    python3 tools/detect_ats_for_quiet.py

Output:
    - Console summary + ready-to-paste config.py entries
    - output/scans/ats-detection-quiet.json
"""

import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


# ── Quiet career_page sources from v0.9.12 source-health log ──
QUIET_COMPANIES = [
    "Phantom", "SatoshiLabs", "DFINITY", "FalconX", "Pod Network",
    "LangChain", "Pact", "WOOFi", "Zircuit", "Token Metrics",
    "Halborn", "Digital Asset", "Winnables", "Blaize", "Frax",
    "Taiko", "Arkham", "QuickNode", "Token Terminal", "Gemini",
    "Zerion",
]

OUTPUT_PATH    = Path("output/scans/ats-detection-quiet.json")
TIMEOUT        = 10
INTER_REQ_WAIT = 0.15  # between probes
COMPANY_WAIT   = 0.4   # between companies


# ── ATS endpoints ─────────────────────────────────────────────────────

ATS_ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{s}/jobs",
    "ashby":      "https://api.ashbyhq.com/posting-api/job-board/{s}",
    "lever":      "https://api.lever.co/v0/postings/{s}?mode=json",
}


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _fetch(url: str) -> tuple[int, str]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "JH-Operator/0.1 (ats-detector)"}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_ctx()) as resp:
            body = resp.read(65536).decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def _ats_response_valid(ats: str, body: str) -> bool:
    try:
        data = json.loads(body)
        if ats == "lever":
            return isinstance(data, list)
        return isinstance(data, dict) and "jobs" in data
    except Exception:
        return False


# ── Slug generation ─────────────────────────────────────────────────

def _slugs(name: str) -> list[str]:
    base = name.lower().strip()
    # strip a few common suffixes
    for suffix in (" labs", " network", " protocol", " finance",
                   " capital", " digital", " group", " inc", " inc."):
        if base.endswith(suffix):
            base = base[: -len(suffix)].strip()

    clean = re.sub(r"[^\w\s.-]", "", base)
    nospace = re.sub(r"[\s_-]+", "", clean)
    hyphen  = re.sub(r"[\s_]+", "-", clean)
    dot     = re.sub(r"[\s_]+", ".", clean)
    return list(dict.fromkeys(s for s in [nospace, hyphen, dot] if s))


def _job_count(ats: str, body: str) -> int:
    try:
        data = json.loads(body)
        if ats == "lever":
            return len(data) if isinstance(data, list) else 0
        return len(data.get("jobs", []))
    except Exception:
        return 0


def detect(company: str) -> dict:
    for ats, tmpl in ATS_ENDPOINTS.items():
        for slug in _slugs(company):
            url = tmpl.format(s=slug)
            status, body = _fetch(url)
            time.sleep(INTER_REQ_WAIT)
            if status == 200 and _ats_response_valid(ats, body):
                count = _job_count(ats, body)
                if count > 0:
                    return {
                        "company": company, "status": "found",
                        "ats": ats, "slug": slug, "url": url,
                        "jobs_count": count,
                    }
    return {"company": company, "status": "not_found",
            "ats": None, "slug": None, "url": None, "jobs_count": 0}


def main():
    print("=" * 60)
    print("  ATS DETECTION — QUIET CAREER_PAGE SOURCES")
    print(f"  Probing {len(QUIET_COMPANIES)} companies")
    print("=" * 60)
    print()

    results: list[dict] = []
    for name in QUIET_COMPANIES:
        print(f"  {name:<22} ... ", end="", flush=True)
        r = detect(name)
        if r["status"] == "found":
            print(f"✅ {r['ats']}/{r['slug']} ({r['jobs_count']} jobs)")
        else:
            print("❌ no ATS")
        results.append(r)
        time.sleep(COMPANY_WAIT)

    found = [r for r in results if r["status"] == "found"]
    miss  = [r for r in results if r["status"] != "found"]

    print()
    print("=" * 60)
    print(f"  RESULTS: {len(found)} found, {len(miss)} still no ATS")
    print("=" * 60)

    if found:
        print()
        print("=== Ready-to-paste config.py entries ===")
        print()
        for r in found:
            print(
                f'    {{"type": "{r["ats"]}", "id": "{r["slug"]}", '
                f'"name": "{r["company"]}", "category": "crypto"}},'
            )

    if miss:
        print()
        print("=== Still quiet (no ATS detected) ===")
        for r in miss:
            print(f"  {r['company']}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "checked": len(results),
                "found": len(found),
                "not_found": len(miss),
            },
            "results": results,
        }, f, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
