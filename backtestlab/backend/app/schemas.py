"""
Pydantic v2 request/response models for the BacktestLab API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any


# --- Request Models ---


class BacktestRequest(BaseModel):
    """Request body for POST /backtest."""

    symbol: str = Field(default="DEMO-BTC", description="Symbol to backtest")
    timeframe: str = Field(default="1h", description="Candle timeframe")
    start: Optional[str] = Field(default=None, description="Start datetime (ISO format)")
    end: Optional[str] = Field(default=None, description="End datetime (ISO format)")
    strategy: str = Field(default="sma_crossover", description="Strategy name")
    params: dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    long_only: bool = Field(default=False, description="Long-only mode")
    initial_capital: float = Field(default=10_000.0, ge=100, description="Initial capital")
    fee_bps: float = Field(default=5.0, ge=0, description="Fee in basis points per side")
    slippage_model: str = Field(
        default="fixed", description="Slippage model: 'fixed' or 'volume_impact'"
    )
    slippage_bps: float = Field(default=2.0, ge=0, description="Base slippage in bps")
    impact_coeff: float = Field(
        default=0.1, ge=0, description="Market impact coefficient (for volume_impact model)"
    )
    latency_ms: float = Field(default=50.0, ge=0, description="Execution latency in ms")


class OptimizeRequest(BaseModel):
    """Request body for POST /optimize."""

    symbol: str = Field(default="DEMO-BTC")
    timeframe: str = Field(default="1h")
    start: Optional[str] = None
    end: Optional[str] = None
    strategy: str = Field(default="sma_crossover")
    long_only: bool = False
    initial_capital: float = Field(default=10_000.0, ge=100)
    fee_bps: float = Field(default=5.0, ge=0)
    slippage_model: str = "fixed"
    slippage_bps: float = Field(default=2.0, ge=0)
    impact_coeff: float = Field(default=0.1, ge=0)
    latency_ms: float = Field(default=50.0, ge=0)
    param_ranges: dict[str, list] = Field(
        default_factory=dict,
        description="Parameter ranges for grid search: {param_name: [val1, val2, ...]}",
    )
    train_pct: float = Field(default=0.7, ge=0.1, le=0.95, description="Train split fraction")


class MonteCarloRequest(BaseModel):
    """Request body for POST /montecarlo."""

    trade_returns: list[float] = Field(
        description="List of trade return percentages"
    )
    initial_capital: float = Field(default=10_000.0, ge=100)
    n_simulations: int = Field(default=1000, ge=100, le=10000)
    n_trades: Optional[int] = Field(
        default=None, description="Number of trades to simulate (default: same as input)"
    )


class ReplayConfig(BaseModel):
    """WebSocket replay configuration."""

    symbol: str = "DEMO-BTC"
    timeframe: str = "1h"
    start: Optional[str] = None
    end: Optional[str] = None
    strategy: str = "sma_crossover"
    params: dict[str, Any] = Field(default_factory=dict)
    long_only: bool = False
    initial_capital: float = 10_000.0
    fee_bps: float = 5.0
    slippage_model: str = "fixed"
    slippage_bps: float = 2.0
    impact_coeff: float = 0.1
    latency_ms: float = 50.0
    speed: float = Field(default=1.0, ge=0.1, le=50.0, description="Replay speed multiplier")


class ExplainRequest(BaseModel):
    """Request body for POST /explain."""

    stats: dict[str, Any] = Field(description="Backtest statistics")
    trades_summary: dict[str, Any] = Field(
        default_factory=dict, description="Trades summary"
    )
    strategy_name: str = ""
    symbol: str = ""


# --- Response Models ---


class CandleData(BaseModel):
    time: float  # Unix timestamp in seconds
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class MarkerData(BaseModel):
    time: float
    position: str  # 'aboveBar' or 'belowBar'
    color: str
    shape: str  # 'arrowUp' or 'arrowDown'
    text: str


class TradeData(BaseModel):
    entry_time: float
    exit_time: float
    side: str
    entry_price: float
    exit_price: float
    size: float
    gross_pnl: float
    fees: float
    slippage_cost: float
    net_pnl: float
    return_pct: float
    bars_held: int


class EquityPoint(BaseModel):
    time: float
    value: float


class BacktestResponse(BaseModel):
    candles: list[CandleData]
    indicators: dict[str, list[Optional[float]]]
    markers: list[MarkerData]
    trades: list[TradeData]
    equity_ideal: list[EquityPoint]
    equity_realistic: list[EquityPoint]
    equity_buyhold: list[EquityPoint]
    drawdown: list[EquityPoint]
    stats_ideal: dict[str, Any]
    stats_realistic: dict[str, Any]
    stats_buyhold: dict[str, Any]


class StrategyInfo(BaseModel):
    name: str
    key: str
    description: str
    params: list[dict[str, Any]]


class OptimizeResult(BaseModel):
    param1_name: str
    param2_name: str
    param1_values: list[Any]
    param2_values: list[Any]
    train_sharpe_matrix: list[list[float]]
    train_return_matrix: list[list[float]]
    test_sharpe_matrix: list[list[float]]
    test_return_matrix: list[list[float]]
    best_params: dict[str, Any]
    best_train_sharpe: float
    best_test_sharpe: float
    overfit_warning: bool
    overfit_message: str


class MonteCarloResult(BaseModel):
    percentile_5: list[float]
    percentile_25: list[float]
    percentile_50: list[float]
    percentile_75: list[float]
    percentile_95: list[float]
    probability_of_loss: float
    mean_final_equity: float
    median_final_equity: float


class ExplainResponse(BaseModel):
    analysis: str
    source: str  # 'ai' or 'rule_based'
