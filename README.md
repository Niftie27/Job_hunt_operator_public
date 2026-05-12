# Job Hunt Operator

Automated job discovery pipeline for blockchain/web3 engineering roles. Fetches from **95+ sources** (ATS APIs, career pages, aggregators), classifies by role type and seniority, tracks state across runs, and produces a daily markdown brief.

> This is the **public mirror** of a personal automation tool I run daily for my own job search. It's filtered to code only — the live tracker, contact data, and historical briefs live in a private companion repo.

## How it works

`python3 run.py` runs the full pipeline:

1. **Fetch** from Greenhouse / Ashby / Lever JSON APIs (structured data — fast and clean)
2. **Fetch** career pages via Playwright (for sites without an ATS API)
3. **Fetch** aggregators — web3.career, CryptoJobsList, cryptocurrencyjobs.co (the last one is a JS-rendered SPA — we hit its public Algolia search API directly)
4. **Fetch** detail-only career pages via Jina AI Reader (LLM-ready markdown, no API key needed)
5. **Dedupe** within the batch and against an outreach tracker
6. **Compare** against prior runs to label leads as 🆕 new vs 🔁 still_open
7. **Classify** each lead — role type (engineering/non), seniority (junior/mid/senior/lead), web3 relevance score
8. **Generate** a 3-section markdown brief + leads CSV + per-source health log

Two modes: `--mode crypto` (default, ~60 sources) or `--mode all` (95+ sources, includes general tech).

## Report sections

1. **Engineering / Dev Roles** — junior/mid engineering roles ranked by web3 relevance
2. **Senior / Lead Engineering Roles** — surfaced for outreach decisions (apply, network, or watch)
3. **Company Hiring Signals** — non-engineering roles at crypto companies (signals who's expanding)

Each lead is tagged with freshness, seniority, web3 score, source type, tracker match (with recruiter contact info if available), and company activity count.

## Files

```
├── config.py                    ← sources list + keyword scoring weights
├── fetchers.py                  ← Greenhouse / Ashby / Lever / Getro / web3career / cryptojobslist / cryptocurrencyjobs (Algolia)
├── playwright_fetcher.py        ← career page scraper (headless Chromium, title-only)
├── jina_fetcher.py              ← LLM-friendly markdown fetcher for detail-only career pages
├── crawl4ai_fetcher.py          ← LLM-extraction fetcher (pilot, currently inactive — see commit history)
├── pipeline.py                  ← classification, dedupe, tracker matching, report generation
├── run.py                       ← main runner with --mode flag and per-source health logging
├── state.py                     ← JSON persistence (first_seen/last_seen/times_seen)
└── tools/
    ├── run_daily.sh             ← cron wrapper
    ├── detect_ats.py            ← ATS-type detector for unknown career URLs
    ├── detect_ats_for_quiet.py  ← finds hidden ATS endpoints behind quiet career pages
    └── find_tracker_careers.py  ← discovers career pages for companies in tracker + watchlist
```

Generated outputs (`output/`) and private state (`data/`) are gitignored here.

## Adding sources

Edit `config.py` SOURCES list:

```python
{"type": "greenhouse",       "id": "SLUG",                        "name": "Company", "category": "crypto"}
{"type": "ashby",            "id": "SLUG",                        "name": "Company", "category": "crypto"}
{"type": "lever",            "id": "SLUG",                        "name": "Company", "category": "crypto"}
{"type": "career_page",      "id": "https://company.com/careers", "name": "Company", "category": "crypto"}
{"type": "career_page_jina", "id": "https://...",                 "name": "Company", "category": "crypto"}
```

`category` is `"crypto"` (default mode) or `"general"` (only fetched with `--mode all`).

## Requirements

- Python 3.10+
- Playwright + Chromium: `pip install playwright && playwright install chromium`
- System deps (WSL/Linux): `sudo playwright install-deps chromium`
- Optional: Jina Reader needs no key; `crawl4ai_fetcher.py` needs `GROQ_API_KEY` (but is currently unused — see v0.9.16/v0.9.17 history)

## Daily run via cron

```cron
30 7 * * * /home/<user>/code/Job_hunt_operator/tools/run_daily.sh
```

`run_daily.sh` wraps the pipeline with logging at `output/cron-logs/run-YYYY-MM-DD.log` (auto-deleted after 14 days).

## Design principle

> The script surfaces and sorts. The human decides the action.

No "RELEVANT/MAYBE/SKIP" auto-classification — just observable tags (role_type, seniority, web3_score, freshness) so the operator can scan a brief in 60 seconds and decide what to do.

## Engineering notes worth a click

A few decisions that show up in the commit log:

- **v0.9.6 → v0.9.10**: built a multi-source watchlist + tracker discovery flow that automatically probes 200+ companies for hidden ATS endpoints and surfaces ready-to-paste config entries
- **v0.9.16 → v0.9.18**: tried Crawl4AI + Groq for LLM-extracted job descriptions; rolled back (async wrapper bugs, free-tier rate limits made it unworkable). Replaced with Jina AI Reader — same goal, no LLM costs, no rate limit pain
- **v0.9.17**: cryptocurrencyjobs.co serves jobs only via Algolia client-side search; reverse-engineered the public Algolia credentials from their JS bundle to query the index directly (saves a 250 KB SPA render per category)
- **v0.9.11**: source category split (`crypto` vs `general`) with separate state files so switching modes doesn't flag every existing role as "new"

The honest tradeoff log is in the commit messages — including the things that didn't work.
