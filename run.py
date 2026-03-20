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
    score_all,
    generate_report,
)


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
    
    # ── Step 4: Score ──
    print("\n⚡ Step 4: Scoring leads...")
    all_leads = score_all(all_leads)
    relevant = sum(1 for l in all_leads if l["relevance"] == "RELEVANT")
    maybe = sum(1 for l in all_leads if l["relevance"] == "MAYBE")
    skip = sum(1 for l in all_leads if l["relevance"] == "SKIP")
    print(f"  RELEVANT: {relevant}  |  MAYBE: {maybe}  |  SKIP: {skip}")
    
    # ── Step 5: Generate report ──
    print("\n📝 Step 5: Generating report...")
    fetch_stats = {
        "total_fetched": len(all_leads),
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
        "errors": errors,
    }
    report = generate_report(all_leads, fetch_stats)
    filepath = _save_report(report)
    
    # ── Step 6: Save raw leads as CSV (for later analysis) ──
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
    
    fieldnames = ["relevance", "score", "title", "company", "location", 
                  "source", "date", "url", "tracker_match", "tracker_note"]
    
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
