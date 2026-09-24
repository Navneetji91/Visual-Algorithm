// API client for BacktestLab backend

import type {
  BacktestRequest,
  BacktestResponse,
  StrategyInfo,
  OptimizeRequest,
  OptimizeResult,
  MonteCarloResult,
  ExplainResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }
  return response.json();
}

export async function getSymbols(): Promise<string[]> {
  const data = await fetchJSON<{ symbols: string[] }>(`${API_BASE}/symbols`);
  return data.symbols;
}

export async function getStrategies(): Promise<StrategyInfo[]> {
  const data = await fetchJSON<{ strategies: StrategyInfo[] }>(`${API_BASE}/strategies`);
  return data.strategies;
}

export async function runBacktest(req: BacktestRequest): Promise<BacktestResponse> {
  return fetchJSON<BacktestResponse>(`${API_BASE}/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function runOptimize(req: OptimizeRequest): Promise<OptimizeResult> {
  return fetchJSON<OptimizeResult>(`${API_BASE}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function runMonteCarlo(
  tradeReturns: number[],
  initialCapital: number = 10000,
  nSimulations: number = 1000
): Promise<MonteCarloResult> {
  return fetchJSON<MonteCarloResult>(`${API_BASE}/montecarlo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      trade_returns: tradeReturns,
      initial_capital: initialCapital,
      n_simulations: nSimulations,
    }),
  });
}

export async function explainResults(
  stats: Record<string, unknown>,
  tradesSummary: Record<string, unknown> = {},
  strategyName: string = "",
  symbol: string = ""
): Promise<ExplainResponse> {
  return fetchJSON<ExplainResponse>(`${API_BASE}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      stats,
      trades_summary: tradesSummary,
      strategy_name: strategyName,
      symbol,
    }),
  });
}

export function createReplayWebSocket(): WebSocket {
  const wsUrl = API_BASE.replace("http", "ws") + "/replay";
  return new WebSocket(wsUrl);
}

export { API_BASE };
