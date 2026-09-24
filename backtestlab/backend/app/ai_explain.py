"""
AI / Rule-based trade explanation engine.

Uses Anthropic API if ANTHROPIC_API_KEY is set, otherwise falls back
to a deterministic rule-based explainer.
"""

import os
from typing import Any


def explain_results(
    stats: dict[str, Any],
    trades_summary: dict[str, Any] = None,
    strategy_name: str = "",
    symbol: str = "",
) -> dict[str, str]:
    """
    Generate a plain-English analysis of backtest results.

    Args:
        stats: Backtest statistics dict
        trades_summary: Summary of trades (optional)
        strategy_name: Name of strategy used
        symbol: Symbol backtested

    Returns:
        {"analysis": str, "source": "ai" | "rule_based"}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model_name = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    if api_key:
        try:
            return _ai_explain(stats, trades_summary, strategy_name, symbol, api_key, model_name)
        except Exception as e:
            # Fall back to rule-based if AI fails
            analysis = _rule_based_explain(stats, trades_summary, strategy_name, symbol)
            analysis += f"\n\n_(AI explanation unavailable: {str(e)})_"
            return {"analysis": analysis, "source": "rule_based"}
    else:
        return {
            "analysis": _rule_based_explain(stats, trades_summary, strategy_name, symbol),
            "source": "rule_based",
        }


def _ai_explain(
    stats: dict, trades_summary: dict, strategy_name: str, symbol: str,
    api_key: str, model_name: str
) -> dict[str, str]:
    """Use Anthropic API for explanation."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Analyze these backtest results for the {strategy_name} strategy on {symbol}:

Statistics:
{_format_stats(stats)}

{f'Trade Summary: {trades_summary}' if trades_summary else ''}

Provide a concise analysis covering:
1. Overall performance assessment
2. Risk-adjusted returns quality
3. Execution cost impact (fees + slippage)
4. Key strengths and weaknesses
5. Actionable suggestions for improvement

Keep it under 300 words, use bullet points, and be direct."""

    response = client.messages.create(
        model=model_name,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "analysis": response.content[0].text,
        "source": "ai",
    }


def _rule_based_explain(
    stats: dict, trades_summary: dict = None, strategy_name: str = "",
    symbol: str = ""
) -> str:
    """Deterministic rule-based analysis."""
    lines = []
    lines.append(f"## Analysis: {strategy_name} on {symbol}\n")

    # Performance
    total_ret = stats.get("total_return", 0) * 100
    sharpe = stats.get("sharpe_ratio", 0)
    max_dd = stats.get("max_drawdown", 0) * 100
    win_rate = stats.get("win_rate", 0) * 100
    pf = stats.get("profit_factor", 0)
    n_trades = stats.get("num_trades", 0)
    fees = stats.get("total_fees", 0)
    slippage = stats.get("total_slippage", 0)

    # Overall assessment
    if total_ret > 20:
        lines.append(f"✅ **Strong performance**: {total_ret:.1f}% total return.")
    elif total_ret > 0:
        lines.append(f"⚠️ **Modest performance**: {total_ret:.1f}% total return.")
    else:
        lines.append(f"❌ **Negative performance**: {total_ret:.1f}% total return. The strategy lost money.")

    # Sharpe
    if sharpe > 2:
        lines.append(f"✅ **Excellent risk-adjusted returns**: Sharpe ratio of {sharpe:.2f}.")
    elif sharpe > 1:
        lines.append(f"✅ **Good risk-adjusted returns**: Sharpe ratio of {sharpe:.2f}.")
    elif sharpe > 0:
        lines.append(f"⚠️ **Below-average risk-adjusted returns**: Sharpe ratio of {sharpe:.2f}.")
    else:
        lines.append(f"❌ **Poor risk-adjusted returns**: Sharpe ratio of {sharpe:.2f}.")

    # Drawdown
    if abs(max_dd) > 30:
        lines.append(f"🔴 **Large drawdown**: {max_dd:.1f}%. This strategy experienced significant losses before recovering.")
    elif abs(max_dd) > 15:
        lines.append(f"🟡 **Moderate drawdown**: {max_dd:.1f}%.")
    else:
        lines.append(f"🟢 **Controlled drawdown**: {max_dd:.1f}%.")

    # Win rate
    if win_rate > 60:
        lines.append(f"✅ **High win rate**: {win_rate:.0f}% of trades were profitable.")
    elif win_rate > 40:
        lines.append(f"⚠️ **Average win rate**: {win_rate:.0f}%.")
    elif n_trades > 0:
        lines.append(f"❌ **Low win rate**: {win_rate:.0f}%. Consider reviewing entry criteria.")

    # Execution costs
    total_costs = fees + slippage
    if total_costs > 0 and n_trades > 0:
        cost_per_trade = total_costs / n_trades
        lines.append(f"\n💰 **Execution costs**: ${total_costs:.2f} total (${cost_per_trade:.2f}/trade).")
        if fees > 0:
            lines.append(f"  - Fees: ${fees:.2f}")
        if slippage > 0:
            lines.append(f"  - Slippage: ${slippage:.2f}")

    # Over-trading detection
    if n_trades > 100:
        lines.append(f"\n⚠️ **Potential over-trading**: {n_trades} trades. High frequency increases cost drag.")

    # Profit factor
    if pf > 0:
        if pf > 2:
            lines.append(f"✅ **Strong profit factor**: {pf:.2f}x (wins are {pf:.1f}x larger than losses).")
        elif pf > 1:
            lines.append(f"⚠️ **Marginal profit factor**: {pf:.2f}x.")
        else:
            lines.append(f"❌ **Profit factor below 1**: {pf:.2f}x. Losses outweigh wins.")

    lines.append("\n---")
    lines.append("*This is a rule-based analysis. Set ANTHROPIC_API_KEY for AI-powered insights.*")

    return "\n".join(lines)


def _format_stats(stats: dict) -> str:
    """Format stats dict for AI prompt."""
    lines = []
    for k, v in stats.items():
        if isinstance(v, float):
            lines.append(f"  {k}: {v:.4f}")
        else:
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)
