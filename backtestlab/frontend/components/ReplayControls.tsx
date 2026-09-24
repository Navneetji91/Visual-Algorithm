"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import type { ReplayMessage, CandleData, MarkerData, EquityPoint } from "@/lib/types";
import { API_BASE } from "@/lib/api";

interface ReplayControlsProps {
  config: {
    symbol: string;
    timeframe: string;
    strategy: string;
    params: Record<string, number>;
    long_only: boolean;
    initial_capital: number;
    fee_bps: number;
    slippage_model: string;
    slippage_bps: number;
    impact_coeff: number;
    latency_ms: number;
  };
  onCandle?: (candle: CandleData) => void;
  onMarkers?: (markers: MarkerData[]) => void;
  onEquity?: (point: EquityPoint) => void;
  onIndicators?: (values: Record<string, number | null>) => void;
  onComplete?: () => void;
}

export default function ReplayControls({
  config,
  onCandle,
  onMarkers,
  onEquity,
  onIndicators,
  onComplete,
}: ReplayControlsProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const wsUrl = API_BASE.replace("http", "ws") + "/replay";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ ...config, speed }));
      setIsPlaying(true);
    };

    ws.onmessage = (event) => {
      const msg: ReplayMessage = JSON.parse(event.data);

      switch (msg.type) {
        case "init":
          setTotal(msg.total || 0);
          break;
        case "candle":
          setProgress(msg.index || 0);
          if (msg.candle) onCandle?.(msg.candle);
          if (msg.markers && msg.markers.length > 0) onMarkers?.(msg.markers);
          if (msg.equity) onEquity?.(msg.equity);
          if (msg.indicators) onIndicators?.(msg.indicators);
          break;
        case "done":
          setIsPlaying(false);
          onComplete?.();
          break;
        case "error":
          console.error("Replay error:", msg.message);
          setIsPlaying(false);
          break;
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setIsPlaying(false);
    };

    ws.onerror = () => {
      setConnected(false);
      setIsPlaying(false);
    };
  }, [config, speed, onCandle, onMarkers, onEquity, onIndicators, onComplete]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsPlaying(false);
    setConnected(false);
    setProgress(0);
  }, []);

  const sendAction = useCallback((action: string, value?: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, value }));
    }
  }, []);

  const togglePlay = () => {
    if (!connected) {
      connect();
    } else if (isPlaying) {
      sendAction("pause");
      setIsPlaying(false);
    } else {
      sendAction("resume");
      setIsPlaying(true);
    }
  };

  const changeSpeed = (newSpeed: number) => {
    setSpeed(newSpeed);
    sendAction("speed", newSpeed);
  };

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  const progressPct = total > 0 ? (progress / total) * 100 : 0;

  return (
    <div className="bg-[#0d1117] rounded-xl border border-gray-800 p-3">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-semibold text-gray-300 mr-2">Replay</h3>

        <button
          onClick={togglePlay}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            isPlaying
              ? "bg-amber-600/20 text-amber-400 border border-amber-800"
              : "bg-emerald-600/20 text-emerald-400 border border-emerald-800"
          }`}
        >
          {isPlaying ? "⏸ Pause" : connected ? "▶ Resume" : "▶ Play"}
        </button>

        {connected && (
          <button
            onClick={disconnect}
            className="px-2 py-1.5 rounded-lg text-xs text-red-400 border border-red-800 hover:bg-red-900/20"
          >
            ⏹ Stop
          </button>
        )}

        <div className="flex items-center gap-1">
          {[0.5, 1, 2, 5, 10].map((s) => (
            <button
              key={s}
              onClick={() => changeSpeed(s)}
              className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                speed === s
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-800 text-gray-500 hover:text-gray-300"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        {connected && (
          <div className="flex-1 flex items-center gap-2 ml-2">
            <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-200"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <span className="text-[10px] text-gray-500 tabular-nums">
              {progress}/{total}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
