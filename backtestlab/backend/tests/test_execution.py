"""Regression tests for latency-aware, no-look-ahead execution."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.execution import simulate_ideal, simulate_realistic


def _candles(prices: list[float]) -> pd.DataFrame:
    times = pd.date_range("2024-01-01", periods=len(prices), freq="1h", tz="UTC")
    return pd.DataFrame({
        "time": times,
        "open": prices,
        "high": prices,
        "low": prices,
        "close": prices,
        "volume": [1.0] * len(prices),
    })


def test_future_peeking_signal_cannot_fill_on_its_own_bar():
    """A target at bar i must only enter at bar i + 1."""
    candles = _candles([100.0, 100.0, 10_000.0, 10_000.0, 10_000.0])
    # A deliberately clairvoyant target would make 99x if executed on bar 1.
    signals = pd.Series([0, 1, 0, 0, 0])

    _, trades = simulate_ideal(candles, signals)

    assert len(trades) == 1
    # The engine shifts the target: entry is at bar 2, after the price jump.
    assert trades[0]["entry_price"] == pytest.approx(10_000.0)
    assert trades[0]["net_pnl"] == pytest.approx(0.0)


def test_realistic_fill_uses_first_tick_after_latency():
    candles = _candles([100.0, 100.0, 100.0, 100.0])
    signals = pd.Series([0, 1, 0, 0])
    ticks = pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2024-01-01T02:00:00.020Z",
            "2024-01-01T02:00:00.060Z",
            "2024-01-01T03:00:00.060Z",
        ]),
        "price": [99.0, 101.0, 102.0],
        "size": [1.0, 1.0, 1.0],
    })

    _, trades = simulate_realistic(
        candles, signals, ticks, latency_ms=50, fee_bps=0, slippage_bps=0
    )

    assert len(trades) == 1
    assert trades[0]["entry_price"] == pytest.approx(101.0)
    assert trades[0]["entry_time"] == pytest.approx(pd.Timestamp("2024-01-01T02:00:00.060Z").timestamp())
