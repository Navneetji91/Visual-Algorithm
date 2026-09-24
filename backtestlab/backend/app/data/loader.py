"""
Data loader: loads tick data, resamples to OHLCV candles, caches results.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional

from app.data.synthetic import get_or_generate_ticks, AVAILABLE_SYMBOLS, DATA_DIR

# Cache directory for resampled candles
CACHE_DIR = DATA_DIR / "cache"

VALID_TIMEFRAMES = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}

PERIODS_PER_YEAR = {
    "1m": 365 * 24 * 60,
    "5m": 365 * 24 * 12,
    "15m": 365 * 24 * 4,
    "30m": 365 * 24 * 2,
    "1h": 365 * 24,
    "4h": 365 * 6,
    "1d": 365,
}


def load_ticks(symbol: str) -> pd.DataFrame:
    """Load tick data for a symbol (generate synthetic if needed)."""
    return get_or_generate_ticks(symbol)


def resample_to_candles(
    ticks: pd.DataFrame,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Resample tick data to OHLCV candles using Pandas resample.

    Args:
        ticks: DataFrame with columns [timestamp, price, size]
        timeframe: One of '1m', '5m', '15m', '30m', '1h', '4h', '1d'
        start: Optional start datetime string
        end: Optional end datetime string

    Returns:
        DataFrame with columns [time, open, high, low, close, volume]
        indexed by candle open time.
    """
    if timeframe not in VALID_TIMEFRAMES:
        raise ValueError(f"Invalid timeframe: {timeframe}. Valid: {list(VALID_TIMEFRAMES.keys())}")

    df = ticks.copy()

    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Filter date range
    if start:
        df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

    if df.empty:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

    df = df.set_index("timestamp")

    freq = VALID_TIMEFRAMES[timeframe]
    ohlcv = df["price"].resample(freq).agg(["first", "max", "min", "last"])
    ohlcv.columns = ["open", "high", "low", "close"]
    ohlcv["volume"] = df["size"].resample(freq).sum()

    # Drop NaN rows (periods with no ticks)
    ohlcv = ohlcv.dropna(subset=["open"])
    ohlcv = ohlcv.reset_index()
    ohlcv = ohlcv.rename(columns={"timestamp": "time"})

    return ohlcv


def get_candles(
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get OHLCV candles for a symbol, with Parquet caching.

    Uses cache key: symbol + timeframe (full data cached, then filtered).
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = f"{symbol.lower()}_{timeframe}"
    cache_path = CACHE_DIR / f"{cache_key}_candles.parquet"

    if cache_path.exists():
        candles = pd.read_parquet(cache_path)
    else:
        ticks = load_ticks(symbol)
        candles = resample_to_candles(ticks, timeframe)
        # Cache full candle data
        table = pa.Table.from_pandas(candles, preserve_index=False)
        pq.write_table(table, cache_path, compression="snappy")

    # Apply date filter
    if start:
        candles = candles[candles["time"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        candles = candles[candles["time"] <= pd.Timestamp(end, tz="UTC")]

    return candles.reset_index(drop=True)


def get_ticks_for_range(
    symbol: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """Get raw tick data for a date range."""
    ticks = load_ticks(symbol)

    if start:
        ticks = ticks[ticks["timestamp"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        ticks = ticks[ticks["timestamp"] <= pd.Timestamp(end, tz="UTC")]

    return ticks.reset_index(drop=True)
