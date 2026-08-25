#!/bin/bash
# setup_mac.sh — one-step installer for the Aegis Manual Crypto Lab on macOS.
#
# This script clones/pulls the read-only advisory script to a folder on your
# Desktop, verifies Python 3 is installed, then starts the script in the
# background with nohup. It tails the log so the terminal auto-refreshes every
# 15 minutes without screen/tmux artifacts.

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

echo "[setup] stopping any existing manual_lab processes ..."
pkill -f "AegisManualLab/manual_lab.py" >/dev/null 2>&1 || true

echo "[setup] verifying Python 3 ..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  echo "Install Python 3 from: https://www.python.org/downloads/macos/"
  exit 1
fi

echo "[setup] starting background live auto-refresh ..."
# Rotate old log so we start with a clean tail.
if [ -f manual_lab.log ]; then
  mv manual_lab.log "manual_lab.log.$(date +%Y%m%d%H%M%S)"
fi
nohup python3 -u "$LAB_DIR/manual_lab.py" > "$LAB_DIR/manual_lab.log" 2>&1 &

echo "[setup] PID: $! — tailing log now ..."
echo "Press Ctrl+C to stop watching (the script keeps running in the background)."
echo "To stop the script later, run: pkill -f AegisManualLab/manual_lab.py"
sleep 2
tail -f "$LAB_DIR/manual_lab.log"
