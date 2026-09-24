"use client";

import { useEffect, useRef } from "react";
import type { MonteCarloResult } from "@/lib/types";

interface MonteCarloChartProps {
  data: MonteCarloResult | null;
  loading: boolean;
  onRun?: () => void;
}

export default function MonteCarloChart({ data, loading, onRun }: MonteCarloChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!data || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const pad = { top: 30, right: 60, bottom: 30, left: 20 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    // Find data bounds
    const allVals = [
      ...data.percentile_5,
      ...data.percentile_95,
    ];
    const minVal = Math.min(...allVals);
    const maxVal = Math.max(...allVals);
    const n = data.percentile_50.length;

    const xScale = (i: number) => pad.left + (i / (n - 1)) * plotW;
    const yScale = (v: number) => pad.top + plotH - ((v - minVal) / (maxVal - minVal)) * plotH;

    // Clear
      ctx.fillStyle = "#101925";
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = "#161b22";
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
      const y = pad.top + (plotH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();

      const val = maxVal - (i / 4) * (maxVal - minVal);
      ctx.fillStyle = "#8b949e";
      ctx.font = "9px monospace";
      ctx.textAlign = "left";
      ctx.fillText("$" + val.toFixed(0), w - pad.right + 4, y + 3);
    }

    // Fan bands
    const drawBand = (upper: number[], lower: number[], color: string) => {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(xScale(0), yScale(upper[0]));
      for (let i = 1; i < n; i++) ctx.lineTo(xScale(i), yScale(upper[i]));
      for (let i = n - 1; i >= 0; i--) ctx.lineTo(xScale(i), yScale(lower[i]));
      ctx.closePath();
      ctx.fill();
    };

    // 5-95 band (lightest)
    drawBand(data.percentile_95, data.percentile_5, "rgba(99, 102, 241, 0.08)");
    // 25-75 band
    drawBand(data.percentile_75, data.percentile_25, "rgba(99, 102, 241, 0.15)");

    // Median line
    ctx.strokeStyle = "#6366f1";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = xScale(i);
      const y = yScale(data.percentile_50[i]);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Initial capital line
    const ic = data.percentile_50[0];
    ctx.strokeStyle = "#ef535050";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pad.left, yScale(ic));
    ctx.lineTo(w - pad.right, yScale(ic));
    ctx.stroke();
    ctx.setLineDash([]);

    // Labels
    ctx.fillStyle = "#8b949e";
    ctx.font = "9px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Trade #", w / 2, h - 5);

  }, [data]);

  if (!data && !loading) {
    return (
      <div className="bg-[#0d1117] rounded-xl border border-gray-800 p-6 flex flex-col items-center gap-3">
        <p className="text-gray-500 text-sm">Run Monte Carlo simulation</p>
        <button
          onClick={onRun}
          className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg text-sm font-semibold text-white hover:from-indigo-500 hover:to-purple-500 transition-all"
        >
          🎲 Run Monte Carlo
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-[#0d1117] rounded-xl border border-gray-800 p-6 flex items-center justify-center">
        <div className="flex items-center gap-2 text-gray-400">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Running 1,000 simulations...
        </div>
      </div>
    );
  }

  return (
    <div className="terminal-card rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#c7a45d]/15 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[#f3efe5]">Monte Carlo Simulation</h3>
        <div className="flex gap-3 text-[10px] text-gray-400">
          <span>P(Loss): <strong className={data!.probability_of_loss > 0.5 ? "text-red-400" : "text-emerald-400"}>
            {(data!.probability_of_loss * 100).toFixed(0)}%
          </strong></span>
          <span>Median: <strong className="text-indigo-400">
            ${data!.median_final_equity.toFixed(0)}
          </strong></span>
        </div>
      </div>
      <canvas ref={canvasRef} className="w-full" style={{ height: 220 }} />
      <div className="px-4 py-2 flex gap-4 text-[10px] text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded" style={{ backgroundColor: "rgba(99, 102, 241, 0.3)" }} />
          5th-95th percentile
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-indigo-500 inline-block" />
          Median
        </span>
      </div>
    </div>
  );
}
