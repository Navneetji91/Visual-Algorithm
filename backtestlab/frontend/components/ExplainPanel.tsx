"use client";

import { useState } from "react";
import type { ExplainResponse } from "@/lib/types";
import { explainResults } from "@/lib/api";

interface ExplainPanelProps {
  stats: Record<string, any> | null;
  strategyName: string;
  symbol: string;
}

export default function ExplainPanel({ stats, strategyName, symbol }: ExplainPanelProps) {
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExplain = async () => {
    if (!stats) return;
    setLoading(true);
    setError(null);
    try {
      const result = await explainResults(stats, {}, strategyName, symbol);
      setExplanation(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!stats) {
    return null;
  }

  return (
    <div className="terminal-card rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#c7a45d]/15 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[#f3efe5]">Analysis <span className="terminal-label ml-2 text-[9px]">Desk note</span></h3>
        {explanation && (
          <span className="text-[10px] text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
            {explanation.source === "ai" ? "🤖 AI" : "📊 Rule-based"}
          </span>
        )}
      </div>

      <div className="p-4">
        {!explanation && !loading && (
          <button
            onClick={handleExplain}
            className="brass-button w-full px-4 py-3 rounded-md text-sm font-semibold transition-all"
          >
            🧠 Explain My Results
          </button>
        )}

        {loading && (
          <div className="flex items-center justify-center py-6 gap-2 text-gray-400">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Analyzing...
          </div>
        )}

        {error && (
          <div className="bg-red-900/30 border border-red-800 rounded-lg p-3 text-xs text-red-400">
            {error}
          </div>
        )}

        {explanation && (
            <div className="prose prose-invert prose-sm max-w-none text-xs text-gray-300 leading-relaxed whitespace-pre-wrap animate-fade-in">
            {explanation.analysis}
          </div>
        )}
      </div>
    </div>
  );
}
