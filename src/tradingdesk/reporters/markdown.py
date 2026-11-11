"""Markdown report generator matching original Trading Desk report structure."""

from pathlib import Path
from tradingdesk.models.report import DeskReport
from tradingdesk.config import config


def generate_markdown_report(report: DeskReport) -> str:
    """Render a DeskReport into Markdown text."""
    r = report
    q = r.market_quote
    m = r.research
    quant = r.quant
    em = quant.expected_move
    g = quant.greeks
    risk = r.risk

    lines = [
        f"# {r.symbol} Analysis Report - {r.date_str}",
        "",
        "## Market Research",
        f"**Current Sentiment:** {m.sentiment}",
        "",
        m.summary,
        "",
    ]

    if m.key_headlines:
        lines.append("**Key Headlines:**")
        for h in m.key_headlines:
            lines.append(f"- {h}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Financial Analysis",
        "**Live Market Data:**",
        f"- **Symbol:** {q.symbol}",
        f"- **Last Price:** ${q.last_price:.2f}",
        f"- **Day High/Low:** ${q.day_high:.2f} / ${q.day_low:.2f}",
        f"- **Prev Close:** ${q.previous_close:.2f}",
        "",
        "**Expected Move (1-Standard Deviation):**",
        f"- **Target Expiration:** {em.target_expiration} ({em.dte} DTE)",
        f"- **Implied Volatility (IV):** {em.implied_volatility:.1f}%",
        f"- **Expected Move:** ±${em.expected_move_dollar:.2f}",
        f"- **Range:** ${em.range_low:.2f} - ${em.range_high:.2f}",
        "",
        f"**Greeks (ATM {em.target_expiration} Exp):**",
        f"- **Delta:** {g.delta_call:.2f} (Call) / {g.delta_put:.2f} (Put)",
        f"- **Gamma:** {g.gamma:.4f}",
        f"- **Theta:** -${abs(g.theta_straddle):.2f}/day (combined ATM straddle; Call: -${abs(g.theta_call):.2f}/day, Put: -${abs(g.theta_put):.2f}/day)",
        f"- **Vega:** ${g.vega:.2f}",
        "",
        "**P/L Table (Hypothetical ATM Straddle):**",
        "| Underlying Price | P/L at Expiration |",
        "|------------------|-------------------|",
    ])

    for row in quant.pnl_table:
        sign = "+" if row.pnl_per_share >= 0 else "-"
        formatted_pnl = f"{sign}${abs(row.pnl_per_share):.2f}"
        lines.append(f"| {row.scenario_label:<16} | {formatted_pnl:<17} |")

    lines.extend([
        "",
        "---",
        "",
        "## Risk Audit",
        f"**Risk Rating:** {risk.risk_rating.value}",
        "",
        "### Analysis Checklist:",
    ])

    for idx, item in enumerate(risk.checklist, start=1):
        lines.append(f"{idx}. **{item.name}:** {item.status.value}. {item.detail}")

    lines.extend([
        "",
        '**The "Bear Case":**',
        risk.bear_case,
        "",
        "**Worst Case Scenario (Max Loss):**",
        f"- **Option Buyer:** {risk.worst_case_option_buyer}",
        f"- **Equity Holder:** {risk.worst_case_equity_holder}",
        "",
        "**Suggested Stop-Loss:**",
        f"- **Short-term Exit:** ${risk.suggested_stop_short:.2f}",
        f"- **Hard Stop:** ${risk.suggested_stop_hard:.2f}",
        "",
        "---",
        f"### Final Verdict: {risk.verdict_subtitle or risk.verdict.value}",
        risk.verdict_rationale,
        "",
    ])

    return "\n".join(lines)


def save_markdown_report(report: DeskReport, output_dir: Path | None = None) -> Path:
    """Save the markdown report to the destination directory."""
    target_dir = output_dir or config.reports_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{report.symbol}_analysis.md"
    content = generate_markdown_report(report)
    file_path.write_text(content, encoding="utf-8")
    return file_path
