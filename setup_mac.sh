#!/bin/bash
# setup_mac.sh — one-step installer for the Aegis Manual Crypto Lab on macOS.
#
# This script downloads the read-only advisory script to a folder on your Desktop,
# verifies Python 3 is installed, then starts a `screen` session that auto-refreshes
# every 15 minutes.

set -e

LAB_DIR="$HOME/Desktop/AegisManualLab"
mkdir -p "$LAB_DIR"
cd "$LAB_DIR"

echo "[setup] downloading manual_lab.py ..."
curl -fsSL -o manual_lab.py \
  "https://raw.githubusercontent.com/shawnzyluxe-lab/aegis-manual-lab/main/manual_lab.py"

echo "[setup] downloading manual_journal.csv ..."
curl -fsSL -o manual_journal.csv \
  "https://raw.githubusercontent.com/shawnzyluxe-lab/aegis-manual-lab/main/manual_journal.csv"

echo "[setup] verifying Python 3 ..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  echo "Install Python 3 from: https://www.python.org/downloads/macos/"
  exit 1
fi

echo "[setup] starting live auto-refresh session ..."
screen -dmS manual_lab python3 -u "$LAB_DIR/manual_lab.py"

echo "[setup] attaching to the live terminal ..."
echo "Press Ctrl+A then D to detach (it keeps running in the background)."
exec screen -r manual_lab
