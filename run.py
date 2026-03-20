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
    print("=" * 60)
    print("  JH Operator — Daily Intake Run")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print()
    
    # ── Step 1: Fetch from all sources ──
    print("📡 Step 1: Fetching from sources...")
    all_leads = []
    sources_ok = 0
    sources_failed = 0
    errors = []
    
    for source in SOURCES:
        try:
            jobs = fetch_source(source)
            if jobs:
                all_leads.extend(jobs)
                sources_ok += 1
                print(f"     ✓ {source['name']}: {len(jobs)} jobs")
            else:
                sources_ok += 1  # succeeded but no jobs (that's ok)
                print(f"     ✓ {source['name']}: 0 jobs")
        except Exception as e:
            sources_failed += 1
            err_msg = f"{source['name']}: {e}"
            errors.append(err_msg)
            print(f"     ✗ {err_msg}")
        
        # Be polite: don't hammer APIs too fast
        time.sleep(0.5)
    
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
        _save_report(report)
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
    old_state = load_state()
    print(f"  Previous state has {len(old_state)} known roles")
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
    filepath = _save_report(report)

    # ── Step 7: Save state + raw leads CSV ──
    save_state(new_state)
    print(f"  State saved: {len(new_state)} roles tracked")
    _save_leads_csv(all_leads)

    print("\n" + "=" * 60)
    print("  ✅ Done!")
    print(f"  Report: {filepath}")
    print("=" * 60)


def _save_report(report: str) -> str:
    """Save the markdown report to the output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(OUTPUT_DIR, f"daily-brief-{date_str}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Saved: {filepath}")
    return filepath


def _save_leads_csv(leads: list[dict]) -> str:
    """Save all scored leads as a CSV for reference / future imports."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(OUTPUT_DIR, f"leads-{date_str}.csv")
    
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


import csv  # needed for _save_leads_csv

if __name__ == "__main__":
    main()
