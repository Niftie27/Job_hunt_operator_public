#!/usr/bin/env python3
"""
JH Operator — Daily Run
========================
This is the script you run. It does everything:

    python3 run.py

What happens:
1. Reads your source list from config.py
2. Fetches jobs from each source (Greenhouse, Ashby, Lever, job boards)
3. Removes duplicate listings within the batch
4. Checks each lead against your outreach tracker
5. Scores every lead by keyword relevance
6. Generates a markdown report in output/

That's the whole loop. No magic, no agents, no AI — just fetch, compare, score, report.
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

from config import SOURCES, OUTPUT_DIR, TRACKER_PATH
from fetchers import fetch_source
from pipeline import (
    load_tracker,
    dedupe_within_batch,
    dedupe_against_tracker,
    classify_all,
    generate_report,
)
from state import load_state, save_state, update_state


def main():
    parser = argparse.ArgumentParser(description="JH Operator — Daily Run")
    parser.add_argument(
        "--mode",
        choices=["crypto", "all"],
        default="crypto",
        help="Which sources to fetch: crypto (default) or all (includes general tech)",
    )
    args = parser.parse_args()

    if args.mode == "crypto":
        sources_to_fetch = [s for s in SOURCES if s.get("category", "crypto") == "crypto"]
    else:
        sources_to_fetch = SOURCES

    print("=" * 60)
    print("  JH Operator — Daily Intake Run")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Mode: {args.mode}  ({len(sources_to_fetch)} sources)")
    print("=" * 60)
    print()

    # ── Step 1: Fetch from selected sources ──
    print("📡 Step 1: Fetching from sources...")
    all_leads = []
    sources_ok = 0
    sources_failed = 0
    errors = []
    source_stats: list[dict] = []

    for source in sources_to_fetch:
        url = _resolve_source_url(source)
        try:
            jobs = fetch_source(source)
            count = len(jobs) if jobs else 0
            all_leads.extend(jobs or [])
            sources_ok += 1
            print(f"     ✓ {source['name']}: {count} jobs")
            source_stats.append({
                "name": source["name"], "type": source["type"],
                "url": url, "fetched": count, "error": None,
            })
        except Exception as e:
            sources_failed += 1
            err_msg = f"{source['name']}: {e}"
            errors.append(err_msg)
            print(f"     ✗ {err_msg}")
            source_stats.append({
                "name": source["name"], "type": source["type"],
                "url": url, "fetched": 0, "error": str(e),
            })

        # Be polite: don't hammer APIs too fast
        time.sleep(0.5)

    save_source_health(source_stats, args.mode)

    print(f"\n  Total raw leads: {len(all_leads)}")
    print(f"  Sources OK: {sources_ok}, Failed: {sources_failed}")
    
    if not all_leads:
        print("\n❌ No leads fetched. Check your network/sources.")
        print("   If you're running this locally without internet, that's expected.")
        print("   The pipeline will work when run on the VPS with internet access.")
        # Still generate an empty report so the file exists
        fetch_stats = {
            "total_fetched": 0,
            "sources_ok": sources_ok,
            "sources_failed": sources_failed,
            "errors": errors,
        }
        report = generate_report([], fetch_stats)
        _save_report(report, args.mode)
        return
    
    # ── Step 2: Dedupe within batch ──
    print("\n🔍 Step 2: Removing duplicates within batch...")
    before = len(all_leads)
    all_leads = dedupe_within_batch(all_leads)
    after = len(all_leads)
    print(f"  {before} → {after} (removed {before - after} duplicates)")
    
    # ── Step 3: Check against tracker ──
    print("\n📋 Step 3: Checking against outreach tracker...")
    tracker = load_tracker(TRACKER_PATH)
    print(f"  Tracker has {len(tracker)} historical entries")
    all_leads = dedupe_against_tracker(all_leads, tracker)
    known = sum(1 for l in all_leads if l.get("tracker_match"))
    print(f"  Known companies in this batch: {known}")

    # ── Step 4: Compare against state (memory) ──
    print("\n🧠 Step 4: Comparing against previous runs...")
    state_path = _state_path(args.mode)
    old_state = load_state(state_path)
    print(f"  Previous state has {len(old_state)} known roles ({state_path})")
    new_state, all_leads = update_state(all_leads, old_state)
    new_leads = sum(1 for l in all_leads if l.get("freshness") == "new")
    still_open = sum(1 for l in all_leads if l.get("freshness") == "still_open")
    print(f"  🆕 New: {new_leads}  |  Still open: {still_open}")

    # ── Step 5: Classify ──
    print("\n⚡ Step 5: Classifying leads...")
    all_leads = classify_all(all_leads)
    eng = sum(1 for l in all_leads if l["role_type"] == "engineering" and l["seniority"] in ("junior", "mid", "unclear"))
    senior_eng = sum(1 for l in all_leads if l["role_type"] == "engineering" and l["seniority"] in ("senior", "lead"))
    non_eng = sum(1 for l in all_leads if l["role_type"] == "non_engineering")
    print(f"  Engineering (jr/mid): {eng}  |  Senior/lead eng: {senior_eng}  |  Non-eng signals: {non_eng}")

    # ── Step 6: Generate report ──
    print("\n📝 Step 6: Generating report...")
    fetch_stats = {
        "total_fetched": len(all_leads),
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
        "errors": errors,
    }
    report = generate_report(all_leads, fetch_stats)
    filepath = _save_report(report, args.mode)

    # ── Step 7: Save state + raw leads CSV ──
    save_state(new_state, state_path)
    print(f"  State saved: {len(new_state)} roles tracked")
    _save_leads_csv(all_leads, args.mode)

    print("\n" + "=" * 60)
    print("  ✅ Done!")
    print(f"  Report: {filepath}")
    print("=" * 60)


def _state_path(mode: str) -> str:
    return "data/state.json" if mode == "crypto" else "data/state-all.json"


def _mode_suffix(mode: str) -> str:
    return "" if mode == "crypto" else "-all"


def _save_report(report: str, mode: str) -> str:
    """Save the markdown report to the output directory."""
    briefs_dir = os.path.join(OUTPUT_DIR, "briefs")
    os.makedirs(briefs_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(briefs_dir, f"daily-brief{_mode_suffix(mode)}-{date_str}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Saved: {filepath}")
    return filepath


def _save_leads_csv(leads: list[dict], mode: str) -> str:
    """Save all scored leads as a CSV for reference / future imports."""
    leads_dir = os.path.join(OUTPUT_DIR, "leads")
    os.makedirs(leads_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(leads_dir, f"leads{_mode_suffix(mode)}-{date_str}.csv")
    
    fieldnames = ["freshness", "role_type", "seniority", "web3_score", "title", "company",
                  "location", "source", "source_type", "date", "first_seen", "last_seen",
                  "times_seen", "url", "tracker_match", "tracker_note", "company_roles_count"]
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead)
    
    print(f"  Saved: {filepath}")
    return filepath


def _resolve_source_url(source: dict) -> str:
    t = source["type"]
    sid = source["id"]
    if t == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{sid}/jobs?content=true"
    if t == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{sid}"
    if t == "lever":
        return f"https://api.lever.co/v0/postings/{sid}?mode=json"
    if t == "getro":
        return f"https://{sid}.getro.com/api/v1/jobs"
    if t == "career_page":
        return sid
    if t == "web3career":
        return f"https://web3.career/{sid}-jobs"
    if t == "cryptojobslist":
        return f"https://cryptojobslist.com/{sid}"
    if t == "cryptocurrencyjobs":
        return f"https://cryptocurrencyjobs.co/?q={sid}"
    return ""


def save_source_health(source_stats: list[dict], mode: str) -> str:
    scans_dir = os.path.join(OUTPUT_DIR, "scans")
    os.makedirs(scans_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(scans_dir, f"source-health{_mode_suffix(mode)}-{date_str}.md")

    active = sorted([s for s in source_stats if s["fetched"] > 0],
                    key=lambda s: s["fetched"], reverse=True)
    quiet  = sorted([s for s in source_stats if s["fetched"] == 0 and not s["error"]],
                    key=lambda s: s["name"].lower())
    failed = sorted([s for s in source_stats if s["error"]],
                    key=lambda s: s["name"].lower())

    total_fetched = sum(s["fetched"] for s in source_stats)
    lines = [
        f"# Source Health — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**Mode:** {mode}  |  **Sources:** {len(source_stats)}  |  **Total fetched:** {total_fetched}",
        "",
        "---",
        "",
        "## Active sources (returned jobs)",
        "",
        "| Source | Type | URL | Fetched |",
        "|--------|------|-----|---------|",
    ]
    for s in active:
        lines.append(f"| {s['name']} | {s['type']} | {s['url']} | {s['fetched']} |")
    if not active:
        lines.append("*None.*")

    lines += [
        "",
        "## Quiet sources (0 jobs — dormant or broken scraper)",
        "",
        "| Source | Type | URL |",
        "|--------|------|-----|",
    ]
    for s in quiet:
        lines.append(f"| {s['name']} | {s['type']} | {s['url']} |")
    if not quiet:
        lines.append("*None.*")

    lines += [
        "",
        "## Failed sources (fetch errors)",
        "",
    ]
    if failed:
        lines += [
            "| Source | Type | URL | Error |",
            "|--------|------|-----|-------|",
        ]
        for s in failed:
            err = s["error"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {s['name']} | {s['type']} | {s['url']} | {err} |")
    else:
        lines.append("*None.*")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Source health: {filepath}")
    return filepath


if __name__ == "__main__":
    main()
