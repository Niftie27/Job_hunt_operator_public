#!/bin/bash
# JH Operator — daily cron wrapper
# Add to crontab -e:
#   0 7 * * * /home/tomas/code/Job_hunt_operator/tools/run_daily.sh
# Requires the machine to be powered on at the scheduled time.

REPO="$HOME/code/Job_hunt_operator"
LOG_DIR="$REPO/output/cron-logs"
DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/run-$DATE.log"

mkdir -p "$LOG_DIR"
cd "$REPO" || exit 1

# Auto-export any vars from .env (GROQ_API_KEY, etc.) so child python sees them.
set -a
[ -f .env ] && source .env
set +a

{
    echo "=== Run started: $(date) ==="
    python3 run.py
    echo "=== Run finished: $(date) ==="
} >> "$LOG_FILE" 2>&1

# Keep only the last 14 days of cron logs.
find "$LOG_DIR" -name "run-*.log" -mtime +14 -delete
