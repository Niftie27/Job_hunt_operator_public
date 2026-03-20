# JH Operator — v0.5 Intake Loop

## What this does
Fetches job listings from crypto company career pages, checks them against your outreach tracker, scores them by relevance, and gives you a daily report.

**No AI, no agents, no login needed.** Just Python scripts hitting public APIs.

## Files
```
jh-operator/
├── config.py       ← Edit this to add/remove sources and tune scoring
├── fetchers.py     ← Talks to Greenhouse, Ashby, Lever, web3.career, CryptoJobsList
├── pipeline.py     ← Deduplication, scoring, report generation
├── run.py          ← The one script you run: python3 run.py
├── data/
│   └── tracker.csv ← Your outreach tracker (copy from your actual tracker)
└── output/
    ├── daily-brief-YYYY-MM-DD.md   ← The readable report
    └── leads-YYYY-MM-DD.csv        ← All scored leads as CSV
```

## Setup on VPS

```bash
# 1. Create the project directory (or clone from git)
mkdir -p ~/jh-operator/data ~/jh-operator/output
cd ~/jh-operator

# 2. Copy the scripts (config.py, fetchers.py, pipeline.py, run.py)
#    If using git: git clone <your-repo> .

# 3. Copy your current tracker
cp /path/to/JH_Outreach_Tracker.csv data/tracker.csv

# 4. Test it
python3 run.py

# 5. (Optional) Set up a daily cron job
crontab -e
# Add this line to run every morning at 8:00 AM:
# 0 8 * * * cd ~/jh-operator && python3 run.py >> output/cron.log 2>&1
```

## Requirements
- Python 3.10+ (already on most VPS)
- No pip packages needed — uses only Python standard library
- Internet access to reach Greenhouse/Ashby/Lever APIs

## How to add more sources

Open `config.py` and add to the SOURCES list:

```python
# If the company uses Greenhouse (URL looks like job-boards.greenhouse.io/SLUG):
{"type": "greenhouse", "id": "SLUG", "name": "Company Name"},

# If the company uses Ashby (URL looks like jobs.ashbyhq.com/SLUG):
{"type": "ashby", "id": "SLUG", "name": "Company Name"},

# If the company uses Lever (URL looks like jobs.lever.co/SLUG):
{"type": "lever", "id": "SLUG", "name": "Company Name"},
```

### How to find which ATS a company uses
1. Go to their careers page
2. Click "Apply" on any job
3. Look at the URL:
   - `boards.greenhouse.io/...` → Greenhouse
   - `jobs.ashbyhq.com/...` → Ashby  
   - `jobs.lever.co/...` → Lever
   - Something else → needs a custom fetcher (for later)

## How scoring works

Every job title + description is checked against keyword lists in `config.py`.

- **Primary keywords** (solidity, smart contract, blockchain, web3, defi...) = high points
- **Secondary keywords** (react, node.js, typescript, backend...) = some points
- **Negative keywords** (marketing, sales, VP, director, 10+ years...) = minus points

Total score determines classification:
- Score ≥ 8 → **RELEVANT** (green in report)
- Score ≥ 4 → **MAYBE** (blue in report)
- Score < 4 → **SKIP** (not shown in detail)

You can tune all weights and thresholds in `config.py`.

## What the report looks like

```
# JH Daily Brief — 2026-03-20 13:01

**Total leads found:** 47
**Relevant:** 8 (5 new, 3 known)
**Maybe:** 12 (10 new)
**Skipped:** 27

---
## 🟢 New Relevant Leads

### Smart Contract Engineer — Nansen
- **Score:** 42  |  **Location:** Remote
- **Why relevant:** +10 solidity, +10 smart contract, +7 defi, +6 ethereum
- **Link:** https://...

---
## 🟡 Relevant — Already in Tracker
*(Companies you've contacted before with new roles)*

### Solidity Developer — Animoca Brands
- **Score:** 25  |  **Location:** Remote
- **Prior status:** sent / tracked — follow-up sent
```

## Next steps (what to build after this works)

1. **More sources**: Add Getro boards, more Greenhouse/Ashby slugs from your source list
2. **Persistent state**: Save leads to SQLite so you can track what you've already seen
3. **OpenClaw integration**: Set up as a cron-triggered skill in OpenClaw workspace
4. **Fit triage**: Use the job description to do deeper fit assessment  
5. **Draft prep**: Generate outreach drafts for RELEVANT leads
