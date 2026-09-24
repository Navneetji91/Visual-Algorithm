"""
Tests for metrics module.

Uses known inputs to verify correctness:
- Constant returns (zero volatility)
- Known drawdown sequences
- Empty trade lists
- Edge cases (single bar, zero equity)
"""

import numpy as np
import pytest
import sys
import os

# Add parent dir to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.metrics import (
    total_return,
    cagr,
    annualized_volatility,
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
    drawdown_series,
    compute_trade_stats,
    compute_all_metrics,
)


class TestTotalReturn:
    def test_positive_return(self):
        eq = np.array([10000, 11000, 12000, 11500])
        assert total_return(eq) == pytest.approx(0.15, rel=1e-6)

    def test_negative_return(self):
        eq = np.array([10000, 9000, 8000])
        assert total_return(eq) == pytest.approx(-0.2, rel=1e-6)

    def test_zero_return(self):
        eq = np.array([10000, 10000])
        assert total_return(eq) == pytest.approx(0.0)

    def test_single_point(self):
        eq = np.array([10000])
        assert total_return(eq) == 0.0

    def test_empty(self):
        eq = np.array([])
        assert total_return(eq) == 0.0


class TestCAGR:
    def test_known_cagr(self):
        # 100% return over 1 year = 100% CAGR
        ppy = 365 * 24  # hourly candles
        n_periods = ppy  # exactly 1 year
        eq = np.linspace(10000, 20000, n_periods + 1)
        result = cagr(eq, ppy)
        assert result == pytest.approx(1.0, rel=0.01)

    def test_flat_equity(self):
        eq = np.array([10000] * 100)
        assert cagr(eq, 365 * 24) == pytest.approx(0.0)

    def test_single_point(self):
        assert cagr(np.array([10000]), 365 * 24) == 0.0


class TestVolatility:
    def test_constant_returns(self):
        """Constant returns → zero volatility."""
        # Price goes up by exactly 1% each period
        eq = 10000 * np.cumprod(np.concatenate([[1], np.full(99, 1.01)]))
        returns = np.diff(eq) / eq[:-1]
        vol = annualized_volatility(returns, 365 * 24)
        assert vol == pytest.approx(0.0, abs=1e-10)

    def test_nonzero_volatility(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, size=1000)
        vol = annualized_volatility(returns, 365 * 24)
        assert vol > 0


class TestSharpeRatio:
    def test_zero_volatility(self):
        """Constant positive returns → Sharpe = 0 (by our convention: std=0)."""
        returns = np.full(100, 0.01)
        assert sharpe_ratio(returns, 365 * 24) == 0.0

    def test_positive_sharpe(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.01, size=1000)
        s = sharpe_ratio(returns, 365 * 24)
        assert s > 0

    def test_negative_sharpe(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(-0.005, 0.01, size=1000)
        s = sharpe_ratio(returns, 365 * 24)
        assert s < 0


class TestSortinoRatio:
    def test_no_downside(self):
        """All positive returns → Sortino = inf."""
        returns = np.full(100, 0.01)
        s = sortino_ratio(returns, 365 * 24)
        assert s == float("inf") or s == 0.0  # depends on convention

    def test_with_downside(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.01, size=1000)
        s = sortino_ratio(returns, 365 * 24)
        assert s > 0


class TestMaxDrawdown:
    def test_known_drawdown(self):
        """Peak at 12000, trough at 9000 → DD = -25%."""
        eq = np.array([10000, 12000, 11000, 9000, 10000])
        dd, dur = max_drawdown(eq)
        assert dd == pytest.approx(-0.25, rel=1e-6)

    def test_no_drawdown(self):
        """Monotonically increasing → DD = 0."""
        eq = np.array([10000, 11000, 12000, 13000])
        dd, dur = max_drawdown(eq)
        assert dd == pytest.approx(0.0)
        assert dur == 0

    def test_full_drawdown(self):
        """100% drawdown."""
        eq = np.array([10000, 5000, 0.01])
        dd, dur = max_drawdown(eq)
        assert dd < -0.99

    def test_single_point(self):
        dd, dur = max_drawdown(np.array([10000]))
        assert dd == 0.0


class TestDrawdownSeries:
    def test_shape(self):
        eq = np.array([10000, 12000, 11000, 9000, 10000])
        dd = drawdown_series(eq)
        assert len(dd) == len(eq)
        assert all(d <= 0 for d in dd)


class TestTradeStats:
    def test_empty_trades(self):
        stats = compute_trade_stats([])
        assert stats["num_trades"] == 0
        assert stats["win_rate"] == 0.0
        assert stats["profit_factor"] == 0.0

    def test_all_winners(self):
        trades = [{"net_pnl": 100, "return_pct": 0.01} for _ in range(10)]
        stats = compute_trade_stats(trades)
        assert stats["win_rate"] == pytest.approx(1.0)
        assert stats["num_trades"] == 10

    def test_mixed_trades(self):
        trades = [
            {"net_pnl": 200, "return_pct": 0.02},
            {"net_pnl": -100, "return_pct": -0.01},
            {"net_pnl": 150, "return_pct": 0.015},
            {"net_pnl": -50, "return_pct": -0.005},
        ]
        stats = compute_trade_stats(trades)
        assert stats["num_trades"] == 4
        assert stats["win_rate"] == pytest.approx(0.5)
        assert stats["profit_factor"] == pytest.approx(350 / 150, rel=1e-6)
        assert stats["avg_win"] == pytest.approx(175.0)
        assert stats["avg_loss"] == pytest.approx(-75.0)


class TestComputeAllMetrics:
    def test_basic(self):
        eq = np.array([10000, 10100, 10200, 10150, 10300])
        trades = [
            {"net_pnl": 100, "return_pct": 0.01, "bars_held": 1},
            {"net_pnl": 100, "return_pct": 0.01, "bars_held": 1},
            {"net_pnl": -50, "return_pct": -0.005, "bars_held": 1},
            {"net_pnl": 150, "return_pct": 0.015, "bars_held": 1},
        ]
        metrics = compute_all_metrics(eq, trades, periods_per_year=365 * 24, n_candles=10)
        assert metrics["total_return"] == pytest.approx(0.03, rel=1e-6)
        assert metrics["num_trades"] == 4
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics

    def test_empty(self):
        eq = np.array([10000])
        metrics = compute_all_metrics(eq, [], periods_per_year=365 * 24)
        assert metrics["total_return"] == 0.0
        assert metrics["num_trades"] == 0


class TestCalmarRatio:
    def test_no_drawdown(self):
        eq = np.array([10000, 11000, 12000])
        c = calmar_ratio(eq, 365 * 24)
        assert c == 0.0  # 0 drawdown → 0/0 → 0

    def test_with_drawdown(self):
        eq = np.array([10000, 12000, 9000, 11000])
        c = calmar_ratio(eq, 365 * 24)
        # Just check it's a number
        assert isinstance(c, float)
