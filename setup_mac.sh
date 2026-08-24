#!/bin/bash
# setup_mac.sh — one-step installer for the Aegis Manual Crypto Lab on macOS.
#
# This script clones/pulls the read-only advisory script to a folder on your
# Desktop, verifies Python 3 is installed, then starts a `screen` session that
# auto-refreshes every 15 minutes.

set -e

REPO_URL="https://github.com/shawnzyluxe-lab/aegis-manual-lab.git"
LAB_DIR="$HOME/Desktop/AegisManualLab"

# Preserve any existing journal before wiping/re-cloning the directory.
JOURNAL_BACKUP="/tmp/manual_journal_backup_$$.csv"
if [ -f "$LAB_DIR/manual_journal.csv" ]; then
  cp "$LAB_DIR/manual_journal.csv" "$JOURNAL_BACKUP"
fi

echo "[setup] checking for git ..."
if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found. Install it with: xcode-select --install"
  exit 1
fi

echo "[setup] pulling latest aegis-manual-lab into $LAB_DIR ..."
if [ -d "$LAB_DIR/.git" ]; then
  cd "$LAB_DIR"
  git fetch --depth 1 origin main
  git reset --hard origin/main
else
  rm -rf "$LAB_DIR"
  git clone --depth 1 "$REPO_URL" "$LAB_DIR"
fi

# Restore the operator's journal so it isn't overwritten by the repo template.
if [ -f "$JOURNAL_BACKUP" ]; then
  cp "$JOURNAL_BACKUP" "$LAB_DIR/manual_journal.csv"
  rm -f "$JOURNAL_BACKUP"
fi

cd "$LAB_DIR"

echo "[setup] stopping any existing manual_lab screen sessions and processes ..."
screen -ls 2>/dev/null | grep -E '\.manual_lab\s+' | awk '{print $1}' | while read -r session; do
  screen -X -S "$session" quit >/dev/null 2>&1 || true
done
screen -wipe >/dev/null 2>&1 || true
pkill -f "AegisManualLab/manual_lab.py" >/dev/null 2>&1 || true

echo "[setup] verifying Python 3 ..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  echo "Install Python 3 from: https://www.python.org/downloads/macos/"
  exit 1
fi

echo "[setup] starting live auto-refresh session ..."
sleep 1
screen -dmS manual_lab python3 -u "$LAB_DIR/manual_lab.py"

echo "[setup] attaching to the live terminal ..."
echo "Press Ctrl+A then D to detach (it keeps running in the background)."
exec screen -r manual_lab
