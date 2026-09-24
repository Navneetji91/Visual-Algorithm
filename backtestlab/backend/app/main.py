"""
BacktestLab — FastAPI application.

Main entry point with CORS, REST endpoints, and WebSocket replay.
"""

import asyncio
import json
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    BacktestRequest, BacktestResponse,
    OptimizeRequest, OptimizeResult,
    MonteCarloRequest, MonteCarloResult,
    ExplainRequest, ExplainResponse,
    StrategyInfo,
)
from app.data.synthetic import AVAILABLE_SYMBOLS
from app.data.loader import get_candles, VALID_TIMEFRAMES
from app.strategies import STRATEGY_REGISTRY, get_indicator_series, compute_signals
from app.engine import run_backtest
from app.optimize import run_optimization
from app.montecarlo import run_monte_carlo
from app.ai_explain import explain_results

import pandas as pd
import numpy as np


app = FastAPI(
    title="BacktestLab API",
    description="Visual Algorithmic Trading Backtester & Execution Engine",
    version="1.0.0",
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health ---


@app.get("/")
def health():
    return {"status": "ok", "app": "BacktestLab", "version": "1.0.0"}


# --- Symbols ---


@app.get("/symbols")
def get_symbols():
    """List available symbols."""
    return {"symbols": AVAILABLE_SYMBOLS}


# --- Candles ---


@app.get("/candles")
def candles_endpoint(
    symbol: str = Query(default="DEMO-BTC"),
    timeframe: str = Query(default="1h"),
    start: str = Query(default=None),
    end: str = Query(default=None),
):
    """Get OHLCV candle data."""
    try:
        df = get_candles(symbol, timeframe, start, end)
        candles = []
        for _, row in df.iterrows():
            candles.append({
                "time": float(pd.Timestamp(row["time"]).timestamp()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            })
        return {"candles": candles, "count": len(candles)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Strategies ---


@app.get("/strategies")
def get_strategies():
    """List available strategies with parameter schemas."""
    strategies = []
    for key, info in STRATEGY_REGISTRY.items():
        strategies.append(
            StrategyInfo(
                name=info["name"],
                key=key,
                description=info["description"],
                params=info["params"],
            )
        )
    return {"strategies": strategies}


# --- Backtest ---


@app.post("/backtest")
def backtest_endpoint(req: BacktestRequest):
    """Run a backtest with both ideal and realistic execution."""
    try:
        result = run_backtest(
            symbol=req.symbol,
            timeframe=req.timeframe,
            start=req.start,
            end=req.end,
            strategy=req.strategy,
            params=req.params,
            long_only=req.long_only,
            initial_capital=req.initial_capital,
            fee_bps=req.fee_bps,
            slippage_model=req.slippage_model,
            slippage_bps=req.slippage_bps,
            impact_coeff=req.impact_coeff,
            latency_ms=req.latency_ms,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


# --- Optimize ---


@app.post("/optimize")
def optimize_endpoint(req: OptimizeRequest):
    """Run parameter optimization with train/test split."""
    try:
        result = run_optimization(
            symbol=req.symbol,
            timeframe=req.timeframe,
            start=req.start,
            end=req.end,
            strategy=req.strategy,
            long_only=req.long_only,
            initial_capital=req.initial_capital,
            fee_bps=req.fee_bps,
            slippage_model=req.slippage_model,
            slippage_bps=req.slippage_bps,
            impact_coeff=req.impact_coeff,
            latency_ms=req.latency_ms,
            param_ranges=req.param_ranges,
            train_pct=req.train_pct,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


# --- Monte Carlo ---


@app.post("/montecarlo")
def montecarlo_endpoint(req: MonteCarloRequest):
    """Run Monte Carlo simulation."""
    try:
        result = run_monte_carlo(
            trade_returns=req.trade_returns,
            initial_capital=req.initial_capital,
            n_simulations=req.n_simulations,
            n_trades=req.n_trades,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monte Carlo failed: {str(e)}")


# --- Explain ---


@app.post("/explain")
def explain_endpoint(req: ExplainRequest):
    """Get AI or rule-based analysis of results."""
    try:
        result = explain_results(
            stats=req.stats,
            trades_summary=req.trades_summary,
            strategy_name=req.strategy_name,
            symbol=req.symbol,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explain failed: {str(e)}")


# --- WebSocket Replay ---


@app.websocket("/replay")
async def replay_endpoint(websocket: WebSocket):
    """
    WebSocket replay mode.

    Client sends config JSON, then server streams candles one at a time.
    Client can send: {"action": "pause"}, {"action": "resume"},
                     {"action": "speed", "value": 2.0},
                     {"action": "seek", "index": 100}
    """
    await websocket.accept()

    try:
        # Receive config
        config_raw = await websocket.receive_text()
        config = json.loads(config_raw)

        from app.schemas import ReplayConfig
        replay_config = ReplayConfig(**config)

        # Load data
        candles = get_candles(
            replay_config.symbol, replay_config.timeframe,
            replay_config.start, replay_config.end,
        )

        if len(candles) < 5:
            await websocket.send_json({"error": "Not enough data"})
            return

        # Compute signals and indicators
        params = replay_config.params
        signals = compute_signals(candles, replay_config.strategy, params, replay_config.long_only)
        indicators = get_indicator_series(candles, replay_config.strategy, params)

        # Run full backtest for the equity curve
        from app.data.loader import get_ticks_for_range
        ticks = get_ticks_for_range(replay_config.symbol, replay_config.start, replay_config.end)
        from app.execution import simulate_realistic
        equity, trades = simulate_realistic(
            candles, signals, ticks,
            initial_capital=replay_config.initial_capital,
            fee_bps=replay_config.fee_bps,
            slippage_model=replay_config.slippage_model,
            slippage_bps=replay_config.slippage_bps,
            impact_coeff=replay_config.impact_coeff,
            latency_ms=replay_config.latency_ms,
        )

        # Pre-compute candle times
        candle_times = candles["time"].apply(
            lambda t: float(pd.Timestamp(t).timestamp())
        ).values

        # Pre-compute markers
        markers_by_time = {}
        for t in trades:
            entry_t = t["entry_time"]
            if entry_t not in markers_by_time:
                markers_by_time[entry_t] = []
            markers_by_time[entry_t].append({
                "time": entry_t,
                "position": "belowBar",
                "color": "#26a69a" if t["side"] == "long" else "#ef5350",
                "shape": "arrowUp" if t["side"] == "long" else "arrowDown",
                "text": f"{'BUY' if t['side'] == 'long' else 'SELL'} @ {t['entry_price']:.2f}",
            })
            if t["exit_time"] > 0:
                exit_t = t["exit_time"]
                if exit_t not in markers_by_time:
                    markers_by_time[exit_t] = []
                markers_by_time[exit_t].append({
                    "time": exit_t,
                    "position": "aboveBar",
                    "color": "#ef5350" if t["side"] == "long" else "#26a69a",
                    "shape": "arrowDown" if t["side"] == "long" else "arrowUp",
                    "text": f"EXIT PnL: {t['net_pnl']:.2f}",
                })

        speed = replay_config.speed
        paused = False
        idx = 0
        total = len(candles)

        await websocket.send_json({"type": "init", "total": total})

        while idx < total:
            # Check for client messages (non-blocking)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                cmd = json.loads(msg)
                action = cmd.get("action", "")
                if action == "pause":
                    paused = True
                elif action == "resume":
                    paused = False
                elif action == "speed":
                    speed = float(cmd.get("value", 1.0))
                elif action == "seek":
                    idx = int(cmd.get("index", 0))
                    idx = max(0, min(idx, total - 1))
            except asyncio.TimeoutError:
                pass

            if paused:
                await asyncio.sleep(0.1)
                continue

            ct = candle_times[idx]
            row = candles.iloc[idx]

            # Build candle data
            candle_data = {
                "time": ct,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }

            # Indicator values at this index
            ind_vals = {}
            for name, vals in indicators.items():
                v = vals[idx]
                ind_vals[name] = v if v is not None and not (isinstance(v, float) and np.isnan(v)) else None

            # Markers at this time
            time_markers = markers_by_time.get(ct, [])

            # Equity
            eq_val = float(equity[idx])

            payload = {
                "type": "candle",
                "index": idx,
                "candle": candle_data,
                "indicators": ind_vals,
                "markers": time_markers,
                "equity": {"time": ct, "value": eq_val},
            }

            await websocket.send_json(payload)
            idx += 1

            # Delay based on speed (base: 200ms per candle at speed 1.0)
            delay = 0.2 / speed
            await asyncio.sleep(delay)

        await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
