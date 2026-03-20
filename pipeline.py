"""
JH Operator — Pipeline
=======================
Three jobs:
1. DEDUPE:  Check each new lead against the tracker (already contacted?)
2. SCORE:   Rate each lead by keyword relevance
3. REPORT:  Format everything into a readable daily report

This file has no side effects — it takes data in, returns data out.
The main script (run.py) is what actually calls these and saves files.
"""

import csv
import re
from datetime import datetime
from config import (
    PRIMARY_KEYWORDS, SECONDARY_KEYWORDS, NEGATIVE_KEYWORDS,
    SCORE_RELEVANT, SCORE_MAYBE, TRACKER_PATH,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. DEDUPE — Compare new leads against your tracker history
# ═══════════════════════════════════════════════════════════════════════

def load_tracker(path: str = None) -> list[dict]:
    """
    Load the outreach tracker CSV into a list of dicts.
    Each row becomes a dict with the CSV column names as keys.
    """
    path = path or TRACKER_PATH
    try:
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        print(f"  ⚠ Tracker not found at {path}, running without history")
        return []


def _normalize_company(name: str) -> str:
    """
    Normalize a company name for fuzzy matching.
    "Ava Labs" and "avalabs" and "Ava Labs (Avalanche)" should all match.
    """
    name = name.lower().strip()
    # Remove common suffixes and noise
    for remove in ["inc", "inc.", "ltd", "ltd.", "gmbh", "labs", "protocol", 
                    "network", "foundation", "finance", "(", ")", ",", "."]:
        name = name.replace(remove, "")
    # Remove extra whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Also create a no-space version for matching "moonpay" vs "moon pay"
    return name


def dedupe_against_tracker(leads: list[dict], tracker: list[dict]) -> list[dict]:
    """
    For each lead, check if the company already appears in the tracker.
    Adds two fields to each lead:
        - "tracker_match": True/False
        - "tracker_note":  what happened before (e.g. "sent / tracked — cold outreach")
    
    IMPORTANT: A tracker match does NOT mean "skip".
    It means "you already have history with this company."
    The decision to skip or re-engage is yours.
    """
    # Build a set of normalized tracker company names + their status
    tracker_companies = {}
    for row in tracker:
        comp = _normalize_company(row.get("company", ""))
        if comp:
            status = row.get("pipeline_status", "unknown")
            stage = row.get("stage_label", "")
            note = row.get("notes", "")
            tracker_companies[comp] = {
                "status": status,
                "stage": stage,
                "note": note[:100],  # truncate long notes
            }
    
    for lead in leads:
        norm = _normalize_company(lead.get("company", ""))
        if norm in tracker_companies:
            match = tracker_companies[norm]
            lead["tracker_match"] = True
            lead["tracker_note"] = f"{match['status']} — {match['stage']}"
        else:
            lead["tracker_match"] = False
            lead["tracker_note"] = ""
    
    return leads


# ═══════════════════════════════════════════════════════════════════════
# 2. SCORE — Rate relevance based on keywords in title + snippet
# ═══════════════════════════════════════════════════════════════════════

def score_lead(lead: dict) -> dict:
    """
    Score a single lead based on keyword matching.
    
    How it works:
    - Combine the job title and snippet into one text blob
    - Check every keyword from config against that text
    - Add up the points (positive for good matches, negative for bad signals)
    - Classify as RELEVANT / MAYBE / SKIP based on thresholds
    
    Adds to the lead:
        - "score":       numeric relevance score
        - "relevance":   "RELEVANT" / "MAYBE" / "SKIP"
        - "matched":     list of keywords that matched (for debugging)
    """
    text = f"{lead.get('title', '')} {lead.get('snippet', '')}".lower()
    
    score = 0
    matched = []
    
    # Check primary keywords (highest value)
    for kw, points in PRIMARY_KEYWORDS.items():
        if kw.lower() in text:
            score += points
            matched.append(f"+{points} {kw}")
    
    # Check secondary keywords (supporting evidence)
    for kw, points in SECONDARY_KEYWORDS.items():
        if kw.lower() in text:
            score += points
            matched.append(f"+{points} {kw}")
    
    # Check negative keywords (red flags)
    for kw, points in NEGATIVE_KEYWORDS.items():
        if kw.lower() in text:
            score += points  # points are already negative
            matched.append(f"{points} {kw}")
    
    # Classify
    if score >= SCORE_RELEVANT:
        relevance = "RELEVANT"
    elif score >= SCORE_MAYBE:
        relevance = "MAYBE"
    else:
        relevance = "SKIP"
    
    lead["score"] = score
    lead["relevance"] = relevance
    lead["matched"] = matched
    
    return lead


def score_all(leads: list[dict]) -> list[dict]:
    """Score every lead and sort by score descending."""
    scored = [score_lead(lead) for lead in leads]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


# ═══════════════════════════════════════════════════════════════════════
# 3. DEDUPLICATE WITHIN BATCH — Same job from multiple sources
# ═══════════════════════════════════════════════════════════════════════

def dedupe_within_batch(leads: list[dict]) -> list[dict]:
    """
    Remove duplicates within the current fetch batch.
    Two leads are "the same" if they have the same company + very similar title.
    We keep the one with the longer snippet (more info).
    """
    seen = {}  # key: (normalized_company, normalized_title) → lead
    
    for lead in leads:
        comp = _normalize_company(lead.get("company", ""))
        title = lead.get("title", "").lower().strip()
        # Simplify title for matching: "Senior Smart Contract Engineer" ≈ "Smart Contract Engineer"
        simple_title = re.sub(r"\b(senior|junior|lead|staff|principal|sr|jr)\b", "", title).strip()
        simple_title = re.sub(r"\s+", " ", simple_title)
        
        key = (comp, simple_title)
        
        if key in seen:
            # Keep the one with more info
            existing = seen[key]
            if len(lead.get("snippet", "")) > len(existing.get("snippet", "")):
                seen[key] = lead
        else:
            seen[key] = lead
    
    return list(seen.values())


# ═══════════════════════════════════════════════════════════════════════
# 4. REPORT — Format the results into a readable daily brief
# ═══════════════════════════════════════════════════════════════════════

def generate_report(leads: list[dict], fetch_stats: dict) -> str:
    """
    Generate a markdown report from scored + deduped leads.
    
    fetch_stats: {"total_fetched": N, "sources_ok": N, "sources_failed": N, "errors": [...]}
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    relevant = [l for l in leads if l["relevance"] == "RELEVANT"]
    maybe    = [l for l in leads if l["relevance"] == "MAYBE"]
    skipped  = [l for l in leads if l["relevance"] == "SKIP"]
    
    new_relevant     = [l for l in relevant if not l.get("tracker_match")]
    known_relevant   = [l for l in relevant if l.get("tracker_match")]
    new_maybe        = [l for l in maybe if not l.get("tracker_match")]
    
    lines = []
    lines.append(f"# JH Daily Brief — {now}")
    lines.append("")
    lines.append(f"**Total leads found:** {len(leads)}")
    lines.append(f"**Relevant:** {len(relevant)} ({len(new_relevant)} new, {len(known_relevant)} known)")
    lines.append(f"**Maybe:** {len(maybe)} ({len(new_maybe)} new)")
    lines.append(f"**Skipped:** {len(skipped)}")
    lines.append(f"**Sources checked:** {fetch_stats.get('sources_ok', 0)} ok, {fetch_stats.get('sources_failed', 0)} failed")
    lines.append("")
    
    # ── NEW RELEVANT (the most important section) ──
    if new_relevant:
        lines.append("---")
        lines.append("## 🟢 New Relevant Leads")
        lines.append("")
        for l in new_relevant:
            lines.append(f"### {l['title']} — {l['company']}")
            lines.append(f"- **Score:** {l['score']}  |  **Location:** {l['location']}")
            lines.append(f"- **Source:** {l['source']}")
            lines.append(f"- **Why relevant:** {', '.join(l.get('matched', []))}")
            if l.get("url"):
                lines.append(f"- **Link:** {l['url']}")
            if l.get("snippet"):
                lines.append(f"- **Snippet:** {l['snippet'][:200]}...")
            lines.append("")
    
    # ── KNOWN COMPANIES WITH NEW ROLES ──
    if known_relevant:
        lines.append("---")
        lines.append("## 🟡 Relevant — Already in Tracker")
        lines.append("*(You've contacted these companies before. New role might be worth re-engaging.)*")
        lines.append("")
        for l in known_relevant:
            lines.append(f"### {l['title']} — {l['company']}")
            lines.append(f"- **Score:** {l['score']}  |  **Location:** {l['location']}")
            lines.append(f"- **Prior status:** {l['tracker_note']}")
            if l.get("url"):
                lines.append(f"- **Link:** {l['url']}")
            lines.append("")
    
    # ── MAYBE ──
    if new_maybe:
        lines.append("---")
        lines.append("## 🔵 Maybe — Worth a Look")
        lines.append("")
        for l in new_maybe[:15]:  # cap at 15 to keep report readable
            lines.append(f"- **{l['title']}** at {l['company']} (score: {l['score']}) — {l.get('location', '?')}")
            if l.get("url"):
                lines.append(f"  {l['url']}")
        if len(new_maybe) > 15:
            lines.append(f"  *(+ {len(new_maybe) - 15} more)*")
        lines.append("")
    
    # ── FETCH ERRORS ──
    if fetch_stats.get("errors"):
        lines.append("---")
        lines.append("## ⚠ Source Errors")
        for err in fetch_stats["errors"]:
            lines.append(f"- {err}")
        lines.append("")
    
    return "\n".join(lines)
