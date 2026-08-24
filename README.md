# Aegis Manual Crypto Lab

A read-only, manual crypto advisory sandbox. It polls Coinbase public 15-minute
candlesticks for 10 major USD pairs, computes a 9-EMA, and prints a visible
terminal alert when a candle closes below the 9-EMA after closing above it.

It does **not** connect to exchange write endpoints, place orders, move capital,
or integrate with any production trading engine.

## macOS quick start

Open Terminal and run:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/shawnzyluxe-lab/aegis-manual-lab/main/setup_mac.sh)"
```

This will:
- create `~/Desktop/AegisManualLab`
- download `manual_lab.py` and `manual_journal.csv`
- start a `screen` session that auto-refreshes every 15 minutes
- attach your Terminal so you see the live output

Controls while inside the live session:
- **Detach and keep running:** `Ctrl+A` then `D`
- **Reattach later:** `screen -r manual_lab`
- **Stop the background process:** `screen -X -S manual_lab quit`

## Manual run

```bash
git clone https://github.com/shawnzyluxe-lab/aegis-manual-lab.git
cd aegis-manual-lab
python3 -u manual_lab.py
```
