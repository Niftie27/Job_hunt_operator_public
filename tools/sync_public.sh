#!/bin/bash
# Sync the public mirror at github.com/Niftie27/Job_hunt_operator_public
# from this private repo, stripping /data /docs /output from history.
#
# Usage (from anywhere):
#   bash /home/tomas/code/Job_hunt_operator/tools/sync_public.sh
#
# Requires: git-filter-repo (already installed in this WSL env).

set -euo pipefail

PRIVATE_DIR="/home/tomas/code/Job_hunt_operator"
PUBLIC_DIR="/home/tomas/code/Job_hunt_operator_public"
OVERRIDES="$PRIVATE_DIR/tools/public_mirror"
PUBLIC_REMOTE="git@github.com:Niftie27/Job_hunt_operator_public.git"

if [ ! -d "$PUBLIC_DIR/.git" ]; then
    echo "Public clone missing at $PUBLIC_DIR — re-cloning from private."
    git clone "$PRIVATE_DIR" "$PUBLIC_DIR"
fi

cd "$PUBLIC_DIR"

# Pull latest private history into the public clone (no-op if already up to date)
git fetch "$PRIVATE_DIR" main
git reset --hard FETCH_HEAD

# Strip data/docs/output from every commit (rewrites SHAs)
git filter-repo --invert-paths --path data --path docs --path output --force

# Re-apply the public-only README and .gitignore
cp "$OVERRIDES/README.md"   ./README.md
cp "$OVERRIDES/.gitignore"  ./.gitignore
git add README.md .gitignore
git -c user.name='Niftie27' -c user.email='tom.pazout@gmail.com' \
    commit -m "Public mirror sync ($(date -u +%Y-%m-%d))"

# git-filter-repo strips the origin remote as a safety measure — re-add it
git remote remove origin 2>/dev/null || true
git remote add origin "$PUBLIC_REMOTE"

# Refresh the lease so --force-with-lease passes (we INTEND to overwrite history,
# but want to fail if someone else pushed to public between fetch and push).
git fetch origin main || true
git push --force-with-lease=main:refs/remotes/origin/main origin main

echo
echo "✅ Public mirror synced. Commits pushed:"
git log --oneline -5
