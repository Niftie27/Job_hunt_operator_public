"""
JH Operator — State Persistence (v0.7)
=======================================
A tiny JSON-based memory layer. This is what turns the pipeline from
"show me everything again" into "show me what's new."

HOW IT WORKS:
- After each run, we save every lead's role_key + first_seen + last_seen + times_seen
- On the next run, we load that state and compare:
    - New lead (never seen before) → marked as "new"
    - Known lead (seen before) → marked as "still_open", first_seen preserved
    - Gone lead (was in state but not in this run) → stays in state as "gone"

ROLE KEY:
- ATS sources: use the job_id from the API (stable, unique)
- Aggregators: use company + normalized title + normalized location (best effort)

STATE FILE: data/state.json
- Just a JSON dict mapping role_key → {first_seen, last_seen, times_seen}
- Small enough to read/write in one shot
- Human-readable if you want to inspect it
"""

import json
import os
import re
from datetime import datetime


STATE_PATH = "data/state.json"


def _normalize_for_key(text: str) -> str:
    """Lowercase, strip, collapse whitespace, remove punctuation."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text


def make_role_key(lead: dict) -> str:
    """
    Generate a stable key for a lead.
    
    ATS sources have a job_id from the API — use source + job_id.
    Aggregator sources don't — use company + title + location.
    
    Examples:
        "greenhouse/consensys:7297078"
        "ashby/nethermind:bedb6b20-6056-4b78-a313-099d1aeaca62"
        "web3career/solidity:unknown_senior_smart_contract_engineer_unknown"
    """
    source = lead.get("source", "unknown")
    job_id = lead.get("job_id", "")

    if job_id:
        return f"{source}:{job_id}"
    else:
        company = _normalize_for_key(lead.get("company", "unknown"))
        title = _normalize_for_key(lead.get("title", "unknown"))
        location = _normalize_for_key(lead.get("location", "unknown"))
        return f"{source}:{company}_{title}_{location}"


def load_state(path: str = None) -> dict:
    """
    Load previous state from JSON file.
    Returns dict: {role_key: {first_seen, last_seen, times_seen}}
    Returns empty dict if file doesn't exist (first run).
    """
    path = path or STATE_PATH
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  ⚠ Failed to load state from {path}: {e}")
        return {}


def save_state(state: dict, path: str = None):
    """Save state to JSON file."""
    path = path or STATE_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def update_state(leads: list[dict], old_state: dict) -> tuple[dict, list[dict]]:
    """
    Compare current leads against previous state.
    
    For each lead:
    - If role_key not in old_state → it's NEW. Set first_seen = today.
    - If role_key in old_state → it's STILL OPEN. Keep first_seen, update last_seen.
    
    Returns:
        new_state: updated state dict (to be saved)
        leads: same leads list but with added fields:
            - role_key
            - first_seen (real, from state)
            - last_seen
            - times_seen
            - freshness: "new" or "still_open"
    """
    today = datetime.now().strftime("%Y-%m-%d")
    new_state = dict(old_state)  # copy — we'll update in place

    for lead in leads:
        key = make_role_key(lead)
        lead["role_key"] = key

        if key in old_state:
            # STILL OPEN — seen before
            entry = old_state[key]
            lead["first_seen"] = entry["first_seen"]
            lead["last_seen"] = today
            lead["times_seen"] = entry["times_seen"] + 1
            lead["freshness"] = "still_open"
        else:
            # NEW — never seen before
            lead["first_seen"] = today
            lead["last_seen"] = today
            lead["times_seen"] = 1
            lead["freshness"] = "new"

        # Update state
        new_state[key] = {
            "first_seen": lead["first_seen"],
            "last_seen": today,
            "times_seen": lead["times_seen"],
        }

    return new_state, leads
