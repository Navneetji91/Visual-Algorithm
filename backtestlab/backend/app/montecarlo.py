"""
Monte Carlo simulation for trade return resampling.

Shuffles/resamples trade returns to produce percentile bands
of possible equity outcomes.
"""

import numpy as np
from typing import Optional


def run_monte_carlo(
    trade_returns: list[float],
    initial_capital: float = 10_000.0,
    n_simulations: int = 1000,
    n_trades: Optional[int] = None,
) -> dict:
    """
    Monte Carlo simulation by resampling trade returns.

    Args:
        trade_returns: List of trade return fractions (e.g., 0.02 = 2%)
        initial_capital: Starting equity
        n_simulations: Number of random permutations to run
        n_trades: Number of trades per simulation (default: same as input)

    Returns:
        Dict with percentile bands, probability of loss, mean/median final equity
    """
    if not trade_returns:
        return {
            "percentile_5": [initial_capital],
            "percentile_25": [initial_capital],
            "percentile_50": [initial_capital],
            "percentile_75": [initial_capital],
            "percentile_95": [initial_capital],
            "probability_of_loss": 0.0,
            "mean_final_equity": initial_capital,
            "median_final_equity": initial_capital,
        }

    rng = np.random.default_rng(42)
    returns = np.array(trade_returns)
    n = n_trades if n_trades is not None else len(returns)

    # Simulate equity paths
    # Shape: (n_simulations, n_trades + 1)
    equity_paths = np.zeros((n_simulations, n + 1))
    equity_paths[:, 0] = initial_capital

    for sim in range(n_simulations):
        # Resample with replacement
        sampled = rng.choice(returns, size=n, replace=True)
        # Build equity path
        for t in range(n):
            equity_paths[sim, t + 1] = equity_paths[sim, t] * (1 + sampled[t])

    # Compute percentiles at each trade step
    percentiles = {}
    for pct, name in [(5, "percentile_5"), (25, "percentile_25"), (50, "percentile_50"),
                       (75, "percentile_75"), (95, "percentile_95")]:
        percentiles[name] = np.percentile(equity_paths, pct, axis=0).tolist()

    # Final equity distribution
    final_equities = equity_paths[:, -1]
    prob_loss = float(np.mean(final_equities < initial_capital))

    return {
        **percentiles,
        "probability_of_loss": prob_loss,
        "mean_final_equity": float(np.mean(final_equities)),
        "median_final_equity": float(np.median(final_equities)),
    }
