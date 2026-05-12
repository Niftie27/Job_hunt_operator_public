# Workflow rules for this repo

## Two-repo setup — load-bearing

This is the **private** primary repo. There is also a **public mirror**:
`github.com/Niftie27/Job_hunt_operator_public` (portfolio for recruiters).

- `/data /docs /output` are **tracked here** (recruiter tracker, watchlist,
  daily briefs, leads CSVs, cron logs) and **excluded from the public mirror**
  (gitignored AND filtered out of every commit in its history).
- The public README and .gitignore are managed via `tools/public_mirror/`
  (source of truth lives in this repo).

## Daily flow — DO NOT FORGET

```bash
# Normal work — push to PRIVATE as usual
git add ...; git commit -m "..."; git push

# When public should catch up (after a meaningful commit / version bump):
bash tools/sync_public.sh
```

`tools/sync_public.sh` is idempotent. It pulls private's main into the public
clone, runs `git filter-repo --invert-paths --path data --path docs --path output`,
re-applies the public README + `.gitignore` from `tools/public_mirror/`, then
force-pushes to the public remote.

**Never `git push` directly to the public remote** — always go through the
sync script so data can't leak.

When changing the public-facing README, edit `tools/public_mirror/README.md`
in this repo (not the file in the sibling clone) and then sync.

## Cron

`tools/run_daily.sh` runs `python3 run.py` at 07:30 daily via WSL crontab
(`crontab -l`). Logs land in `output/cron-logs/run-YYYY-MM-DD.log`
(auto-deleted after 14 days).

## Quick reference

| Need | Command |
|--|--|
| Verify cron is installed | `crontab -l` |
| Run pipeline manually | `python3 run.py` (default `--mode crypto`) |
| Run with general-tech sources too | `python3 run.py --mode all` |
| Sync public mirror | `bash tools/sync_public.sh` |
| See which sources are quiet | `output/scans/source-health-YYYY-MM-DD.md` |

## Open Questions & Cleanup TODO (post-v0.9.21)

### Files to investigate / potentially remove
- `docs/archive/JH_Jobs_links.md` — old version, superseded by Google Sheet
- `docs/source-library.md` — predates current architecture, audit content
- `output/scans/jh_jobs_sources_seed.csv` — one-shot migration artifact, no longer needed
- `data/watchlist-archived.txt` — superseded by Sheet's `excluded` Type, but still on disk

### Suspicious empty files
- `output/scans/needs-classification.md` — empty because auto-classify works; verify by adding intentionally bad URL
- `output/scans/pending-integrations.md` — empty BUT Sheet has rows with `pending_apify` Type (LinkedIn URLs). Why aren't they in the log? Check sync routing logic.

### State file question
- `data/state.json` — crypto mode state (current)
- `data/state-all.json` — all-mode state
- If user only uses --mode crypto, state-all.json is dormant. Could clean up if not used long-term.

### Watchlist count — resolved
Verified via `git show 2961a29~1:data/watchlist.txt | wc -l` = 162.
No data loss. Earlier "1541 entries" was likely confusion with planned
deep-research expansion (declined — quality over quantity) or with 
cryptocurrencyjobs.co aggregator coverage (~1500 companies via 5 category 
slugs in config.py). Current 162 is the actual sustained count.

### Source health terminology
- `output/scans/source-health-YYYY-MM-DD.md` — per-source fetch report
- Three sections: active (jobs returned), quiet (0 jobs, no error), failed (error)
- Not "health" in monitoring sense — more like "yield per source per run"
- Consider renaming to `source-yield-...` for clarity (future refactor)

### Architecture simplification candidates
- Can `JH_Jobs_Sources` Sheet replace `watchlist.txt` entirely? (name_only rows already serve that purpose)
- Can `find_tracker_careers.py` operate directly on Sheet rows with empty URL instead of reading watchlist.txt?
- If yes: delete watchlist.txt + watchlist-archived.txt, simplify dispatcher.

### PostgreSQL migration roadmap (Phase 2)
- Move state.json + tracker.csv → Postgres tables
- Schema: companies, jobs, outreach, sources, scans
- Host: Supabase (free tier, managed)
- Trigger: when JSON state hits multi-MB or query needs arise
- Estimated effort: 2-3 weeks incremental work alongside running pipeline
