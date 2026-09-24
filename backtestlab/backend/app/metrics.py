"""
Performance metrics for backtest results.

All computations are vectorized. Annualization uses crypto 24/7 calendar
(365 days/year). Guards against divide-by-zero and empty-trade cases.
"""

import numpy as np
import pandas as pd
from typing import Optional


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Safe division with default for zero denominator."""
    if b == 0 or np.isnan(b):
        return default
    return a / b


def total_return(equity_curve: np.ndarray) -> float:
    """Total return as a fraction (e.g., 0.15 = 15%)."""
    if len(equity_curve) < 2:
        return 0.0
    return (equity_curve[-1] / equity_curve[0]) - 1.0


def cagr(equity_curve: np.ndarray, periods_per_year: float) -> float:
    """Compound Annual Growth Rate."""
    if len(equity_curve) < 2:
        return 0.0
    n_periods = len(equity_curve) - 1
    years = n_periods / periods_per_year
    if years <= 0:
        return 0.0
    total = equity_curve[-1] / equity_curve[0]
    if total <= 0:
        return -1.0
    # ``total ** (1 / years)`` can overflow for very short samples.  Compute
    # in log space and cap at the largest finite float so metrics remain JSON
    # serializable without emitting runtime warnings.
    log_growth = np.log(total) / years
    return float(np.exp(min(log_growth, np.log(np.finfo(np.float64).max))) - 1.0)


def annualized_volatility(returns: np.ndarray, periods_per_year: float) -> float:
    """Annualized volatility of returns."""
    if len(returns) < 2:
        return 0.0
    return float(np.std(returns, ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(
    returns: np.ndarray, periods_per_year: float, risk_free_rate: float = 0.0
) -> float:
    """
    Annualized Sharpe ratio.

    Uses excess returns over the risk-free rate.
    """
    if len(returns) < 2:
        return 0.0
    excess_returns = returns - risk_free_rate / periods_per_year
    mean_excess = np.mean(excess_returns)
    std = np.std(returns, ddof=1)
    if std < 1e-12:
        return 0.0
    return float(mean_excess / std * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: np.ndarray, periods_per_year: float, risk_free_rate: float = 0.0
) -> float:
    """
    Annualized Sortino ratio (uses downside deviation only).
    """
    if len(returns) < 2:
        return 0.0
    excess_returns = returns - risk_free_rate / periods_per_year
    mean_excess = np.mean(excess_returns)
    downside = returns[returns < 0]
    if len(downside) == 0:
        return float("inf") if mean_excess > 0 else 0.0
    if len(downside) < 2:
        return 0.0
    downside_std = np.std(downside, ddof=1)
    if downside_std == 0:
        return 0.0
    return float(mean_excess / downside_std * np.sqrt(periods_per_year))


def max_drawdown(equity_curve: np.ndarray) -> tuple[float, int]:
    """
    Maximum drawdown and its duration in periods.

    Returns:
        (max_dd_fraction, duration_in_periods)
        max_dd_fraction is negative (e.g., -0.15 = -15%)
    """
    if len(equity_curve) < 2:
        return 0.0, 0

    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak

    max_dd = float(np.min(drawdown))

    # Duration: longest time spent below previous peak
    is_in_dd = equity_curve < peak
    if not np.any(is_in_dd):
        return 0.0, 0

    # Find the longest consecutive run of being in drawdown
    dd_changes = np.diff(is_in_dd.astype(int))
    starts = np.where(dd_changes == 1)[0] + 1
    ends = np.where(dd_changes == -1)[0] + 1

    # Handle edge cases
    if is_in_dd[0]:
        starts = np.insert(starts, 0, 0)
    if is_in_dd[-1]:
        ends = np.append(ends, len(equity_curve))

    if len(starts) == 0 or len(ends) == 0:
        return max_dd, 0

    min_len = min(len(starts), len(ends))
    durations = ends[:min_len] - starts[:min_len]
    max_duration = int(np.max(durations)) if len(durations) > 0 else 0

    return max_dd, max_duration


def calmar_ratio(equity_curve: np.ndarray, periods_per_year: float) -> float:
    """Calmar ratio: CAGR / |max drawdown|."""
    c = cagr(equity_curve, periods_per_year)
    dd, _ = max_drawdown(equity_curve)
    return _safe_div(c, abs(dd))


def drawdown_series(equity_curve: np.ndarray) -> np.ndarray:
    """Compute the drawdown series (all values <= 0)."""
    if len(equity_curve) < 1:
        return np.array([])
    peak = np.maximum.accumulate(equity_curve)
    return (equity_curve - peak) / peak


def compute_trade_stats(trades: list[dict]) -> dict:
    """
    Compute trade-level statistics.

    Args:
        trades: List of trade dicts with at least 'net_pnl' and 'return_pct'

    Returns:
        Dict with win_rate, profit_factor, avg_win, avg_loss, expectancy, num_trades
    """
    if not trades:
        return {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0,
            "num_trades": 0,
        }

    pnls = np.array([t["net_pnl"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]

    win_rate = len(wins) / len(pnls) if len(pnls) > 0 else 0.0
    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0
    total_wins = float(np.sum(wins)) if len(wins) > 0 else 0.0
    total_losses = float(np.abs(np.sum(losses))) if len(losses) > 0 else 0.0
    profit_factor = _safe_div(total_wins, total_losses)
    expectancy = float(np.mean(pnls))

    return {
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "num_trades": len(pnls),
    }


def compute_all_metrics(
    equity_curve: np.ndarray,
    trades: list[dict],
    periods_per_year: float,
    total_fees: float = 0.0,
    total_slippage: float = 0.0,
    n_candles: int = 0,
) -> dict:
    """
    Compute all performance metrics.

    Args:
        equity_curve: Array of equity values over time
        trades: List of trade dicts
        periods_per_year: Annualization factor
        total_fees: Total fees paid
        total_slippage: Total slippage cost
        n_candles: Total number of candles in the test period

    Returns:
        Dict with all metrics
    """
    eq = np.asarray(equity_curve, dtype=np.float64)

    if len(eq) < 2:
        returns = np.array([0.0])
    else:
        returns = np.diff(eq) / eq[:-1]
        # Handle any inf/nan from zero equity
        returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=-1.0)

    dd, dd_dur = max_drawdown(eq)
    trade_stats = compute_trade_stats(trades)

    # Exposure: fraction of time with a position
    if n_candles > 0 and trades:
        bars_held = sum(t.get("bars_held", 0) for t in trades)
        exposure = min(bars_held / n_candles, 1.0)
    else:
        exposure = 0.0

    return {
        "total_return": total_return(eq),
        "cagr": cagr(eq, periods_per_year),
        "annualized_volatility": annualized_volatility(returns, periods_per_year),
        "sharpe_ratio": sharpe_ratio(returns, periods_per_year),
        "sortino_ratio": sortino_ratio(returns, periods_per_year),
        "max_drawdown": dd,
        "max_drawdown_duration": dd_dur,
        "calmar_ratio": calmar_ratio(eq, periods_per_year),
        "exposure_pct": exposure,
        "total_fees": total_fees,
        "total_slippage": total_slippage,
        **trade_stats,
    }
