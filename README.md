# Job Hunt Operator

Automated job discovery pipeline for blockchain/web3 engineering roles. Fetches from 42+ sources, classifies by role type and seniority, tracks state across runs, and produces daily reports.

## How it works

`python3 run.py` does everything:

1. Fetches jobs from Greenhouse, Ashby, Lever APIs (structured data)
2. Fetches jobs from career pages via Playwright (JS-rendered HTML)
3. Fetches jobs from web3.career and CryptoJobsList (aggregators)
4. Removes duplicate listings within the batch
5. Checks each lead against your outreach tracker (data/tracker.csv)
6. Compares against previous runs (data/state.json) — marks new vs still_open
7. Classifies: role type (engineering/non_engineering/unclear), seniority (junior/mid/senior/lead), web3 relevance score
8. Generates a 3-section daily report + leads CSV

## Report sections

1. **Engineering / Dev Roles** — junior/mid engineering roles with web3 relevance
2. **Senior / Lead Engineering Roles** — your call: direct apply, outreach trigger, or company signal
3. **Company Hiring Signals** — non-engineering roles at crypto companies (shows who's actively hiring)

New leads get 🆕 badge. Each lead tagged with: freshness status, seniority, web3 score, source type (ats/aggregator), tracker match, company activity count.

## Files

```
├── config.py              ← sources list + keyword scoring weights
├── fetchers.py            ← Greenhouse/Ashby/Lever/Getro/web3career/cryptojobslist
├── playwright_fetcher.py  ← career page scraper (headless Chromium)
├── pipeline.py            ← classification + report generation
├── run.py                 ← main runner (this is what you execute)
├── state.py               ← JSON persistence (first_seen/last_seen/times_seen)
├── data/
│   ├── tracker.csv        ← outreach history (manually updated)
│   └── state.json         ← pipeline memory (auto-generated, gitignored)
├── docs/                  ← reference files, source library, setup guide
├── tools/                 ← one-time scripts (ATS detection, etc.)
└── output/
    ├── briefs/            ← daily-brief-YYYY-MM-DD.md
    ├── leads/             ← leads-YYYY-MM-DD.csv
    └── scans/             ← one-time scan results
```

## Adding sources

Edit `config.py` SOURCES list:

- Greenhouse: `{"type": "greenhouse", "id": "SLUG", "name": "Company"}`
- Ashby: `{"type": "ashby", "id": "SLUG", "name": "Company"}`
- Lever: `{"type": "lever", "id": "SLUG", "name": "Company"}`
- Career page: `{"type": "career_page", "id": "https://company.com/careers", "name": "Company"}`

## Requirements

- Python 3.10+
- Playwright + Chromium: `pip install playwright && playwright install chromium`
- System deps (WSL/Linux): `sudo playwright install-deps chromium`

## Design principle

The script surfaces and sorts. The human decides the action.
