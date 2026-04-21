"""
JH Operator — Pipeline (v0.6)
==============================
What changed from v0.5:
- Scoring no longer tries to guess your action (no more RELEVANT/MAYBE/SKIP)
- Instead, each lead gets OBSERVABLE TAGS that the script can actually infer:
    - role_type:    "engineering" or "non_engineering"
    - seniority:    "junior" / "mid" / "senior" / "lead" / "unclear"
    - web3_score:   how blockchain/web3-relevant the role is (number)
    - web3_matched: list of matched keywords
    - source_type:  "ats" (official) or "aggregator" (job board)
    - tracker_match + tracker_note
    - first_seen date
    - company_roles_count (how many roles this company has in the batch)
- The report has 3 sections, sorted by what the script can infer
- YOU decide the action: direct apply, stretch apply, cold outreach, or skip

Design principle (agreed with GPT + Tomáš):
    The script surfaces and sorts. The human decides the action.
"""

import csv
import re
from datetime import datetime
from collections import Counter
from config import (
    PRIMARY_KEYWORDS, SECONDARY_KEYWORDS,
    TRACKER_PATH,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. DEDUPE — Compare new leads against your tracker history
# ═══════════════════════════════════════════════════════════════════════

def load_tracker(path: str = None) -> list[dict]:
    path = path or TRACKER_PATH
    try:
        with open(path, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"  ⚠ Tracker not found at {path}, running without history")
        return []


def _normalize_company(name: str) -> str:
    name = name.lower().strip()
    for remove in ["inc", "inc.", "ltd", "ltd.", "gmbh", "labs", "protocol",
                    "network", "foundation", "finance", "(", ")", ",", "."]:
        name = name.replace(remove, "")
    return re.sub(r"\s+", " ", name).strip()


def dedupe_against_tracker(leads: list[dict], tracker: list[dict]) -> list[dict]:
    """
    Check if the company already appears in the tracker.
    A match does NOT mean skip — it means you have history.
    """
    tracker_companies = {}
    for row in tracker:
        comp = _normalize_company(row.get("company", ""))
        if comp:
            tracker_companies[comp] = {
                "status": row.get("pipeline_status", "unknown"),
                "stage": row.get("stage_label", ""),
                "note": row.get("notes", "")[:100],
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
# 2. DEDUPLICATE WITHIN BATCH
# ═══════════════════════════════════════════════════════════════════════

def dedupe_within_batch(leads: list[dict]) -> list[dict]:
    seen = {}
    for lead in leads:
        comp = _normalize_company(lead.get("company", ""))
        title = lead.get("title", "").lower().strip()
        simple_title = re.sub(r"\s+", " ", title).strip()
        key = (comp, simple_title)

        if key in seen:
            existing = seen[key]
            if len(lead.get("snippet", "")) > len(existing.get("snippet", "")):
                seen[key] = lead
        else:
            seen[key] = lead

    return list(seen.values())


# ═══════════════════════════════════════════════════════════════════════
# 3. CLASSIFY — Infer what the script can actually know
# ═══════════════════════════════════════════════════════════════════════

# ── Seniority detection ──────────────────────────────────────────────

SENIORITY_PATTERNS = {
    "lead": [
        "lead ", " lead", "tech lead", "team lead", "engineering lead",
    ],
    "senior": [
        "senior", "sr ", "sr.", "staff", "principal",
    ],
    "junior": [
        "junior", "jr ", "jr.", "entry level", "entry-level",
        "intern", "internship", "graduate",
    ],
}


def _detect_seniority(title: str) -> str:
    """Detect seniority from the job title. Returns junior/mid/senior/lead/unclear."""
    t = title.lower()
    for pattern in SENIORITY_PATTERNS["lead"]:
        if pattern in t:
            return "lead"
    for pattern in SENIORITY_PATTERNS["senior"]:
        if pattern in t:
            return "senior"
    for pattern in SENIORITY_PATTERNS["junior"]:
        if pattern in t:
            return "junior"
    eng_words = ["engineer", "developer", "architect", "programmer", "auditor"]
    if any(w in t for w in eng_words):
        return "mid"
    return "unclear"


# ── Role type detection ──────────────────────────────────────────────

NON_ENGINEERING_PATTERNS = [
    "product manager", "project manager", "program manager",
    "marketing", "marketer", "brand ",
    "designer", "design director", "design lead",
    "ux researcher", "ux writer", "ui/ux",
    "data scientist", "data analyst", "analytics engineer",
    "business development", "business operations",
    "operations manager", "product operations", "operations analyst",
    "customer operations", "payment operations",
    "compliance", "legal", "counsel", "lawyer",
    "recruiter", "talent", "people ",
    "finance ", "accounting", "controller",
    "risk ", "risk analyst", "fiu analyst", "fraud ",
    "support specialist", "customer success", "customer support",
    "community manager", "community lead",
    "content ", "copywriter", "communications",
    "sales ", "account executive", "account manager",
    "office manager", "executive assistant",
    "quantitative researcher",
    "hr ", "human resources", "workday", "payroll",
    "general application", "general interest",
    "business analyst", "financial analyst", "operations analyst",
    "investment analyst", "research analyst",
]

ENGINEERING_BOOST_PATTERNS = [
    "engineer", "developer", "architect", "programmer",
    "solidity", "smart contract", "blockchain", "protocol",
    "backend", "frontend", "full-stack", "fullstack", "full stack",
    "devops", "sre", "infrastructure", "platform",
    "security engineer", "auditor",
    "rust ", "golang", "python ",
]


def _detect_role_type(title: str) -> str:
    """
    Classify as 'engineering', 'non_engineering', or 'unclear' based on title.
    Engineering signals override non-engineering patterns.
    If neither matches, return 'unclear' — do NOT default to engineering.
    """
    t = title.lower()
    for pattern in ENGINEERING_BOOST_PATTERNS:
        if pattern in t:
            return "engineering"
    for pattern in NON_ENGINEERING_PATTERNS:
        if pattern in t:
            return "non_engineering"
    return "unclear"


# ── Web3 relevance scoring ───────────────────────────────────────────

SNIPPET_WEIGHT = 0.3


def _score_web3_relevance(title: str, snippet: str) -> tuple[int, list[str]]:
    """
    Score how web3/blockchain-relevant this role is.
    Title keywords get full weight. Snippet keywords get 30%.
    Does NOT penalize seniority — senior roles are valuable as outreach triggers.
    """
    title_lower = title.lower()
    snippet_lower = snippet.lower()

    score = 0
    matched = []

    for kw, points in PRIMARY_KEYWORDS.items():
        kw_lower = kw.lower()
        if kw_lower in title_lower:
            score += points
            matched.append(f"+{points} {kw} [title]")
        elif kw_lower in snippet_lower:
            reduced = round(points * SNIPPET_WEIGHT)
            if reduced > 0:
                score += reduced
                matched.append(f"+{reduced} {kw} [snippet]")

    for kw, points in SECONDARY_KEYWORDS.items():
        kw_lower = kw.lower()
        if kw_lower in title_lower:
            score += points
            matched.append(f"+{points} {kw} [title]")
        elif kw_lower in snippet_lower:
            reduced = round(points * SNIPPET_WEIGHT)
            if reduced > 0:
                score += reduced
                matched.append(f"+{reduced} {kw} [snippet]")

    return score, matched


# ── Source type detection ────────────────────────────────────────────

def _detect_source_type(source: str) -> str:
    if any(ats in source for ats in ["greenhouse", "ashby", "lever"]):
        return "ats"
    return "aggregator"


# ── Main classification function ─────────────────────────────────────

def classify_lead(lead: dict) -> dict:
    """
    Add all observable tags to a lead. Does NOT decide action.
    """
    title = lead.get("title", "")
    snippet = lead.get("snippet", "")

    lead["role_type"] = _detect_role_type(title)
    lead["seniority"] = _detect_seniority(title)
    lead["web3_score"], lead["web3_matched"] = _score_web3_relevance(title, snippet)
    lead["source_type"] = _detect_source_type(lead.get("source", ""))
    # first_seen / last_seen / times_seen / freshness are set by state.py,
    # not here. If state hasn't run yet, these won't exist on the lead.

    return lead


def classify_all(leads: list[dict]) -> list[dict]:
    """Classify every lead and add company activity counts."""
    classified = [classify_lead(lead) for lead in leads]

    company_counts = Counter(_normalize_company(l.get("company", "")) for l in classified)
    for lead in classified:
        norm = _normalize_company(lead.get("company", ""))
        lead["company_roles_count"] = company_counts.get(norm, 1)

    return classified


# ═══════════════════════════════════════════════════════════════════════
# 4. REPORT — 3 sections, tags on everything, human decides action
# ═══════════════════════════════════════════════════════════════════════

def _format_tags(lead: dict) -> str:
    tags = []

    # Freshness — most important signal, always first
    freshness = lead.get("freshness", "?")
    if freshness == "new":
        tags.append("🆕 status:new")
    elif freshness == "still_open":
        times = lead.get("times_seen", 0)
        tags.append(f"status:still_open · seen {times}x since {lead.get('first_seen', '?')}")
    else:
        tags.append("status:unknown")

    tags.append(lead.get("seniority", "?"))
    tags.append(f"scoring:{lead.get('web3_score', 0)}")
    tags.append(lead.get("source_type", "?"))

    if lead.get("_unclear_flag"):
        tags.append("❓ ROLE TYPE UNCLEAR")
    if lead.get("tracker_match"):
        tags.append("📇 IN TRACKER")
    if lead.get("company_roles_count", 1) > 1:
        tags.append(f"{lead['company_roles_count']} roles at company")

    return " · ".join(tags)


def _format_lead_full(lead: dict) -> list[str]:
    lines = []
    title = lead.get("title", "Unknown")
    company = lead.get("company", "Unknown")
    new_badge = "🆕 " if lead.get("freshness") == "new" else ""
    lines.append(f"### {new_badge}{title} — {company}")

    # Line 1: status | seniority | score | source
    freshness = lead.get("freshness", "?")
    if freshness == "new":
        status_str = "🆕 new"
    elif freshness == "still_open":
        times = lead.get("times_seen", 0)
        status_str = f"seen {times}x since {lead.get('first_seen', '?')}"
    else:
        status_str = "unknown"
    seniority = lead.get("seniority", "?")
    score = lead.get("web3_score", 0)
    source_type = lead.get("source_type", "?")
    lines.append(f"`{status_str} | {seniority} | score:{score} | {source_type}`")

    # Line 2: location
    lines.append(f"**Location:** {lead.get('location', 'Unknown')}")

    # Line 3: notes (tracker + unclear flag)
    notes = []
    if lead.get("tracker_match"):
        note = lead.get("tracker_note", "")
        notes.append(f"📇 in tracker{': ' + note if note else ''}")
    if lead.get("_unclear_flag"):
        notes.append("❓ role unclear")
    if notes:
        lines.append("  " + " · ".join(notes))

    # Line 4: relevance keywords
    kw_summary = ", ".join(lead.get("web3_matched", [])[:6])
    if kw_summary:
        lines.append(f"**Signals:** {kw_summary}")

    # Line 5: URL
    if lead.get("url"):
        lines.append(f"**Link:** {lead['url']}")

    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def _format_lead_compact(lead: dict) -> list[str]:
    lines = []
    title = lead.get("title", "Unknown")
    location = lead.get("location", "?")
    url = lead.get("url", "")
    new_badge = "🆕 " if lead.get("freshness") == "new" else ""
    lines.append(f"  - {new_badge}{title} ({location})")
    if url:
        lines.append(f"    {url}")
    return lines


def generate_report(leads: list[dict], fetch_stats: dict) -> str:
    """
    3-section report. Script surfaces and sorts. Human decides action.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    MIN_WEB3_SCORE = 3
    # Unclear role types need stronger web3 signal to earn a spot
    MIN_WEB3_SCORE_UNCLEAR = 6

    eng_roles = [l for l in leads
                 if l["role_type"] == "engineering"
                 and l["seniority"] in ("junior", "mid", "unclear")
                 and l["web3_score"] >= MIN_WEB3_SCORE]

    # Unclear role types with strong web3 signal get included but flagged
    unclear_with_signal = [l for l in leads
                           if l["role_type"] == "unclear"
                           and l["web3_score"] >= MIN_WEB3_SCORE_UNCLEAR]
    for l in unclear_with_signal:
        l["_unclear_flag"] = True
    eng_roles.extend(unclear_with_signal)

    senior_eng_roles = [l for l in leads
                        if l["role_type"] == "engineering"
                        and l["seniority"] in ("senior", "lead")
                        and l["web3_score"] >= MIN_WEB3_SCORE]

    company_signals = [l for l in leads
                       if l["role_type"] == "non_engineering"
                       and l["web3_score"] >= MIN_WEB3_SCORE]

    # Sort: NEW leads first, then still_open, then by web3_score within each group
    def _sort_key(lead):
        fresh = 0 if lead.get("freshness") == "new" else 1
        return (fresh, -lead.get("web3_score", 0))

    eng_roles.sort(key=_sort_key)
    senior_eng_roles.sort(key=_sort_key)

    # Count new vs still_open across all sections
    all_shown = eng_roles + senior_eng_roles + company_signals
    new_count = sum(1 for l in all_shown if l.get("freshness") == "new")
    still_open_count = sum(1 for l in all_shown if l.get("freshness") == "still_open")

    lines = []
    lines.append(f"# JH Daily Brief — {now}")
    lines.append("")
    lines.append(f"**Total leads fetched:** {len(leads)}")
    lines.append(f"**🆕 New since last run:** {new_count}")
    lines.append(f"**Still open:** {still_open_count}")
    lines.append(f"**Engineering roles (junior/mid):** {len(eng_roles)}")
    lines.append(f"**Senior/lead engineering roles:** {len(senior_eng_roles)}")
    lines.append(f"**Company hiring signals:** {len(company_signals)}")
    lines.append(f"**Sources:** {fetch_stats.get('sources_ok', 0)} ok, "
                 f"{fetch_stats.get('sources_failed', 0)} failed")
    lines.append("")

    # ── Section 1 ──
    if eng_roles:
        lines.append("---")
        lines.append("## 1. Engineering / Dev Roles Worth Reviewing")
        lines.append("")
        for l in eng_roles:
            lines.extend(_format_lead_full(l))

    # ── Section 2 ──
    if senior_eng_roles:
        lines.append("---")
        lines.append("## 2. Senior / Lead Engineering Roles Worth Reviewing")
        lines.append("*These may be direct targets, outreach triggers, or company signals — your call.*")
        lines.append("")
        for l in senior_eng_roles:
            lines.extend(_format_lead_full(l))

    # ── Section 3 ──
    if company_signals:
        lines.append("---")
        lines.append("## 3. Company Hiring Signals")
        lines.append("*Non-engineering roles at web3/crypto companies. These companies are actively hiring.*")
        lines.append("")

        companies = {}
        for l in company_signals:
            comp = l.get("company", "Unknown")
            companies.setdefault(comp, []).append(l)

        for comp, roles in sorted(companies.items()):
            tracker_flag = ""
            if any(r.get("tracker_match") for r in roles):
                tracker_flag = " 📇"
            lines.append(f"**{comp}**{tracker_flag} ({len(roles)} non-eng roles)")
            for r in roles[:5]:
                title = r.get("title", "Unknown")
                loc = r.get("location", "?")
                new_badge = "🆕 " if r.get("freshness") == "new" else ""
                lines.append(f"• {new_badge}{title} ({loc})")
            if len(roles) > 5:
                lines.append(f"*(+ {len(roles) - 5} more)*")
            lines.append("")

    # ── Errors ──
    if fetch_stats.get("errors"):
        lines.append("---")
        lines.append("## ⚠ Source Errors")
        for err in fetch_stats["errors"]:
            lines.append(f"- {err}")
        lines.append("")

    return "\n".join(lines)
