"""
Strategy registry: each strategy is a function that takes a candles DataFrame
and keyword parameters, returning a Series of target positions in {-1, 0, 1}.

Adding a new strategy requires only:
1. Write a function with signature (candles: DataFrame, **params) -> Series
2. Add an entry to STRATEGY_REGISTRY

The registry includes parameter schemas so the frontend can dynamically
build controls (sliders, dropdowns) for each strategy.
"""

import pandas as pd
import numpy as np
from typing import Any, Callable

from app.indicators import sma, rsi, macd


def sma_crossover(candles: pd.DataFrame, fast: int = 10, slow: int = 30, **kwargs) -> pd.Series:
    """
    SMA Crossover strategy.

    Long when fast SMA > slow SMA, flat (or short) otherwise.
    Signals are computed on the close price.
    """
    fast_sma = sma(candles["close"], fast)
    slow_sma = sma(candles["close"], slow)

    position = pd.Series(0, index=candles.index, dtype=np.int8)
    position[fast_sma > slow_sma] = 1
    position[fast_sma < slow_sma] = -1

    return position


def rsi_mean_reversion(
    candles: pd.DataFrame,
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
    **kwargs,
) -> pd.Series:
    """
    RSI mean-reversion strategy.

    Enter long when RSI crosses up out of oversold zone.
    Exit (flat) when RSI crosses into overbought zone.
    """
    rsi_vals = rsi(candles["close"], period)

    position = pd.Series(0, index=candles.index, dtype=np.int8)

    # Vectorized state tracking using forward-fill approach:
    # Mark entry and exit signals, then forward-fill the position
    long_entry = (rsi_vals > oversold) & (rsi_vals.shift(1) <= oversold)
    long_exit = (rsi_vals > overbought) & (rsi_vals.shift(1) <= overbought)
    short_entry = (rsi_vals < overbought) & (rsi_vals.shift(1) >= overbought)
    short_exit = (rsi_vals < oversold) & (rsi_vals.shift(1) >= oversold)

    # Set position signals
    position[long_entry] = 1
    position[long_exit] = 0
    position[short_entry] = -1
    position[short_exit] = 0

    # Mark non-signal bars as NaN for forward-fill
    signal_mask = long_entry | long_exit | short_entry | short_exit
    position[~signal_mask] = np.nan
    position.iloc[0] = 0  # start flat
    position = position.ffill().astype(np.int8)

    return position


def macd_strategy(
    candles: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    **kwargs,
) -> pd.Series:
    """
    MACD crossover strategy.

    Long when MACD line > signal line, flat/short when below.
    """
    macd_line, signal_line, histogram = macd(candles["close"], fast, slow, signal)

    position = pd.Series(0, index=candles.index, dtype=np.int8)
    position[macd_line > signal_line] = 1
    position[macd_line < signal_line] = -1

    return position


# --- Strategy Registry ---

StrategyFn = Callable[[pd.DataFrame, Any], pd.Series]

STRATEGY_REGISTRY: dict[str, dict] = {
    "sma_crossover": {
        "name": "SMA Crossover",
        "description": "Go long when fast SMA crosses above slow SMA, short when below.",
        "function": sma_crossover,
        "params": [
            {
                "name": "fast",
                "type": "int",
                "default": 10,
                "min": 2,
                "max": 100,
                "step": 1,
                "description": "Fast SMA period",
            },
            {
                "name": "slow",
                "type": "int",
                "default": 30,
                "min": 5,
                "max": 200,
                "step": 1,
                "description": "Slow SMA period",
            },
        ],
    },
    "rsi_mean_reversion": {
        "name": "RSI Mean Reversion",
        "description": "Enter long when RSI crosses up out of oversold, exit at overbought. Enter short at overbought, exit at oversold.",
        "function": rsi_mean_reversion,
        "params": [
            {
                "name": "period",
                "type": "int",
                "default": 14,
                "min": 2,
                "max": 50,
                "step": 1,
                "description": "RSI lookback period",
            },
            {
                "name": "oversold",
                "type": "float",
                "default": 30.0,
                "min": 10.0,
                "max": 45.0,
                "step": 1.0,
                "description": "Oversold threshold",
            },
            {
                "name": "overbought",
                "type": "float",
                "default": 70.0,
                "min": 55.0,
                "max": 90.0,
                "step": 1.0,
                "description": "Overbought threshold",
            },
        ],
    },
    "macd_strategy": {
        "name": "MACD Crossover",
        "description": "Long when MACD line is above signal line, short when below.",
        "function": macd_strategy,
        "params": [
            {
                "name": "fast",
                "type": "int",
                "default": 12,
                "min": 2,
                "max": 50,
                "step": 1,
                "description": "Fast EMA period",
            },
            {
                "name": "slow",
                "type": "int",
                "default": 26,
                "min": 10,
                "max": 100,
                "step": 1,
                "description": "Slow EMA period",
            },
            {
                "name": "signal",
                "type": "int",
                "default": 9,
                "min": 2,
                "max": 30,
                "step": 1,
                "description": "Signal line period",
            },
        ],
    },
}


def get_strategy(name: str) -> dict:
    """Get a strategy by name."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}"
        )
    return STRATEGY_REGISTRY[name]


def compute_signals(
    candles: pd.DataFrame, strategy_name: str, params: dict, long_only: bool = False
) -> pd.Series:
    """
    Compute position signals for a strategy.

    Args:
        candles: OHLCV DataFrame
        strategy_name: Key in STRATEGY_REGISTRY
        params: Strategy-specific parameters
        long_only: If True, clip signals to [0, 1] (no shorts)

    Returns:
        Series of target positions in {-1, 0, 1}
    """
    strategy = get_strategy(strategy_name)
    fn = strategy["function"]
    positions = fn(candles, **params)

    if long_only:
        positions = positions.clip(lower=0)

    return positions


def get_indicator_series(
    candles: pd.DataFrame, strategy_name: str, params: dict
) -> dict[str, list]:
    """
    Compute indicator series for a strategy (for chart overlays).

    Returns a dict of indicator_name -> list of values (aligned with candles).
    """
    close = candles["close"]
    indicators: dict[str, list] = {}

    if strategy_name == "sma_crossover":
        fast_period = params.get("fast", 10)
        slow_period = params.get("slow", 30)
        from app.indicators import sma as sma_fn

        indicators["SMA Fast"] = sma_fn(close, fast_period).tolist()
        indicators["SMA Slow"] = sma_fn(close, slow_period).tolist()

    elif strategy_name == "rsi_mean_reversion":
        period = params.get("period", 14)
        from app.indicators import rsi as rsi_fn

        indicators["RSI"] = rsi_fn(close, period).tolist()

    elif strategy_name == "macd_strategy":
        fast = params.get("fast", 12)
        slow = params.get("slow", 26)
        signal = params.get("signal", 9)
        from app.indicators import macd as macd_fn

        macd_line, signal_line, histogram = macd_fn(close, fast, slow, signal)
        indicators["MACD"] = macd_line.tolist()
        indicators["Signal"] = signal_line.tolist()
        indicators["Histogram"] = histogram.tolist()

    return indicators
