"use client";

import { useEffect, useRef } from "react";
import type { EquityPoint } from "@/lib/types";

interface EquityChartProps {
  equityIdeal: EquityPoint[];
  equityRealistic: EquityPoint[];
  equityBuyhold: EquityPoint[];
  drawdown: EquityPoint[];
  idealReturn: number;
  realisticReturn: number;
}

export default function EquityChart({
  equityIdeal,
  equityRealistic,
  equityBuyhold,
  drawdown,
  idealReturn,
  realisticReturn,
}: EquityChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);

  const costImpact = ((idealReturn - realisticReturn) * 100).toFixed(1);

  useEffect(() => {
    if (!chartContainerRef.current || equityIdeal.length === 0) return;

    let isMounted = true;

    const initChart = async () => {
      const lwc = await import("lightweight-charts");

      if (!isMounted || !chartContainerRef.current) return;

      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }

      const chart = lwc.createChart(chartContainerRef.current, {
        layout: {
          background: { color: "#101925" },
          textColor: "#98a3b3",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "#1a2737" },
          horzLines: { color: "#1a2737" },
        },
        crosshair: {
          mode: 0,
        },
        timeScale: {
          borderColor: "#344357",
          timeVisible: true,
        },
        rightPriceScale: {
          borderColor: "#344357",
        },
        width: chartContainerRef.current.clientWidth,
        height: 280,
      });

      chartRef.current = chart;

      // Ideal equity line
      const idealSeries = chart.addSeries(lwc.LineSeries, {
        color: "#4cb38b",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        title: "Ideal",
      });
      idealSeries.setData(equityIdeal as any);

      // Realistic equity line
      const realisticSeries = chart.addSeries(lwc.LineSeries, {
        color: "#c7a45d",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        title: "Realistic",
      });
      realisticSeries.setData(equityRealistic as any);

      // Buy & Hold line
      const bh = chart.addSeries(lwc.LineSeries, {
        color: "#75a7d9",
        lineWidth: 1,
        lineStyle: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        title: "Buy & Hold",
      });
      bh.setData(equityBuyhold as any);

      // Drawdown area (pane 1)
      if (drawdown.length > 0) {
        const ddSeries = chart.addSeries(lwc.AreaSeries, {
          topColor: "rgba(239, 83, 80, 0.3)",
          bottomColor: "rgba(239, 83, 80, 0.0)",
          lineColor: "#d46a6a",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        }, 1);
        ddSeries.setData(drawdown as any);
      }

      chart.timeScale().fitContent();

      const resizeObserver = new ResizeObserver((entries) => {
        if (entries[0] && chartRef.current) {
          chartRef.current.applyOptions({ width: entries[0].contentRect.width });
        }
      });
      resizeObserver.observe(chartContainerRef.current);

      return () => resizeObserver.disconnect();
    };

    initChart();

    return () => {
      isMounted = false;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [equityIdeal, equityRealistic, equityBuyhold, drawdown]);

  return (
    <div className="terminal-card rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#c7a45d]/15 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[#f3efe5]">Equity Curve <span className="terminal-label ml-2 text-[9px]">Capital ledger</span></h3>
        <div className="flex items-center gap-3">
          <div className="flex gap-3 text-[10px]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-0.5 bg-green-500 inline-block" /> Ideal
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-0.5 bg-amber-500 inline-block" /> Realistic
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-0.5 bg-indigo-500 inline-block" style={{ borderBottom: '1px dashed' }} /> B&H
            </span>
          </div>
          {Number(costImpact) > 0 && (
            <div className="bg-red-900/40 border border-red-800/60 px-2 py-0.5 rounded-full">
              <span className="text-[10px] font-bold text-red-400">
                ⚠ Execution Cost: -{costImpact}% drag
              </span>
            </div>
          )}
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
}
