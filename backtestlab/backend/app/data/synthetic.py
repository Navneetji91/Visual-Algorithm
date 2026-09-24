"""
Synthetic tick data generator using Geometric Brownian Motion
with GARCH-like volatility clustering and regime shifts.

Generates realistic-looking crypto tick data for backtesting demos
without requiring any external data downloads.
"""

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def generate_synthetic_ticks(
    symbol: str,
    start_price: float,
    base_vol: float = 0.02,
    days: int = 90,
    ticks_per_day: int = 80_000,
    seed: int = 42,
    regime_shift_prob: float = 0.0003,
) -> pd.DataFrame:
    """
    Generate synthetic tick data with realistic microstructure.

    Uses Geometric Brownian Motion with:
    - GARCH(1,1)-like volatility clustering
    - Regime shifts between trending and mean-reverting periods
    - Irregular timestamps at millisecond precision
    - Volume/size that correlates with volatility

    Args:
        symbol: Symbol name (e.g., "DEMO-BTC")
        start_price: Initial price
        base_vol: Base annualized volatility (e.g., 0.60 = 60%)
        days: Number of days to generate
        ticks_per_day: Average ticks per day
        seed: Random seed for reproducibility
        regime_shift_prob: Probability of regime change per tick

    Returns:
        DataFrame with columns: [timestamp, price, size]
    """
    rng = np.random.default_rng(seed)
    total_ticks = days * ticks_per_day

    # --- Timestamps: irregular intervals (exponential distribution) ---
    # Average interval = 1 day / ticks_per_day in milliseconds
    avg_interval_ms = (24 * 3600 * 1000) / ticks_per_day
    intervals_ms = rng.exponential(avg_interval_ms, size=total_ticks).astype(np.int64)
    intervals_ms = np.maximum(intervals_ms, 1)  # at least 1ms apart
    cumulative_ms = np.cumsum(intervals_ms)

    start_ts = pd.Timestamp("2024-01-01", tz="UTC")
    timestamps = start_ts + pd.to_timedelta(cumulative_ms, unit="ms")

    # --- GARCH-like volatility ---
    # sigma_t^2 = omega + alpha * r_{t-1}^2 + beta * sigma_{t-1}^2
    omega = base_vol**2 * (1 - 0.85 - 0.10) / (365 * ticks_per_day)
    alpha = 0.10
    beta = 0.85

    # --- Regime shifts ---
    # regimes: 0 = range-bound (mean-reverting), 1 = trending
    regimes = np.zeros(total_ticks, dtype=np.int8)
    regime = 0
    drift_multipliers = np.zeros(total_ticks)
    for i in range(1, total_ticks):
        if rng.random() < regime_shift_prob:
            regime = 1 - regime
        regimes[i] = regime
        # trending regime: add a drift; range-bound: slight mean-reversion
        if regime == 1:
            drift_multipliers[i] = rng.choice([-1, 1]) * 0.5  # directional
        else:
            drift_multipliers[i] = 0.0

    # --- Generate returns with GARCH vol ---
    innovations = rng.standard_normal(total_ticks)
    sigma2 = np.full(total_ticks, omega / (1 - alpha - beta))
    returns = np.zeros(total_ticks)

    dt = 1.0 / (365 * ticks_per_day)

    for i in range(1, total_ticks):
        sigma2[i] = omega + alpha * returns[i - 1] ** 2 + beta * sigma2[i - 1]
        sigma = np.sqrt(sigma2[i])
        drift = drift_multipliers[i] * sigma * np.sqrt(dt) * 10
        returns[i] = drift + sigma * innovations[i] * np.sqrt(dt)

    # --- Price path ---
    log_prices = np.log(start_price) + np.cumsum(returns)
    prices = np.exp(log_prices)

    # --- Sizes: correlated with volatility ---
    base_size = 0.01 if "BTC" in symbol else 0.1
    vol_factor = np.sqrt(sigma2) / np.sqrt(sigma2.mean())
    sizes = base_size * vol_factor * rng.exponential(1.0, size=total_ticks)
    sizes = np.round(sizes, 6)

    # --- Build DataFrame ---
    df = pd.DataFrame(
        {
            "timestamp": timestamps[:total_ticks],
            "price": np.round(prices, 2),
            "size": sizes,
        }
    )

    return df


def save_ticks_parquet(df: pd.DataFrame, symbol: str) -> Path:
    """Save tick DataFrame to Parquet file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{symbol.lower()}_ticks.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path, compression="snappy")
    return path


def get_or_generate_ticks(symbol: str) -> pd.DataFrame:
    """Load ticks from Parquet cache or generate if not present."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{symbol.lower()}_ticks.parquet"

    if path.exists():
        return pd.read_parquet(path)

    # Symbol configs
    configs = {
        "DEMO-BTC": {"start_price": 42000.0, "base_vol": 0.60, "seed": 42},
        "DEMO-ETH": {"start_price": 2200.0, "base_vol": 0.75, "seed": 123},
    }

    if symbol not in configs:
        raise ValueError(f"Unknown symbol: {symbol}. Available: {list(configs.keys())}")

    cfg = configs[symbol]
    df = generate_synthetic_ticks(symbol=symbol, **cfg)
    save_ticks_parquet(df, symbol)
    return df


AVAILABLE_SYMBOLS = ["DEMO-BTC", "DEMO-ETH"]
