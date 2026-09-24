"""
Parameter grid search optimizer with walk-forward train/test split.
"""

import numpy as np
import pandas as pd
from typing import Any, Optional
from itertools import product

from app.data.loader import get_candles, get_ticks_for_range, PERIODS_PER_YEAR
from app.strategies import compute_signals, get_strategy
from app.execution import simulate_realistic
from app.metrics import compute_all_metrics


def run_optimization(
    symbol: str = "DEMO-BTC",
    timeframe: str = "1h",
    start: Optional[str] = None,
    end: Optional[str] = None,
    strategy: str = "sma_crossover",
    long_only: bool = False,
    initial_capital: float = 10_000.0,
    fee_bps: float = 5.0,
    slippage_model: str = "fixed",
    slippage_bps: float = 2.0,
    impact_coeff: float = 0.1,
    latency_ms: float = 50.0,
    param_ranges: Optional[dict[str, list]] = None,
    train_pct: float = 0.7,
) -> dict[str, Any]:
    """
    Grid search optimization with train/test split.

    Optimizes on the train set, then evaluates the best params on the test set
    to detect overfitting.
    """
    if param_ranges is None:
        param_ranges = {}

    # Get strategy info for defaults
    strat_info = get_strategy(strategy)

    # If param_ranges is empty, use defaults for the first two params
    if not param_ranges:
        params_schema = strat_info["params"]
        for p in params_schema[:2]:
            name = p["name"]
            lo, hi, step = p["min"], p["max"], p["step"]
            # Generate ~10 values
            n_vals = min(10, int((hi - lo) / step) + 1)
            if p["type"] == "int":
                vals = np.linspace(lo, hi, n_vals).astype(int).tolist()
                vals = sorted(set(vals))
            else:
                vals = np.linspace(lo, hi, n_vals).tolist()
            param_ranges[name] = vals

    # Load data
    candles = get_candles(symbol, timeframe, start, end)
    ticks = get_ticks_for_range(symbol, start, end)
    ppy = PERIODS_PER_YEAR.get(timeframe, 365 * 24)

    # Train/test split
    split_idx = int(len(candles) * train_pct)
    train_candles = candles.iloc[:split_idx].reset_index(drop=True)
    test_candles = candles.iloc[split_idx:].reset_index(drop=True)

    # Split ticks too
    if len(train_candles) > 0 and len(test_candles) > 0:
        split_time = candles.iloc[split_idx]["time"]
        train_ticks = ticks[ticks["timestamp"] < split_time].reset_index(drop=True)
        test_ticks = ticks[ticks["timestamp"] >= split_time].reset_index(drop=True)
    else:
        train_ticks = ticks
        test_ticks = ticks

    # Get param names (first two for the matrix)
    param_names = list(param_ranges.keys())
    if len(param_names) < 2:
        # Pad with a dummy single-value param
        if len(param_names) == 1:
            param_names.append("_dummy")
            param_ranges["_dummy"] = [0]
        else:
            raise ValueError("Need at least one parameter range for optimization")

    p1_name, p2_name = param_names[0], param_names[1]
    p1_values = param_ranges[p1_name]
    p2_values = param_ranges[p2_name]

    # Grid search
    train_sharpe = np.zeros((len(p1_values), len(p2_values)))
    train_returns = np.zeros((len(p1_values), len(p2_values)))
    test_sharpe = np.zeros((len(p1_values), len(p2_values)))
    test_returns = np.zeros((len(p1_values), len(p2_values)))

    best_train_sharpe = -np.inf
    best_params = {}

    for i, p1 in enumerate(p1_values):
        for j, p2 in enumerate(p2_values):
            params = {p1_name: p1, p2_name: p2}
            # Remove dummy param
            run_params = {k: v for k, v in params.items() if k != "_dummy"}

            try:
                # Train
                if len(train_candles) > 10:
                    train_signals = compute_signals(train_candles, strategy, run_params, long_only)
                    eq_train, trades_train = simulate_realistic(
                        train_candles, train_signals, train_ticks,
                        initial_capital, fee_bps, slippage_model, slippage_bps,
                        impact_coeff, latency_ms,
                    )
                    metrics_train = compute_all_metrics(eq_train, trades_train, ppy, n_candles=len(train_candles))
                    train_sharpe[i, j] = metrics_train["sharpe_ratio"]
                    train_returns[i, j] = metrics_train["total_return"]
                else:
                    train_sharpe[i, j] = 0
                    train_returns[i, j] = 0

                # Test
                if len(test_candles) > 10:
                    test_signals = compute_signals(test_candles, strategy, run_params, long_only)
                    eq_test, trades_test = simulate_realistic(
                        test_candles, test_signals, test_ticks,
                        initial_capital, fee_bps, slippage_model, slippage_bps,
                        impact_coeff, latency_ms,
                    )
                    metrics_test = compute_all_metrics(eq_test, trades_test, ppy, n_candles=len(test_candles))
                    test_sharpe[i, j] = metrics_test["sharpe_ratio"]
                    test_returns[i, j] = metrics_test["total_return"]
                else:
                    test_sharpe[i, j] = 0
                    test_returns[i, j] = 0

                if train_sharpe[i, j] > best_train_sharpe:
                    best_train_sharpe = train_sharpe[i, j]
                    best_params = params.copy()

            except Exception:
                train_sharpe[i, j] = 0
                train_returns[i, j] = 0
                test_sharpe[i, j] = 0
                test_returns[i, j] = 0

    # Get best test sharpe at the best train params
    best_i = 0
    best_j = 0
    for i in range(len(p1_values)):
        for j in range(len(p2_values)):
            if train_sharpe[i, j] == best_train_sharpe:
                best_i, best_j = i, j

    best_test_sharpe_val = float(test_sharpe[best_i, best_j])

    # Overfitting detection
    overfit_warning = False
    overfit_message = ""
    if best_train_sharpe > 0:
        degradation = (best_train_sharpe - best_test_sharpe_val) / best_train_sharpe
        if degradation > 0.5 or best_test_sharpe_val < 0:
            overfit_warning = True
            overfit_message = (
                f"⚠️ Potential overfitting detected! "
                f"Train Sharpe: {best_train_sharpe:.2f}, "
                f"Test Sharpe: {best_test_sharpe_val:.2f} "
                f"({degradation:.0%} degradation). "
                f"The strategy may not generalize to unseen data."
            )

    # Clean NaN/inf
    def clean_matrix(m):
        m = np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0)
        return m.tolist()

    return {
        "param1_name": p1_name,
        "param2_name": p2_name,
        "param1_values": [v if not isinstance(v, np.integer) else int(v) for v in p1_values],
        "param2_values": [v if not isinstance(v, np.integer) else int(v) for v in p2_values],
        "train_sharpe_matrix": clean_matrix(train_sharpe),
        "train_return_matrix": clean_matrix(train_returns),
        "test_sharpe_matrix": clean_matrix(test_sharpe),
        "test_return_matrix": clean_matrix(test_returns),
        "best_params": {k: (int(v) if isinstance(v, np.integer) else v) for k, v in best_params.items() if k != "_dummy"},
        "best_train_sharpe": float(best_train_sharpe) if not np.isinf(best_train_sharpe) else 0.0,
        "best_test_sharpe": best_test_sharpe_val,
        "overfit_warning": overfit_warning,
        "overfit_message": overfit_message,
    }
