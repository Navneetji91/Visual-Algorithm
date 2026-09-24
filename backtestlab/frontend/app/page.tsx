"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import ControlPanel from "@/components/ControlPanel";
import PriceChart from "@/components/PriceChart";
import EquityChart from "@/components/EquityChart";
import StatsCards from "@/components/StatsCards";
import TradeTable from "@/components/TradeTable";
import Heatmap from "@/components/Heatmap";
import MonteCarloChart from "@/components/MonteCarloChart";
import ReplayControls from "@/components/ReplayControls";
import ExplainPanel from "@/components/ExplainPanel";
import type {
  BacktestRequest,
  BacktestResponse,
  OptimizeResult,
  MonteCarloResult,
} from "@/lib/types";
import { runBacktest, runOptimize, runMonteCarlo } from "@/lib/api";

type TabKey = "results" | "heatmap" | "montecarlo" | "replay";

export default function HomePage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [lastRequest, setLastRequest] = useState<BacktestRequest | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("results");

  // Optimization state
  const [optimizeResult, setOptimizeResult] = useState<OptimizeResult | null>(null);
  const [optimizeLoading, setOptimizeLoading] = useState(false);

  // Monte Carlo state
  const [mcResult, setMcResult] = useState<MonteCarloResult | null>(null);
  const [mcLoading, setMcLoading] = useState(false);

  // Slippage sensitivity debounce
  const slippageTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleRunBacktest = useCallback(async (req: BacktestRequest) => {
    setLoading(true);
    setError(null);
    setLastRequest(req);
    try {
      const data = await runBacktest(req);
      setResult(data);
      setActiveTab("results");
      // Reset secondary results when running new backtest
      setOptimizeResult(null);
      setMcResult(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSlippageChange = useCallback(
    (bps: number) => {
      if (!lastRequest || loading) return;
      if (slippageTimerRef.current) clearTimeout(slippageTimerRef.current);
      slippageTimerRef.current = setTimeout(() => {
        handleRunBacktest({ ...lastRequest, slippage_bps: bps });
      }, 500);
    },
    [lastRequest, loading, handleRunBacktest]
  );

  const handleRunOptimize = useCallback(async () => {
    if (!lastRequest) return;
    setOptimizeLoading(true);
    try {
      const data = await runOptimize({
        symbol: lastRequest.symbol,
        timeframe: lastRequest.timeframe,
        start: lastRequest.start,
        end: lastRequest.end,
        strategy: lastRequest.strategy,
        long_only: lastRequest.long_only,
        initial_capital: lastRequest.initial_capital,
        fee_bps: lastRequest.fee_bps,
        slippage_model: lastRequest.slippage_model,
        slippage_bps: lastRequest.slippage_bps,
        impact_coeff: lastRequest.impact_coeff,
        latency_ms: lastRequest.latency_ms,
        param_ranges: {},
        train_pct: 0.7,
      });
      setOptimizeResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setOptimizeLoading(false);
    }
  }, [lastRequest]);

  const handleRunMonteCarlo = useCallback(async () => {
    if (!result) return;
    setMcLoading(true);
    try {
      const tradeReturns = result.trades.map((t) => t.return_pct);
      const data = await runMonteCarlo(
        tradeReturns,
        lastRequest?.initial_capital || 10000
      );
      setMcResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setMcLoading(false);
    }
  }, [result, lastRequest]);

  const handleHeatmapCellClick = useCallback(
    (params: Record<string, number>) => {
      if (!lastRequest) return;
      handleRunBacktest({ ...lastRequest, params: { ...lastRequest.params, ...params } });
    },
    [lastRequest, handleRunBacktest]
  );

  // Auto-run default backtest on mount
  useEffect(() => {
    handleRunBacktest({
      symbol: "DEMO-BTC",
      timeframe: "1h",
      strategy: "sma_crossover",
      params: { fast: 10, slow: 30 },
      long_only: false,
      initial_capital: 10000,
      fee_bps: 5,
      slippage_model: "fixed",
      slippage_bps: 2,
      impact_coeff: 0.1,
      latency_ms: 50,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tabs: { key: TabKey; label: string; icon: string }[] = [
    { key: "results", label: "Results", icon: "01" },
    { key: "heatmap", label: "Heatmap", icon: "02" },
    { key: "montecarlo", label: "Monte Carlo", icon: "03" },
    { key: "replay", label: "Replay", icon: "04" },
  ];

  return (
    <div className="app-shell flex h-screen text-gray-200 overflow-hidden">
      <div className="ambient-grid" aria-hidden="true" />
      <div className="ambient-glow" aria-hidden="true" />
      <div className="ambient-glow-secondary" aria-hidden="true" />
      {/* Left Panel */}
      <ControlPanel
        onRunBacktest={handleRunBacktest}
        loading={loading}
        onSlippageChange={handleSlippageChange}
      />

      {/* Main Content */}
      <div className="relative flex-1 flex flex-col overflow-hidden">
        <header className="mx-4 mt-3 rounded-lg terminal-card px-4 py-2.5 flex items-center gap-4 shrink-0">
          <div>
            <p className="terminal-label text-[9px]">Desk / Strategy Monitor</p>
            <h2 className="text-sm font-semibold text-[#f3efe5]">Execution-aware market research</h2>
          </div>
          <div className="ml-auto flex items-center gap-3 text-[10px]">
            <span className="hidden sm:flex items-center gap-1.5 text-[#9eacbc]">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              API connected
            </span>
            <span className="rounded border border-[#c7a45d]/30 bg-[#c7a45d]/10 px-2 py-1 font-mono text-[#e6ca8b]">
              SIMULATION
            </span>
          </div>
        </header>
        {/* Error Toast */}
        {error && (
          <div className="mx-4 mt-2 bg-red-900/40 border border-red-800 rounded-lg p-3 text-sm text-red-400 flex items-center justify-between">
            <span>❌ {error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-300">✕</button>
          </div>
        )}

        {/* Tab Bar */}
        <div className="flex items-center gap-1 px-4 pt-3 pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all border ${
                activeTab === tab.key
                  ? "bg-[#c7a45d]/15 text-[#e6ca8b] border-[#c7a45d]/35 shadow-sm"
                  : "text-gray-500 border-transparent hover:text-gray-200 hover:bg-[#172231]/80"
              }`}
            >
              <span className="mr-1.5 font-mono text-[9px] opacity-70">{tab.icon}</span>{tab.label}
            </button>
          ))}

          {/* Pitch badge */}
          <div className="ml-auto hidden lg:block text-[10px] text-gray-500 italic max-w-md text-right">
            &ldquo;Most retail backtests lie because they ignore execution costs. This one doesn&rsquo;t.&rdquo;
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-3">
          {activeTab === "results" && (
            <>
              {/* Loading skeleton */}
              {loading && !result && (
                <div className="space-y-3">
                  <div className="h-[400px] bg-gray-800/30 rounded-xl animate-pulse" />
                  <div className="grid grid-cols-4 gap-2">
                    {[...Array(8)].map((_, i) => (
                      <div key={i} className="h-20 bg-gray-800/30 rounded-xl animate-pulse" />
                    ))}
                  </div>
                </div>
              )}

              {result && (
                <>
                  <PriceChart
                    candles={result.candles}
                    indicators={result.indicators}
                    markers={result.markers}
                    strategyKey={lastRequest?.strategy || ""}
                  />

                  <StatsCards
                    statsIdeal={result.stats_ideal}
                    statsRealistic={result.stats_realistic}
                    statsBuyhold={result.stats_buyhold}
                  />

                  <EquityChart
                    equityIdeal={result.equity_ideal}
                    equityRealistic={result.equity_realistic}
                    equityBuyhold={result.equity_buyhold}
                    drawdown={result.drawdown}
                    idealReturn={result.stats_ideal.total_return}
                    realisticReturn={result.stats_realistic.total_return}
                  />

                  <div className="grid grid-cols-2 gap-3">
                    <TradeTable trades={result.trades} />
                    <ExplainPanel
                      stats={result.stats_realistic as any}
                      strategyName={lastRequest?.strategy || ""}
                      symbol={lastRequest?.symbol || ""}
                    />
                  </div>
                </>
              )}

              {!result && !loading && (
                <div className="flex items-center justify-center h-96 text-gray-600">
                  <div className="text-center">
                    <p className="text-4xl mb-2">📈</p>
                    <p>Configure and run a backtest to see results</p>
                  </div>
                </div>
              )}
            </>
          )}

          {activeTab === "heatmap" && (
            <Heatmap
              data={optimizeResult}
              loading={optimizeLoading}
              onCellClick={handleHeatmapCellClick}
              onRunOptimize={handleRunOptimize}
            />
          )}

          {activeTab === "montecarlo" && (
            <MonteCarloChart
              data={mcResult}
              loading={mcLoading}
              onRun={handleRunMonteCarlo}
            />
          )}

          {activeTab === "replay" && lastRequest && (
            <ReplayControls config={lastRequest} />
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-[#2c3949] text-center text-[9px] text-gray-500 bg-[#101925]/90">
          Educational tool, not financial advice. Past performance does not predict future results. • BacktestLab v1.0
        </div>
      </div>
    </div>
  );
}
