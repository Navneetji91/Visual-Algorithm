"use client";

import { useState } from "react";
import type { OptimizeResult } from "@/lib/types";

interface HeatmapProps {
  data: OptimizeResult | null;
  loading: boolean;
  onCellClick?: (params: Record<string, number>) => void;
  onRunOptimize?: () => void;
}

export default function Heatmap({ data, loading, onCellClick, onRunOptimize }: HeatmapProps) {
  const [showTest, setShowTest] = useState(false);

  if (!data && !loading) {
    return (
      <div className="terminal-card rounded-lg p-6 flex flex-col items-center gap-3">
        <p className="text-gray-500 text-sm">Run parameter optimization to see the heatmap</p>
        <button
          onClick={onRunOptimize}
          className="brass-button px-4 py-2 rounded-md text-sm font-semibold transition-all"
        >
          🔍 Run Optimization
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="terminal-card rounded-lg p-6 flex items-center justify-center">
        <div className="flex items-center gap-2 text-gray-400">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Running grid search...
        </div>
      </div>
    );
  }

  if (!data) return null;

  const matrix = showTest ? data.test_sharpe_matrix : data.train_sharpe_matrix;
  const { param1_name, param2_name, param1_values, param2_values } = data;

  // Find min/max for color scaling
  const allVals = matrix.flat();
  const minVal = Math.min(...allVals);
  const maxVal = Math.max(...allVals);

  const getColor = (val: number): string => {
    if (maxVal === minVal) return "hsl(210, 30%, 20%)";
    const t = (val - minVal) / (maxVal - minVal);
    if (val < 0) {
      // Red scale
      const intensity = Math.abs(val / (Math.abs(minVal) || 1));
      return `hsl(0, ${60 + intensity * 40}%, ${20 + (1 - intensity) * 15}%)`;
    }
    // Green scale
    return `hsl(${120 + t * 30}, ${40 + t * 30}%, ${15 + t * 25}%)`;
  };

  return (
    <div className="terminal-card rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#c7a45d]/15 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[#f3efe5]">
          Parameter Heatmap
          <span className="text-gray-500 font-normal ml-2">
            ({param1_name} × {param2_name})
          </span>
        </h3>
        <div className="flex items-center gap-2">
          {data.overfit_warning && (
            <span className="bg-amber-900/40 border border-amber-800/60 px-2 py-0.5 rounded-full text-[10px] font-bold text-amber-400">
              ⚠ Overfit Risk
            </span>
          )}
          <div className="flex rounded-lg overflow-hidden border border-gray-700">
            <button
              onClick={() => setShowTest(false)}
              className={`px-2 py-1 text-[10px] ${!showTest ? "bg-[#c7a45d] text-[#16130d]" : "bg-[#172231] text-gray-400"}`}
            >
              Train
            </button>
            <button
              onClick={() => setShowTest(true)}
              className={`px-2 py-1 text-[10px] ${showTest ? "bg-[#c7a45d] text-[#16130d]" : "bg-[#172231] text-gray-400"}`}
            >
              Test
            </button>
          </div>
        </div>
      </div>

      {data.overfit_warning && (
        <div className="mx-4 mt-2 bg-amber-900/20 border border-amber-800/40 rounded-lg p-2 text-[10px] text-amber-400">
          {data.overfit_message}
        </div>
      )}

      <div className="p-4 overflow-x-auto">
        <div className="flex items-end gap-1 mb-1">
          <div className="w-12" />
          {param2_values.map((v, j) => (
            <div key={j} className="w-10 text-[9px] text-gray-500 text-center">
              {typeof v === "number" ? v.toFixed(v % 1 ? 1 : 0) : v}
            </div>
          ))}
        </div>
        <div className="text-[9px] text-gray-500 text-center mb-2">{param2_name} →</div>

        {param1_values.map((v1, i) => (
          <div key={i} className="flex items-center gap-1 mb-1">
            <div className="w-12 text-[9px] text-gray-500 text-right pr-1">
              {typeof v1 === "number" ? v1.toFixed(v1 % 1 ? 1 : 0) : v1}
            </div>
            {param2_values.map((v2, j) => {
              const val = matrix[i]?.[j] ?? 0;
              const isBest = data.best_params[param1_name] === v1 && data.best_params[param2_name] === v2;
              return (
                <div
                  key={j}
                  onClick={() => onCellClick?.({ [param1_name]: v1 as number, [param2_name]: v2 as number })}
                  className={`w-10 h-8 rounded cursor-pointer flex items-center justify-center text-[9px] font-mono transition-all hover:ring-1 hover:ring-white/30 ${
                    isBest ? "ring-2 ring-emerald-400" : ""
                  }`}
                  style={{ backgroundColor: getColor(val) }}
                  title={`${param1_name}=${v1}, ${param2_name}=${v2}, Sharpe=${val.toFixed(2)}`}
                >
                  <span className={val >= 0 ? "text-gray-200" : "text-gray-400"}>
                    {val.toFixed(1)}
                  </span>
                </div>
              );
            })}
          </div>
        ))}
        <div className="text-[9px] text-gray-500 ml-12 mt-1">{param1_name} ↓</div>

        <div className="mt-3 flex items-center gap-4 text-[10px] text-gray-400">
          <span>Best train: <strong className="text-emerald-400">{data.best_train_sharpe.toFixed(2)}</strong></span>
          <span>Best test: <strong className={data.best_test_sharpe >= 0 ? "text-emerald-400" : "text-red-400"}>{data.best_test_sharpe.toFixed(2)}</strong></span>
          <span>Best: {JSON.stringify(data.best_params)}</span>
        </div>
      </div>
    </div>
  );
}
