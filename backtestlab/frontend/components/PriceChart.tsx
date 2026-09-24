"use client";

import { useEffect, useRef } from "react";
import type { CandleData, MarkerData } from "@/lib/types";

interface PriceChartProps {
  candles: CandleData[];
  indicators: Record<string, (number | null)[]>;
  markers: MarkerData[];
  strategyKey: string;
  onTimeRangeChange?: (from: number, to: number) => void;
}

export default function PriceChart({
  candles,
  indicators,
  markers,
  strategyKey,
}: PriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);

  useEffect(() => {
    if (!chartContainerRef.current || candles.length === 0) return;

    let isMounted = true;

    const initChart = async () => {
      const lwc = await import("lightweight-charts");

      if (!isMounted || !chartContainerRef.current) return;

      // Clear previous chart
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
          vertLine: { color: "#536174", width: 1, style: 2 },
          horzLine: { color: "#536174", width: 1, style: 2 },
        },
        timeScale: {
          borderColor: "#344357",
          timeVisible: true,
          secondsVisible: false,
        },
        rightPriceScale: {
          borderColor: "#344357",
        },
        width: chartContainerRef.current.clientWidth,
        height: 400,
      });

      chartRef.current = chart;

      // Candlestick series (pane 0)
      const candleSeries = chart.addSeries(lwc.CandlestickSeries, {
        upColor: "#4cb38b",
        downColor: "#d46a6a",
        borderUpColor: "#4cb38b",
        borderDownColor: "#d46a6a",
        wickUpColor: "#4cb38b",
        wickDownColor: "#d46a6a",
      });

      candleSeries.setData(candles as any);

      // Overlay indicators (SMA lines on pane 0)
      const overlayIndicators = ["SMA Fast", "SMA Slow"];
      const overlayColors: Record<string, string> = {
        "SMA Fast": "#c7a45d",
        "SMA Slow": "#75a7d9",
      };

      overlayIndicators.forEach((name) => {
        if (indicators[name]) {
          const lineSeries = chart.addSeries(lwc.LineSeries, {
            color: overlayColors[name] || "#888",
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          });

          const data = candles
            .map((c, i) => ({
              time: c.time,
              value: indicators[name][i],
            }))
            .filter((d) => d.value !== null && d.value !== undefined) as any[];

          lineSeries.setData(data);
        }
      });

      // Markers on the candle series
      if (markers.length > 0) {
        const formattedMarkers = markers.map((m) => ({
          time: m.time as any,
          position: m.position,
          color: m.color,
          shape: m.shape,
          text: m.text,
        }));
        lwc.createSeriesMarkers(candleSeries, formattedMarkers);
      }

      // Sub-pane indicators (RSI / MACD in pane 1)
      if (indicators["RSI"]) {
        const rsiSeries = chart.addSeries(lwc.LineSeries, {
            color: "#c7a45d",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: true,
        }, 1);

        const rsiData = candles
          .map((c, i) => ({
            time: c.time,
            value: indicators["RSI"][i],
          }))
          .filter((d) => d.value !== null && d.value !== undefined) as any[];

        rsiSeries.setData(rsiData);
      }

      if (indicators["MACD"]) {
        // MACD line
        const macdSeries = chart.addSeries(lwc.LineSeries, {
          color: "#75a7d9",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        }, 1);

        const macdData = candles
          .map((c, i) => ({
            time: c.time,
            value: indicators["MACD"][i],
          }))
          .filter((d) => d.value !== null && d.value !== undefined) as any[];

        macdSeries.setData(macdData);

        // Signal line
        if (indicators["Signal"]) {
          const signalSeries = chart.addSeries(lwc.LineSeries, {
            color: "#c7a45d",
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          }, 1);

          const signalData = candles
            .map((c, i) => ({
              time: c.time,
              value: indicators["Signal"][i],
            }))
            .filter((d) => d.value !== null && d.value !== undefined) as any[];

          signalSeries.setData(signalData);
        }

        // Histogram
        if (indicators["Histogram"]) {
          const histSeries = chart.addSeries(lwc.HistogramSeries, {
            priceLineVisible: false,
            lastValueVisible: false,
          }, 1);

          const histData = candles
            .map((c, i) => ({
              time: c.time,
              value: indicators["Histogram"][i],
              color:
                indicators["Histogram"][i] !== null &&
                (indicators["Histogram"][i] as number) >= 0
                  ? "#4cb38b80"
                  : "#d46a6a80",
            }))
            .filter((d) => d.value !== null && d.value !== undefined) as any[];

          histSeries.setData(histData);
        }
      }

      chart.timeScale().fitContent();

      // Resize observer
      const resizeObserver = new ResizeObserver((entries) => {
        if (entries[0] && chartRef.current) {
          const { width } = entries[0].contentRect;
          chartRef.current.applyOptions({ width });
        }
      });
      resizeObserver.observe(chartContainerRef.current);

      return () => {
        resizeObserver.disconnect();
      };
    };

    initChart();

    return () => {
      isMounted = false;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [candles, indicators, markers, strategyKey]);

  return (
    <div className="terminal-card rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#c7a45d]/15 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[#f3efe5]">Price Chart <span className="terminal-label ml-2 text-[9px]">Market tape</span></h3>
        <div className="flex gap-2 text-[10px] text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Buy
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            Sell
          </span>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
}
