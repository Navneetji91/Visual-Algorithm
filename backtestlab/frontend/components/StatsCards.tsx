"use client";

import type { Stats } from "@/lib/types";

interface StatsCardsProps {
  statsIdeal: Stats;
  statsRealistic: Stats;
  statsBuyhold: Stats;
}

interface StatCardData {
  label: string;
  idealVal: string;
  realisticVal: string;
  format: (v: number) => string;
  key: keyof Stats;
  goodDirection?: "up" | "down";
}

function fmt(v: number, pct: boolean = false, decimals: number = 2): string {
  if (pct) return (v * 100).toFixed(decimals) + "%";
  return v.toFixed(decimals);
}

function fmtDollar(v: number): string {
  return "$" + v.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

export default function StatsCards({ statsIdeal, statsRealistic, statsBuyhold }: StatsCardsProps) {
  const cards: {
    label: string;
    ideal: string;
    realistic: string;
    highlight?: boolean;
    negative?: boolean;
  }[] = [
    {
      label: "Total Return",
      ideal: fmt(statsIdeal.total_return, true, 1),
      realistic: fmt(statsRealistic.total_return, true, 1),
      highlight: true,
      negative: statsRealistic.total_return < 0,
    },
    {
      label: "Sharpe Ratio",
      ideal: fmt(statsIdeal.sharpe_ratio),
      realistic: fmt(statsRealistic.sharpe_ratio),
      negative: statsRealistic.sharpe_ratio < 0,
    },
    {
      label: "Sortino Ratio",
      ideal: fmt(statsIdeal.sortino_ratio),
      realistic: fmt(statsRealistic.sortino_ratio),
    },
    {
      label: "Max Drawdown",
      ideal: fmt(statsIdeal.max_drawdown, true, 1),
      realistic: fmt(statsRealistic.max_drawdown, true, 1),
      negative: true,
    },
    {
      label: "Win Rate",
      ideal: fmt(statsIdeal.win_rate, true, 0),
      realistic: fmt(statsRealistic.win_rate, true, 0),
    },
    {
      label: "Profit Factor",
      ideal: fmt(statsIdeal.profit_factor),
      realistic: fmt(statsRealistic.profit_factor),
      negative: statsRealistic.profit_factor < 1,
    },
    {
      label: "Trades",
      ideal: String(statsIdeal.num_trades),
      realistic: String(statsRealistic.num_trades),
    },
    {
      label: "Fees + Slippage",
      ideal: fmtDollar(statsIdeal.total_fees + statsIdeal.total_slippage),
      realistic: fmtDollar(statsRealistic.total_fees + statsRealistic.total_slippage),
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`terminal-card rounded-lg p-3 transition-transform duration-200 hover:-translate-y-0.5 ${
            card.highlight ? "ring-1 ring-[#c7a45d]/45" : ""
          }`}
        >
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">
            {card.label}
          </p>
          <div className="flex items-baseline gap-2">
            <span
            className={`text-lg font-bold tabular-nums ${
                card.negative ? "text-red-400" : "text-emerald-300"
              }`}
            >
              {card.realistic}
            </span>
          </div>
          <div className="flex items-center gap-1 mt-1">
            <span className="text-[9px] text-gray-600">Ideal:</span>
            <span className="text-[10px] text-gray-400 tabular-nums">{card.ideal}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
