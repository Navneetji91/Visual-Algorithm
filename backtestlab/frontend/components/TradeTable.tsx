"use client";

import { useState, useMemo } from "react";
import type { TradeData } from "@/lib/types";

interface TradeTableProps {
  trades: TradeData[];
  onTradeClick?: (trade: TradeData) => void;
}

type SortKey = keyof TradeData;
type SortDir = "asc" | "desc";

export default function TradeTable({ trades, onTradeClick }: TradeTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("entry_time");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sortedTrades = useMemo(() => {
    return [...trades].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const cmp = typeof aVal === "string" ? (aVal as string).localeCompare(bVal as string) : (aVal as number) - (bVal as number);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [trades, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const formatTime = (ts: number) => {
    return new Date(ts * 1000).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const columns: { key: SortKey; label: string; format: (v: any) => string }[] = [
    { key: "entry_time", label: "Entry", format: formatTime },
    { key: "side", label: "Side", format: (v) => v.toUpperCase() },
    { key: "entry_price", label: "Entry $", format: (v) => v.toFixed(2) },
    { key: "exit_price", label: "Exit $", format: (v) => v.toFixed(2) },
    { key: "net_pnl", label: "Net PnL", format: (v) => (v >= 0 ? "+" : "") + v.toFixed(2) },
    { key: "return_pct", label: "Return", format: (v) => (v * 100).toFixed(2) + "%" },
    { key: "fees", label: "Fees", format: (v) => v.toFixed(2) },
    { key: "bars_held", label: "Bars", format: (v) => String(v) },
  ];

  if (trades.length === 0) {
    return (
      <div className="terminal-card rounded-lg p-6 text-center text-gray-500 text-sm">
        No trades to display. Run a backtest to see results.
      </div>
    );
  }

  return (
    <div className="terminal-card rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#c7a45d]/15">
        <h3 className="text-sm font-semibold text-[#f3efe5]">
          Trade Log <span className="text-gray-500 font-normal">({trades.length} trades)</span>
        </h3>
      </div>
      <div className="overflow-x-auto max-h-64 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-[#172231]">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => toggleSort(col.key)}
                  className="px-3 py-2 text-left text-gray-500 font-medium cursor-pointer hover:text-gray-300 transition-colors whitespace-nowrap"
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span className="ml-1 text-[#e6ca8b]">
                      {sortDir === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedTrades.map((trade, i) => (
              <tr
                key={i}
                onClick={() => onTradeClick?.(trade)}
                className="border-t border-[#2c3949]/70 hover:bg-[#c7a45d]/8 cursor-pointer transition-colors"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`px-3 py-1.5 whitespace-nowrap tabular-nums ${
                      col.key === "net_pnl" || col.key === "return_pct"
                        ? (trade as any)[col.key] >= 0
                          ? "text-emerald-400"
                          : "text-red-400"
                        : col.key === "side"
                        ? trade.side === "long"
                          ? "text-emerald-400"
                          : "text-red-400"
                        : "text-gray-400"
                    }`}
                  >
                    {col.format((trade as any)[col.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
