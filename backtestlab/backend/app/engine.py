"""
Backtest orchestration engine.

Coordinates data loading, signal computation, execution simulation,
and metrics calculation. Returns a complete backtest result.
"""

import numpy as np
import pandas as pd
from typing import Optional, Any

from app.data.loader import get_candles, get_ticks_for_range, PERIODS_PER_YEAR
from app.strategies import compute_signals, get_indicator_series
from app.execution import simulate_ideal, simulate_realistic, compute_buy_and_hold
from app.metrics import compute_all_metrics, drawdown_series


def run_backtest(
    symbol: str = "DEMO-BTC",
    timeframe: str = "1h",
    start: Optional[str] = None,
    end: Optional[str] = None,
    strategy: str = "sma_crossover",
    params: Optional[dict] = None,
    long_only: bool = False,
    initial_capital: float = 10_000.0,
    fee_bps: float = 5.0,
    slippage_model: str = "fixed",
    slippage_bps: float = 2.0,
    impact_coeff: float = 0.1,
    latency_ms: float = 50.0,
) -> dict[str, Any]:
    """
    Run a complete backtest with both ideal and realistic execution.

    Returns a dict matching the BacktestResponse schema.
    """
    if params is None:
        params = {}

    # 1. Load candle data
    candles = get_candles(symbol, timeframe, start, end)

    if len(candles) < 5:
        raise ValueError(f"Not enough candle data for {symbol} {timeframe}. Got {len(candles)} candles.")

    # Downsample if too many candles (for response size)
    max_candles = 5000
    if len(candles) > max_candles:
        step = len(candles) // max_candles
        candles = candles.iloc[::step].reset_index(drop=True)

    # 2. Compute signals
    signals = compute_signals(candles, strategy, params, long_only)

    # 3. Compute indicator series for chart
    indicators = get_indicator_series(candles, strategy, params)

    # 4. Ideal execution
    equity_ideal, trades_ideal = simulate_ideal(candles, signals, initial_capital)

    # 5. Realistic execution (with tick data)
    ticks = get_ticks_for_range(symbol, start, end)
    equity_realistic, trades_realistic = simulate_realistic(
        candles, signals, ticks,
        initial_capital=initial_capital,
        fee_bps=fee_bps,
        slippage_model=slippage_model,
        slippage_bps=slippage_bps,
        impact_coeff=impact_coeff,
        latency_ms=latency_ms,
    )

    # 6. Buy-and-hold benchmark
    equity_bh = compute_buy_and_hold(candles, initial_capital)

    # 7. Compute metrics
    ppy = PERIODS_PER_YEAR.get(timeframe, 365 * 24)

    total_fees_realistic = sum(t.get("fees", 0) for t in trades_realistic)
    total_slippage_realistic = sum(t.get("slippage_cost", 0) for t in trades_realistic)

    stats_ideal = compute_all_metrics(
        equity_ideal, trades_ideal, ppy, n_candles=len(candles)
    )
    stats_realistic = compute_all_metrics(
        equity_realistic, trades_realistic, ppy,
        total_fees=total_fees_realistic,
        total_slippage=total_slippage_realistic,
        n_candles=len(candles),
    )
    stats_buyhold = compute_all_metrics(
        equity_bh, [], ppy, n_candles=len(candles)
    )

    # 8. Drawdown series (for realistic)
    dd_series = drawdown_series(equity_realistic)

    # 9. Format candle times as unix timestamps (seconds)
    candle_times = candles["time"].apply(
        lambda t: float(pd.Timestamp(t).timestamp())
    ).values

    # 10. Format candles for response
    candles_out = [
        {
            "time": candle_times[i],
            "open": float(candles.iloc[i]["open"]),
            "high": float(candles.iloc[i]["high"]),
            "low": float(candles.iloc[i]["low"]),
            "close": float(candles.iloc[i]["close"]),
            "volume": float(candles.iloc[i].get("volume", 0)),
        }
        for i in range(len(candles))
    ]

    # 11. Format trade markers
    markers = []
    for t in trades_realistic:
        # Entry marker
        markers.append({
            "time": t["entry_time"],
            "position": "belowBar",
            "color": "#26a69a" if t["side"] == "long" else "#ef5350",
            "shape": "arrowUp" if t["side"] == "long" else "arrowDown",
            "text": f"{'BUY' if t['side'] == 'long' else 'SELL'} @ {t['entry_price']:.2f}",
        })
        # Exit marker
        if t["exit_time"] > 0:
            markers.append({
                "time": t["exit_time"],
                "position": "aboveBar",
                "color": "#ef5350" if t["side"] == "long" else "#26a69a",
                "shape": "arrowDown" if t["side"] == "long" else "arrowUp",
                "text": f"EXIT PnL: {t['net_pnl']:.2f}",
            })

    # Sort markers by time (required by Lightweight Charts)
    markers.sort(key=lambda m: m["time"])

    # 12. Format equity curves
    def format_equity(eq: np.ndarray) -> list[dict]:
        return [{"time": candle_times[i], "value": float(eq[i])} for i in range(len(eq))]

    equity_ideal_out = format_equity(equity_ideal)
    equity_realistic_out = format_equity(equity_realistic)
    equity_bh_out = format_equity(equity_bh)
    dd_out = [{"time": candle_times[i], "value": float(dd_series[i])} for i in range(len(dd_series))]

    # 13. Format trades
    trades_out = [
        {
            "entry_time": t["entry_time"],
            "exit_time": t["exit_time"],
            "side": t["side"],
            "entry_price": round(t["entry_price"], 2),
            "exit_price": round(t["exit_price"], 2),
            "size": round(t["size"], 6),
            "gross_pnl": round(t["gross_pnl"], 2),
            "fees": round(t["fees"], 2),
            "slippage_cost": round(t.get("slippage_cost", 0), 2),
            "net_pnl": round(t["net_pnl"], 2),
            "return_pct": round(t["return_pct"], 4),
            "bars_held": t["bars_held"],
        }
        for t in trades_realistic
    ]

    # Replace NaN with None in indicators
    for key in indicators:
        indicators[key] = [None if (v is None or (isinstance(v, float) and np.isnan(v))) else v for v in indicators[key]]

    return {
        "candles": candles_out,
        "indicators": indicators,
        "markers": markers,
        "trades": trades_out,
        "equity_ideal": equity_ideal_out,
        "equity_realistic": equity_realistic_out,
        "equity_buyhold": equity_bh_out,
        "drawdown": dd_out,
        "stats_ideal": {k: _clean_val(v) for k, v in stats_ideal.items()},
        "stats_realistic": {k: _clean_val(v) for k, v in stats_realistic.items()},
        "stats_buyhold": {k: _clean_val(v) for k, v in stats_buyhold.items()},
    }


def _clean_val(v):
    """Clean a value for JSON serialization (handle NaN, inf)."""
    if isinstance(v, float):
        if np.isnan(v) or np.isinf(v):
            return 0.0
    return v
