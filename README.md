# BacktestLab

BacktestLab is a visual algorithmic-trading backtester built around one principle: a strategy signal is not a fill. It compares an ideal bar-close simulation against tick-level, latency-aware execution with slippage and fees.

> Educational tool, not financial advice. Past performance does not predict future results.

## Architecture

```text
Next.js + Lightweight Charts
          | REST / WebSocket replay
          v
       FastAPI API
          |
          +-- strategies + indicators (Pandas)
          +-- execution engine (ticks, latency, slippage, fees)
          +-- metrics / optimize / Monte Carlo / explainer
          |
          v
  seeded synthetic ticks -> Parquet candle cache
```

## Run locally

Requirements: Python 3.11+ and Node.js 20+.

```powershell
cd backtestlab/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In a second terminal:

```powershell
cd backtestlab/frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The API runs at `http://localhost:8000` and generates deterministic `DEMO-BTC` / `DEMO-ETH` ticks on first use. Copy `.env.example` to `.env.local` in the frontend to override `NEXT_PUBLIC_API_URL`.

## Verification

```powershell
cd backtestlab/backend
python -m pytest -q

cd ../frontend
npm run lint
npm run build
```

## Execution model

Signals use only completed candles and are shifted one bar before they can change a position. For every transition, the realistic engine finds the first tick at or after `signal time + latency` using `numpy.searchsorted`, then applies fixed-bps or size/volume market-impact slippage and per-side fees. The trade ledger stores the selected tick timestamp, so latency is visible in the result rather than merely reflected in price. Open positions are marked to market on candle closes; the last open position is liquidated at the final close.

## Three-minute demo

1. Run the default SMA strategy on `DEMO-BTC` and compare ideal vs realistic equity.
2. Increase the slippage slider and observe the execution-cost gap grow.
3. Open the heatmap, select a high train-Sharpe cell, and compare its test score / overfit warning.
4. Use Monte Carlo to inspect outcome bands, then start Replay to stream the same backtest candle by candle.

## Deployment

Deploy `backtestlab/frontend` to Vercel and set `NEXT_PUBLIC_API_URL` to the public backend URL. Deploy `backtestlab/backend` to Render or Railway with the start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Optional AI explanations use `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`; without them, the deterministic rule-based explainer is used.

## Limitations

Synthetic data is illustrative, not market data. The simulator models simple market orders and does not represent an order book, partial fills, funding, liquidation, exchange outages, or tax effects. Results should be validated on appropriate real data before any trading decision.
