"use client";

import { useState, useEffect, useCallback } from "react";
import type { StrategyInfo, BacktestRequest, StrategyParam } from "@/lib/types";
import { getSymbols, getStrategies } from "@/lib/api";

interface ControlPanelProps {
  onRunBacktest: (req: BacktestRequest) => void;
  loading: boolean;
  onSlippageChange?: (bps: number) => void;
}

const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

export default function ControlPanel({ onRunBacktest, loading, onSlippageChange }: ControlPanelProps) {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [symbol, setSymbol] = useState("DEMO-BTC");
  const [timeframe, setTimeframe] = useState("1h");
  const [strategyKey, setStrategyKey] = useState("sma_crossover");
  const [params, setParams] = useState<Record<string, number>>({});
  const [longOnly, setLongOnly] = useState(false);
  const [initialCapital, setInitialCapital] = useState(10000);
  const [feeBps, setFeeBps] = useState(5);
  const [slippageModel, setSlippageModel] = useState("fixed");
  const [slippageBps, setSlippageBps] = useState(2);
  const [impactCoeff, setImpactCoeff] = useState(0.1);
  const [latencyMs, setLatencyMs] = useState(50);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getSymbols(), getStrategies()])
      .then(([syms, strats]) => {
        setSymbols(syms);
        setStrategies(strats);
        // Set default params from the first strategy
        if (strats.length > 0) {
          const defaults: Record<string, number> = {};
          strats[0].params.forEach((p) => { defaults[p.name] = p.default; });
          setParams(defaults);
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  const currentStrategy = strategies.find((s) => s.key === strategyKey);

  const handleStrategyChange = useCallback(
    (key: string) => {
      setStrategyKey(key);
      const strat = strategies.find((s) => s.key === key);
      if (strat) {
        const defaults: Record<string, number> = {};
        strat.params.forEach((p) => { defaults[p.name] = p.default; });
        setParams(defaults);
      }
    },
    [strategies]
  );

  const handleSubmit = () => {
    onRunBacktest({
      symbol,
      timeframe,
      strategy: strategyKey,
      params,
      long_only: longOnly,
      initial_capital: initialCapital,
      fee_bps: feeBps,
      slippage_model: slippageModel,
      slippage_bps: slippageBps,
      impact_coeff: impactCoeff,
      latency_ms: latencyMs,
    });
  };

  return (
    <aside className="relative z-10 w-80 shrink-0 bg-[#101925]/95 border-r border-[#c7a45d]/20 overflow-y-auto p-4 flex flex-col gap-5 shadow-2xl shadow-black/20">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-md brass-button flex items-center justify-center">
          <span className="text-sm font-bold">BL</span>
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-[#f3efe5]">
            BacktestLab
          </h1>
          <p className="text-[9px] terminal-label text-[#c7a45d] -mt-0.5">Execution Desk</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-2 text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Market Section */}
      <Section title="Market">
        <Label text="Symbol">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="select-input"
          >
            {symbols.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </Label>

        <Label text="Timeframe">
          <div className="flex gap-1 flex-wrap">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-1 rounded text-xs font-mono transition-all ${
                  timeframe === tf
                    ? "bg-[#c7a45d] text-[#16130d] shadow-sm"
                    : "bg-[#172231] text-gray-400 hover:bg-[#263448] hover:text-gray-200"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </Label>
      </Section>

      {/* Strategy Section */}
      <Section title="Strategy">
        <Label text="Algorithm">
          <select
            value={strategyKey}
            onChange={(e) => handleStrategyChange(e.target.value)}
            className="select-input"
          >
            {strategies.map((s) => (
              <option key={s.key} value={s.key}>{s.name}</option>
            ))}
          </select>
        </Label>

        {currentStrategy?.description && (
          <p className="text-[10px] text-gray-500 -mt-1">{currentStrategy.description}</p>
        )}

        {currentStrategy?.params.map((p) => (
          <ParamSlider
            key={p.name}
            param={p}
            value={params[p.name] ?? p.default}
            onChange={(v) => setParams((prev) => ({ ...prev, [p.name]: v }))}
          />
        ))}

        <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={longOnly}
            onChange={(e) => setLongOnly(e.target.checked)}
            className="accent-[#c7a45d]"
          />
          Long only (no shorts)
        </label>
      </Section>

      {/* Execution Section */}
      <Section title="Execution Model">
        <Label text="Latency (ms)">
          <input
            type="number"
            value={latencyMs}
            onChange={(e) => setLatencyMs(Number(e.target.value))}
            className="number-input"
            min={0}
            max={5000}
          />
        </Label>

        <Label text="Slippage Model">
          <select
            value={slippageModel}
            onChange={(e) => setSlippageModel(e.target.value)}
            className="select-input"
          >
            <option value="fixed">Fixed BPS</option>
            <option value="volume_impact">Volume Impact</option>
          </select>
        </Label>

        <Label text={`Slippage (${slippageBps} bps)`}>
          <input
            type="range"
            min={0}
            max={20}
            step={0.5}
            value={slippageBps}
            onChange={(e) => {
              const v = Number(e.target.value);
              setSlippageBps(v);
              onSlippageChange?.(v);
            }}
            className="w-full accent-[#c7a45d]"
          />
          <div className="flex justify-between text-[10px] text-gray-600">
            <span>0</span>
            <span>10</span>
            <span>20</span>
          </div>
        </Label>

        {slippageModel === "volume_impact" && (
          <Label text="Impact Coefficient">
            <input
              type="number"
              value={impactCoeff}
              onChange={(e) => setImpactCoeff(Number(e.target.value))}
              className="number-input"
              step={0.01}
              min={0}
            />
          </Label>
        )}

        <Label text="Fee (bps/side)">
          <input
            type="number"
            value={feeBps}
            onChange={(e) => setFeeBps(Number(e.target.value))}
            className="number-input"
            min={0}
            max={100}
          />
        </Label>

        <Label text="Initial Capital ($)">
          <input
            type="number"
            value={initialCapital}
            onChange={(e) => setInitialCapital(Number(e.target.value))}
            className="number-input"
            min={100}
          />
        </Label>
      </Section>

      {/* Run Button */}
      <button
        onClick={handleSubmit}
        disabled={loading}
        className={`w-full py-3 rounded-md font-semibold text-sm transition-all ${
          loading
            ? "bg-gray-700 text-gray-400 cursor-not-allowed"
            : "brass-button"
        }`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Running Backtest...
          </span>
        ) : (
          "▶ Run Backtest"
        )}
      </button>

      {/* Disclaimer */}
      <p className="text-[9px] text-gray-600 text-center mt-auto pt-4">
        Educational tool. Not financial advice.<br />
        Past performance does not predict future results.
      </p>
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="terminal-label text-[10px] border-b border-[#c7a45d]/15 pb-1.5">{title}</h3>
      {children}
    </div>
  );
}

function Label({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs text-gray-500">{text}</span>
      {children}
    </label>
  );
}

function ParamSlider({
  param,
  value,
  onChange,
}: {
  param: StrategyParam;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <Label text={`${param.description} (${value})`}>
      <input
        type="range"
        min={param.min}
        max={param.max}
        step={param.step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#c7a45d]"
      />
      <div className="flex justify-between text-[10px] text-gray-600">
        <span>{param.min}</span>
        <span>{param.max}</span>
      </div>
    </Label>
  );
}
