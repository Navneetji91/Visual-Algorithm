// TypeScript types mirroring the Pydantic schemas

export interface CandleData {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface MarkerData {
  time: number;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: "arrowUp" | "arrowDown";
  text: string;
}

export interface TradeData {
  entry_time: number;
  exit_time: number;
  side: "long" | "short";
  entry_price: number;
  exit_price: number;
  size: number;
  gross_pnl: number;
  fees: number;
  slippage_cost: number;
  net_pnl: number;
  return_pct: number;
  bars_held: number;
}

export interface EquityPoint {
  time: number;
  value: number;
}

export interface Stats {
  total_return: number;
  cagr: number;
  annualized_volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  max_drawdown_duration: number;
  calmar_ratio: number;
  exposure_pct: number;
  total_fees: number;
  total_slippage: number;
  win_rate: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  expectancy: number;
  num_trades: number;
}

export interface BacktestResponse {
  candles: CandleData[];
  indicators: Record<string, (number | null)[]>;
  markers: MarkerData[];
  trades: TradeData[];
  equity_ideal: EquityPoint[];
  equity_realistic: EquityPoint[];
  equity_buyhold: EquityPoint[];
  drawdown: EquityPoint[];
  stats_ideal: Stats;
  stats_realistic: Stats;
  stats_buyhold: Stats;
}

export interface StrategyParam {
  name: string;
  type: "int" | "float";
  default: number;
  min: number;
  max: number;
  step: number;
  description: string;
}

export interface StrategyInfo {
  name: string;
  key: string;
  description: string;
  params: StrategyParam[];
}

export interface BacktestRequest {
  symbol: string;
  timeframe: string;
  start?: string;
  end?: string;
  strategy: string;
  params: Record<string, number>;
  long_only: boolean;
  initial_capital: number;
  fee_bps: number;
  slippage_model: string;
  slippage_bps: number;
  impact_coeff: number;
  latency_ms: number;
}

export interface OptimizeRequest extends Omit<BacktestRequest, "params"> {
  param_ranges: Record<string, number[]>;
  train_pct: number;
}

export interface OptimizeResult {
  param1_name: string;
  param2_name: string;
  param1_values: number[];
  param2_values: number[];
  train_sharpe_matrix: number[][];
  train_return_matrix: number[][];
  test_sharpe_matrix: number[][];
  test_return_matrix: number[][];
  best_params: Record<string, number>;
  best_train_sharpe: number;
  best_test_sharpe: number;
  overfit_warning: boolean;
  overfit_message: string;
}

export interface MonteCarloResult {
  percentile_5: number[];
  percentile_25: number[];
  percentile_50: number[];
  percentile_75: number[];
  percentile_95: number[];
  probability_of_loss: number;
  mean_final_equity: number;
  median_final_equity: number;
}

export interface ExplainResponse {
  analysis: string;
  source: "ai" | "rule_based";
}

export interface ReplayMessage {
  type: "init" | "candle" | "done" | "error";
  total?: number;
  index?: number;
  candle?: CandleData;
  indicators?: Record<string, number | null>;
  markers?: MarkerData[];
  equity?: EquityPoint;
  message?: string;
}
