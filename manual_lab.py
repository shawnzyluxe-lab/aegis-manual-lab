#!/usr/bin/env python3
"""manual_lab.py — read-only crypto advisory sandbox.

This script is strictly for educational, manual signal generation. It:
- Fetches the latest 15-minute candlesticks for 10 major USD crypto pairs from
  Coinbase's public REST API.
- Computes a rolling 9-period EMA on the closes.
- Flags a buying anomaly when the close of a completed 15-minute candle drops
  below the 9-EMA after having closed above it on the prior candle.
- Prints a dark-formatted terminal block with a manual Coinbase execution
  instruction and recommended stop-loss / take-profit levels.
- Logs every alert, its entry coordinates, and a simulated 15-minute forward
  outcome to `manual_journal.csv`.

It does NOT connect to exchange write endpoints, place orders, move capital, or
integrate with `run_daily.py`.
"""

import csv
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "aegis-manual-lab/0.1 (read-only observation sandbox)"
COINBASE_CANDLES = "https://api.exchange.coinbase.com/products/{product}/candles?granularity=900"

# 10 major -USD coin pairs.
UNIVERSE = [
    "BTC-USD",
    "ETH-USD",
    "XRP-USD",
    "LTC-USD",
    "BCH-USD",
    "LINK-USD",
    "ADA-USD",
    "XLM-USD",
    "DOGE-USD",
    "ETC-USD",
]

EMA_PERIOD = 9
RISK_STOP_PCT = 0.01   # 1% below entry
REWARD_TP_PCT = 0.02   # 2% above entry

JOURNAL_PATH = Path(__file__).with_name("manual_journal.csv")


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _timestamp_from_iso(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp())


@dataclass
class Alert:
    signal_time: int
    token: str
    entry: float
    ema: float
    stop: float
    take_profit: float
    forward_close: float | None
    outcome: str
    pct_pnl: float | None

    def as_dict(self) -> dict:
        return {
            "timestamp": _iso(self.signal_time),
            "token": self.token,
            "entry_price": f"{self.entry:.4f}",
            "ema_9": f"{self.ema:.4f}",
            "stop_loss": f"{self.stop:.4f}",
            "take_profit": f"{self.take_profit:.4f}",
            "forward_15m_close": f"{self.forward_close:.4f}" if self.forward_close is not None else "",
            "outcome": self.outcome,
            "pct_pnl": f"{self.pct_pnl:.4f}" if self.pct_pnl is not None else "",
        }


def _fetch_json(url: str, timeout: int = 15) -> dict | list:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_candles(product: str) -> list[dict]:
    """Fetch the most recent 15-minute candles for a Coinbase product.

    Coinbase returns `[time, low, high, open, close, volume]` arrays, newest
    first. We sort them chronologically and annotate each row.
    """
    url = COINBASE_CANDLES.format(product=product)
    try:
        rows = _fetch_json(url)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"Coinbase {product} candle fetch error: {exc}")
        return []

    candles = []
    for row in rows:
        ts, low, high, open_, close, volume = row
        candles.append(
            {
                "time": int(ts),
                "open": float(open_),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": float(volume),
            }
        )
    candles.sort(key=lambda c: c["time"])
    return candles


def compute_ema9(candles: list[dict]) -> list[float]:
    """Return a 9-period EMA series aligned with the candle list."""
    closes = [c["close"] for c in candles]
    ema: list[float] = [0.0] * len(closes)
    alpha = 2.0 / (EMA_PERIOD + 1)

    if len(closes) < EMA_PERIOD:
        return ema

    sma = sum(closes[:EMA_PERIOD]) / EMA_PERIOD
    for i in range(EMA_PERIOD):
        ema[i] = sma

    for i in range(EMA_PERIOD, len(closes)):
        ema[i] = closes[i] * alpha + ema[i - 1] * (1 - alpha)

    return ema


def _simulate_outcome(entry: float, forward_close: float) -> tuple[str, float]:
    stop = entry * (1 - RISK_STOP_PCT)
    tp = entry * (1 + REWARD_TP_PCT)
    pct_pnl = (forward_close - entry) / entry * 100.0

    if forward_close >= tp:
        return "TP", pct_pnl
    if forward_close <= stop:
        return "SL", pct_pnl
    return "HOLD", pct_pnl


def detect_latest_signal(candles: list[dict], ema: list[float], token: str) -> Alert | None:
    """Find the most recent 15m close that drops below the 9-EMA.

    The alert is generated only for the latest completed crossover. If the next
    forward candle is available, the outcome is simulated; otherwise it remains
    PENDING until the next run supplies the forward tick.
    """
    n = len(candles)
    for i in range(n - 1, EMA_PERIOD, -1):
        prev_close = candles[i - 1]["close"]
        prev_ema = ema[i - 1]
        curr_close = candles[i]["close"]
        curr_ema = ema[i]

        if prev_close >= prev_ema and curr_close < curr_ema:
            entry = curr_close
            stop = entry * (1 - RISK_STOP_PCT)
            tp = entry * (1 + REWARD_TP_PCT)

            if i + 1 < n:
                forward_close = candles[i + 1]["close"]
                outcome, pct_pnl = _simulate_outcome(entry, forward_close)
            else:
                forward_close = None
                outcome = "PENDING"
                pct_pnl = None

            return Alert(
                signal_time=candles[i]["time"],
                token=token,
                entry=entry,
                ema=curr_ema,
                stop=stop,
                take_profit=tp,
                forward_close=forward_close,
                outcome=outcome,
                pct_pnl=pct_pnl,
            )
    return None


def _load_journal() -> list[dict]:
    if not JOURNAL_PATH.exists():
        return []
    with JOURNAL_PATH.open("r", newline="") as handle:
        return list(csv.DictReader(handle))


def _save_journal(rows: list[dict]) -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "timestamp",
        "token",
        "entry_price",
        "ema_9",
        "stop_loss",
        "take_profit",
        "forward_15m_close",
        "outcome",
        "pct_pnl",
    ]
    with JOURNAL_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _update_pending(rows: list[dict], token: str, candles: list[dict]) -> None:
    """Fill in forward outcomes for previously logged PENDING alerts."""
    time_to_index = {c["time"]: i for i, c in enumerate(candles)}
    for row in rows:
        if row.get("outcome") != "PENDING" or row.get("token") != token:
            continue
        signal_ts = _timestamp_from_iso(row["timestamp"])
        idx = time_to_index.get(signal_ts)
        if idx is None or idx + 1 >= len(candles):
            continue
        entry = float(row["entry_price"])
        forward_close = candles[idx + 1]["close"]
        outcome, pct_pnl = _simulate_outcome(entry, forward_close)
        row["forward_15m_close"] = f"{forward_close:.4f}"
        row["outcome"] = outcome
        row["pct_pnl"] = f"{pct_pnl:.4f}"


def _is_already_logged(rows: list[dict], alert: Alert) -> bool:
    timestamp = _iso(alert.signal_time)
    return any(r.get("timestamp") == timestamp and r.get("token") == alert.token for r in rows)


def print_alert(alert: Alert) -> None:
    """Print a dark-formatted terminal block with the manual execution instruction."""
    token = alert.token
    entry = f"{alert.entry:.4f}"
    stop = f"{alert.stop:.4f}"
    tp = f"{alert.take_profit:.4f}"
    outcome = alert.outcome
    pn = f"{alert.pct_pnl:.4f}%" if alert.pct_pnl is not None else "PENDING"

    lines = [
        "",
        "  MANUAL CRYPTO ADVISORY — BUY ANOMALY DETECTED  ",
        f"  TOKEN    : {token}",
        f"  SIGNAL   : 15m close dropped below 9-EMA",
        f"  ACTION   : BUY $10.00 market order of {token}",
        f"  ENTRY    : {entry}",
        f"  STOP-LOSS: {stop} ({token} -1.0%)",
        f"  TAKE-PROF: {tp} ({token} +2.0%)",
        f"  FORWARD  : {outcome} ({pn})",
        "  This is a manual instruction only. No automated execution occurs.",
        "",
    ]
    width = max(len(line) for line in lines)
    box = "\n".join(line.center(width) for line in lines)

    # Dark background with bright green text for visibility.
    print(f"\033[40m\033[1;32m{'#' * width}\033[0m")
    for line in lines:
        print(f"\033[40m\033[1;32m{line:<{width}}\033[0m")
    print(f"\033[40m\033[1;32m{'#' * width}\033[0m\n")


def main() -> int:
    print("manual_lab.py — read-only manual crypto advisory sandbox")
    print("starting 15-minute background loop. press Ctrl+C to stop.\n")

    while True:
        # Clear the terminal so every wake-up refresh is clean and live.
        print("\033[2J\033[H", end="")

        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] heartbeat — fetching 15m candles from Coinbase public API...\n")

        journal_rows = _load_journal()
        new_alerts: list[Alert] = []

        for token in UNIVERSE:
            candles = fetch_candles(token)
            if not candles:
                continue

            ema = compute_ema9(candles)
            _update_pending(journal_rows, token, candles)

            alert = detect_latest_signal(candles, ema, token)
            if alert is not None and not _is_already_logged(journal_rows, alert):
                new_alerts.append(alert)
                journal_rows.append(alert.as_dict())

        for alert in new_alerts:
            print_alert(alert)

        _save_journal(journal_rows)

        print(f"[{now}] Total alerts in journal: {len(journal_rows)}")
        if not new_alerts:
            print(f"[{now}] No new 15m/9-EMA buy anomalies detected in this wake-up.")
        print(f"\n[{now}] sleeping 15 minutes before next scan...")

        time.sleep(900)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nmanual_lab.py stopped")
        raise SystemExit(0)
