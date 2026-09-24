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

/**
 * Requests use Next's same-origin proxy unless an external public API URL is
 * explicitly configured. This keeps the browser out of the CORS path for
 * local development and deployed frontends alike.
 */
const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
const API_BASE = (configuredApiUrl || "/api").replace(/\/+$/, "");

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(url, options);
  } catch {
    throw new Error(
      "Cannot reach the BacktestLab API. Start the backend or check its URL configuration."
    );
  }

  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    const detail = typeof payload?.detail === "string" ? payload.detail : response.statusText;
    throw new Error(detail || `API error: ${response.status}`);
  }

  try {
    return await response.json();
  } catch {
    throw new Error("The BacktestLab API returned an invalid response.");
  }
}

export async function getSymbols(): Promise<string[]> {
  const data = await fetchJSON<{ symbols: string[] }>(apiUrl("/symbols"));
  return data.symbols;
}

export async function getStrategies(): Promise<StrategyInfo[]> {
  const data = await fetchJSON<{ strategies: StrategyInfo[] }>(apiUrl("/strategies"));
  return data.strategies;
}

export async function runBacktest(req: BacktestRequest): Promise<BacktestResponse> {
  return fetchJSON<BacktestResponse>(apiUrl("/backtest"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function runOptimize(req: OptimizeRequest): Promise<OptimizeResult> {
  return fetchJSON<OptimizeResult>(apiUrl("/optimize"), {
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
  return fetchJSON<MonteCarloResult>(apiUrl("/montecarlo"), {
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
  return fetchJSON<ExplainResponse>(apiUrl("/explain"), {
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
  const base = API_BASE.startsWith("http")
    ? API_BASE
    : `${window.location.protocol}//${window.location.host}${API_BASE}`;
  const wsUrl = base.replace(/^http/, "ws") + "/replay";
  return new WebSocket(wsUrl);
}

export { API_BASE };
