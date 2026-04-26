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
