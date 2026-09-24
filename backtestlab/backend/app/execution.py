"""
Tick-level execution simulator — the core differentiator.

Signals are computed on candles but fills are simulated on TICKS:
- No look-ahead bias: signals at candle close act only on future ticks
- Latency simulation: fills at first tick >= signal_time + latency_ms
- Slippage: fixed bps or volume/size-based market impact
- Fees: commission in bps per side
- Dual simulation: "ideal" (close fills, no costs) and "realistic"
"""

import numpy as np
import pandas as pd
from typing import Optional


def simulate_ideal(
    candles: pd.DataFrame,
    signals: pd.Series,
    initial_capital: float = 10_000.0,
) -> tuple[np.ndarray, list[dict]]:
    """
    Ideal execution: fills at signal-bar close, no costs.

    Signals are shifted by 1 so position change acts on the NEXT bar's close
    (no look-ahead bias). This is the "too-good-to-be-true" baseline.

    Args:
        candles: OHLCV DataFrame with 'close' and 'time' columns
        signals: Series of target positions {-1, 0, 1}
        initial_capital: Starting equity

    Returns:
        (equity_curve, trades_list)
    """
    close = candles["close"].values.astype(np.float64)
    times = candles["time"].values
    n = len(close)

    # Shift signals: signal at bar i → position effective at bar i+1
    sig = signals.values.copy().astype(np.float64)
    shifted_sig = np.zeros(n)
    shifted_sig[1:] = sig[:-1]

    # Position changes
    pos_changes = np.diff(shifted_sig, prepend=0)

    # Build equity curve
    equity = np.zeros(n)
    equity[0] = initial_capital
    position = 0.0
    cash = initial_capital
    shares = 0.0

    trades = []
    current_trade = None

    for i in range(n):
        new_pos = shifted_sig[i]
        if new_pos != position:
            # Close current position
            if position != 0 and current_trade is not None:
                exit_price = close[i]
                gross_pnl = shares * (exit_price - current_trade["entry_price"]) * (1 if position > 0 else -1)
                current_trade["exit_time"] = float(pd.Timestamp(times[i]).timestamp()) if hasattr(times[i], 'timestamp') else float(times[i]) / 1e9
                current_trade["exit_price"] = exit_price
                current_trade["gross_pnl"] = gross_pnl
                current_trade["fees"] = 0.0
                current_trade["slippage_cost"] = 0.0
                current_trade["net_pnl"] = gross_pnl
                current_trade["return_pct"] = gross_pnl / (current_trade["entry_price"] * shares) if shares > 0 else 0.0
                current_trade["bars_held"] = i - current_trade.get("_entry_idx", 0)
                del current_trade["_entry_idx"]
                trades.append(current_trade)
                cash += gross_pnl

            # Open new position
            if new_pos != 0:
                entry_price = close[i]
                shares = abs(cash * abs(new_pos)) / entry_price
                entry_time = float(pd.Timestamp(times[i]).timestamp()) if hasattr(times[i], 'timestamp') else float(times[i]) / 1e9
                current_trade = {
                    "entry_time": entry_time,
                    "exit_time": 0.0,
                    "side": "long" if new_pos > 0 else "short",
                    "entry_price": entry_price,
                    "exit_price": 0.0,
                    "size": shares,
                    "gross_pnl": 0.0,
                    "fees": 0.0,
                    "slippage_cost": 0.0,
                    "net_pnl": 0.0,
                    "return_pct": 0.0,
                    "bars_held": 0,
                    "_entry_idx": i,
                }
            else:
                shares = 0.0
                current_trade = None

            position = new_pos

        # Mark to market
        if position != 0 and current_trade is not None:
            mtm_pnl = shares * (close[i] - current_trade["entry_price"]) * (1 if position > 0 else -1)
            equity[i] = cash + abs(shares * current_trade["entry_price"]) + mtm_pnl
        else:
            equity[i] = cash

    # Close any open position at the end
    if position != 0 and current_trade is not None:
        exit_price = close[-1]
        gross_pnl = shares * (exit_price - current_trade["entry_price"]) * (1 if position > 0 else -1)
        current_trade["exit_time"] = float(pd.Timestamp(times[-1]).timestamp()) if hasattr(times[-1], 'timestamp') else float(times[-1]) / 1e9
        current_trade["exit_price"] = exit_price
        current_trade["gross_pnl"] = gross_pnl
        current_trade["fees"] = 0.0
        current_trade["slippage_cost"] = 0.0
        current_trade["net_pnl"] = gross_pnl
        current_trade["return_pct"] = gross_pnl / (current_trade["entry_price"] * shares) if shares > 0 else 0.0
        current_trade["bars_held"] = n - 1 - current_trade.get("_entry_idx", 0)
        if "_entry_idx" in current_trade:
            del current_trade["_entry_idx"]
        trades.append(current_trade)

    return equity, trades


def simulate_realistic(
    candles: pd.DataFrame,
    signals: pd.Series,
    ticks: pd.DataFrame,
    initial_capital: float = 10_000.0,
    fee_bps: float = 5.0,
    slippage_model: str = "fixed",
    slippage_bps: float = 2.0,
    impact_coeff: float = 0.1,
    latency_ms: float = 50.0,
) -> tuple[np.ndarray, list[dict]]:
    """
    Realistic tick-level execution simulator.

    - Signal at candle close time t → order placed at t
    - Fill at first tick with timestamp >= t + latency_ms
    - Slippage applied to fill price
    - Fees deducted per side

    Args:
        candles: OHLCV DataFrame
        signals: Target position series {-1, 0, 1}
        ticks: Raw tick DataFrame [timestamp, price, size]
        initial_capital: Starting equity
        fee_bps: Commission per side in basis points
        slippage_model: 'fixed' or 'volume_impact'
        slippage_bps: Base slippage in bps
        impact_coeff: Market impact coefficient
        latency_ms: Execution latency in milliseconds

    Returns:
        (equity_curve, trades_list)
    """
    close = candles["close"].values.astype(np.float64)
    candle_times = candles["time"].values
    n = len(close)

    # Convert candle times to nanoseconds for comparison with ticks
    candle_times_ns = pd.DatetimeIndex(candle_times).astype(np.int64)

    # Tick data
    tick_times_ns = pd.DatetimeIndex(ticks["timestamp"]).astype(np.int64)
    tick_prices = ticks["price"].values.astype(np.float64)
    tick_sizes = ticks["size"].values.astype(np.float64)

    latency_ns = int(latency_ms * 1e6)  # ms to ns

    # Pre-compute rolling average tick volume (for volume impact model)
    if slippage_model == "volume_impact":
        window = min(1000, len(tick_sizes))
        rolling_avg_vol = pd.Series(tick_sizes).rolling(window, min_periods=1).mean().values
    else:
        rolling_avg_vol = None

    # Shift signals: signal at bar i → act on bar i+1
    sig = signals.values.copy().astype(np.float64)
    shifted_sig = np.zeros(n)
    shifted_sig[1:] = sig[:-1]

    # Build equity curve
    equity = np.zeros(n)
    equity[0] = initial_capital
    position = 0.0
    cash = initial_capital
    shares = 0.0
    total_fees = 0.0
    total_slippage = 0.0

    trades = []
    current_trade = None

    for i in range(n):
        new_pos = shifted_sig[i]

        if new_pos != position:
            # Find fill price from ticks
            signal_time_ns = candle_times_ns[i]
            target_time_ns = signal_time_ns + latency_ns

            # Use searchsorted to find the first tick at or after target time
            tick_idx = np.searchsorted(tick_times_ns, target_time_ns, side="left")

            if tick_idx >= len(tick_prices):
                tick_idx = len(tick_prices) - 1

            fill_price = tick_prices[tick_idx]
            # Preserve the actual tick selected by the latency-aware lookup.
            # A candle timestamp is useful for chart alignment, but it is not
            # the execution time and would hide the impact of latency in the
            # trade ledger.
            fill_time = float(pd.Timestamp(ticks["timestamp"].iloc[tick_idx]).timestamp())

            # Apply slippage
            if slippage_model == "fixed":
                slip_bps = slippage_bps
            elif slippage_model == "volume_impact":
                order_size = abs(cash * abs(new_pos - position)) / fill_price if fill_price > 0 else 0
                avg_vol = rolling_avg_vol[tick_idx] if rolling_avg_vol is not None else 1.0
                slip_bps = slippage_bps + impact_coeff * np.sqrt(
                    order_size / max(avg_vol, 1e-10)
                )
            else:
                slip_bps = slippage_bps

            # Close current position
            if position != 0 and current_trade is not None:
                # Direction of close
                is_buy_to_close = position < 0  # closing a short = buying
                slip_direction = 1 if is_buy_to_close else -1
                slipped_price = fill_price * (1 + slip_direction * slip_bps / 10_000)
                fee = abs(shares * slipped_price) * fee_bps / 10_000
                slip_cost = abs(shares * fill_price * slip_bps / 10_000)

                gross_pnl = shares * (slipped_price - current_trade["entry_price"]) * (1 if position > 0 else -1)
                net_pnl = gross_pnl - fee

                exit_time = fill_time

                current_trade["exit_time"] = exit_time
                current_trade["exit_price"] = slipped_price
                current_trade["gross_pnl"] = gross_pnl
                current_trade["fees"] = fee + current_trade.get("_entry_fee", 0)
                current_trade["slippage_cost"] = slip_cost + current_trade.get("_entry_slip", 0)
                current_trade["net_pnl"] = gross_pnl - current_trade["fees"]
                current_trade["return_pct"] = current_trade["net_pnl"] / (current_trade["entry_price"] * shares) if shares > 0 else 0.0
                current_trade["bars_held"] = i - current_trade.get("_entry_idx", 0)

                # Clean up internal fields
                for key in ["_entry_idx", "_entry_fee", "_entry_slip"]:
                    current_trade.pop(key, None)

                trades.append(current_trade)
                cash += current_trade["net_pnl"] + (shares * current_trade["entry_price"])
                total_fees += current_trade["fees"]
                total_slippage += current_trade["slippage_cost"]

            # Open new position
            if new_pos != 0:
                is_buy = new_pos > 0
                slip_direction = 1 if is_buy else -1
                entry_slipped = fill_price * (1 + slip_direction * slip_bps / 10_000)
                shares = abs(cash * abs(new_pos)) / entry_slipped
                entry_fee = abs(shares * entry_slipped) * fee_bps / 10_000
                entry_slip = abs(shares * fill_price * slip_bps / 10_000)
                cash -= abs(shares * entry_slipped) + entry_fee

                entry_time = fill_time

                current_trade = {
                    "entry_time": entry_time,
                    "exit_time": 0.0,
                    "side": "long" if new_pos > 0 else "short",
                    "entry_price": entry_slipped,
                    "exit_price": 0.0,
                    "size": shares,
                    "gross_pnl": 0.0,
                    "fees": 0.0,
                    "slippage_cost": 0.0,
                    "net_pnl": 0.0,
                    "return_pct": 0.0,
                    "bars_held": 0,
                    "_entry_idx": i,
                    "_entry_fee": entry_fee,
                    "_entry_slip": entry_slip,
                }
            else:
                shares = 0.0
                current_trade = None

            position = new_pos

        # Mark to market
        if position != 0 and current_trade is not None:
            mtm_pnl = shares * (close[i] - current_trade["entry_price"]) * (1 if position > 0 else -1)
            equity[i] = cash + abs(shares * current_trade["entry_price"]) + mtm_pnl
        else:
            equity[i] = cash

    # Close open position at end
    if position != 0 and current_trade is not None:
        exit_price = close[-1]
        gross_pnl = shares * (exit_price - current_trade["entry_price"]) * (1 if position > 0 else -1)
        fee = abs(shares * exit_price) * fee_bps / 10_000

        current_trade["exit_time"] = float(pd.Timestamp(candle_times[-1]).timestamp()) if hasattr(candle_times[-1], 'timestamp') else float(candle_times[-1]) / 1e9
        current_trade["exit_price"] = exit_price
        current_trade["gross_pnl"] = gross_pnl
        current_trade["fees"] = fee + current_trade.get("_entry_fee", 0)
        current_trade["slippage_cost"] = current_trade.get("_entry_slip", 0)
        current_trade["net_pnl"] = gross_pnl - current_trade["fees"]
        current_trade["return_pct"] = current_trade["net_pnl"] / (current_trade["entry_price"] * shares) if shares > 0 else 0.0
        current_trade["bars_held"] = n - 1 - current_trade.get("_entry_idx", 0)
        for key in ["_entry_idx", "_entry_fee", "_entry_slip"]:
            current_trade.pop(key, None)
        trades.append(current_trade)
        total_fees += current_trade["fees"]
        total_slippage += current_trade["slippage_cost"]

    return equity, trades


def compute_buy_and_hold(
    candles: pd.DataFrame, initial_capital: float = 10_000.0
) -> np.ndarray:
    """
    Buy-and-hold benchmark: invest all capital at the first close.

    Returns equity curve aligned with candles.
    """
    close = candles["close"].values.astype(np.float64)
    if len(close) == 0:
        return np.array([initial_capital])
    shares = initial_capital / close[0]
    return shares * close
