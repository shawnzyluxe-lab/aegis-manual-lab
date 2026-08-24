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

CACHE_BUST=$(date +%s)

echo "[setup] downloading latest manual_lab.py ..."
rm -f manual_lab.py
if ! curl -fsSL -o manual_lab.py \
    "https://raw.githubusercontent.com/shawnzyluxe-lab/aegis-manual-lab/main/manual_lab.py?nocache=${CACHE_BUST}"; then
  echo "ERROR: could not download manual_lab.py. Check network / GitHub raw cache."
  exit 1
fi

if [ ! -f manual_journal.csv ]; then
  echo "[setup] creating manual_journal.csv ..."
  curl -fsSL -o manual_journal.csv \
    "https://raw.githubusercontent.com/shawnzyluxe-lab/aegis-manual-lab/main/manual_journal.csv?nocache=${CACHE_BUST}"
fi

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
