"""Rich terminal renderer for Trading Desk reviews."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from tradingdesk.models.report import DeskReport
from tradingdesk.models.risk import CheckStatus, RiskRating, VerdictType

console = Console()


def render_terminal_report(report: DeskReport) -> None:
    """Print beautifully formatted Trading Desk report directly into the terminal."""
    r = report
    q = r.market_quote
    res = r.research
    quant = r.quant
    em = quant.expected_move
    g = quant.greeks
    risk = r.risk

    # --- Header Banner ---
    title_text = Text()
    title_text.append("TRADING DESK ", style="bold cyan")
    title_text.append(f"| {q.symbol} FULL REVIEW ", style="bold white")
    title_text.append(f"({r.date_str})", style="italic dim")
    console.print(Panel(title_text, box=box.ROUNDED, border_style="cyan"))

    # --- Section 1: Market Research ---
    sentiment_color = "green" if "Bullish" in res.sentiment else ("red" if "Bear" in res.sentiment else "yellow")
    research_content = Text()
    research_content.append("Current Sentiment: ", style="bold")
    research_content.append(f"{res.sentiment}\n\n", style=f"bold {sentiment_color}")
    research_content.append(f"{res.summary}\n")

    if res.key_headlines:
        research_content.append("\nKey Headlines:\n", style="bold underline")
        for h in res.key_headlines[:3]:
            research_content.append(f" - {h}\n", style="dim")

    console.print(Panel(research_content, title="[bold]1. Market Research[/bold]", border_style="blue", box=box.ROUNDED))

    # --- Section 2: Financial & Quantitative Analysis ---
    stats_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    stats_table.add_column("Key", style="bold")
    stats_table.add_column("Value")
    stats_table.add_column("Metric", style="bold")
    stats_table.add_column("Value")

    stats_table.add_row(
        "Last Price:", f"${q.last_price:.2f}",
        "Target Expiration:", f"{em.target_expiration} ({em.dte} DTE)",
    )
    stats_table.add_row(
        "Day Range:", f"${q.day_low:.2f} - ${q.day_high:.2f}",
        "Implied Volatility (IV):", f"{em.implied_volatility:.1f}%",
    )
    stats_table.add_row(
        "Prev Close:", f"${q.previous_close:.2f}",
        "1-SD Expected Move:", f"+/-${em.expected_move_dollar:.2f}",
    )
    stats_table.add_row(
        "52W Range:", f"${q.fifty_two_week_low or 0:.2f} - ${q.fifty_two_week_high or 0:.2f}",
        "Expected Range:", f"${em.range_low:.2f} - ${em.range_high:.2f}",
    )

    # Greeks text
    greeks_text = Text()
    greeks_text.append(f"Greeks (ATM {em.target_expiration}): ", style="bold")
    greeks_text.append(f"Delta: {g.delta_call:.2f}C / {g.delta_put:.2f}P  |  ")
    greeks_text.append(f"Gamma: {g.gamma:.4f}  |  ")
    greeks_text.append(f"Theta: -${abs(g.theta_straddle):.2f}/day  |  ")
    greeks_text.append(f"Vega: ${g.vega:.2f}")

    # PnL Scenario Table
    pnl_table = Table(title="Hypothetical ATM Straddle P/L at Expiration", box=box.ROUNDED, header_style="bold magenta")
    pnl_table.add_column("Underlying Price Scenario", justify="left")
    pnl_table.add_column("Underlying Price", justify="right")
    pnl_table.add_column("P/L per Share", justify="right")

    for row in quant.pnl_table:
        sign = "+" if row.pnl_per_share >= 0 else "-"
        pnl_style = "bold green" if row.pnl_per_share > 0 else ("bold red" if row.pnl_per_share < 0 else "white")
        formatted_pnl = f"{sign}${abs(row.pnl_per_share):.2f}"
        pnl_table.add_row(row.scenario_label, f"${row.underlying_price:.2f}", Text(formatted_pnl, style=pnl_style))

    console.print(Panel(stats_table, title="[bold]2. Financial Analysis (Live Data & Quant)[/bold]", border_style="magenta", box=box.ROUNDED))
    console.print(greeks_text)
    console.print(pnl_table)

    # --- Section 3: Risk Audit ---
    risk_color_map = {
        RiskRating.LOW: "green",
        RiskRating.MEDIUM: "yellow",
        RiskRating.HIGH: "bold red",
        RiskRating.EXTREME: "bold white on red",
    }
    risk_text = Text()
    risk_text.append("Risk Rating: ", style="bold")
    risk_text.append(f"{risk.risk_rating.value}\n\n", style=risk_color_map[risk.risk_rating])

    for idx, item in enumerate(risk.checklist, start=1):
        status_color = "green" if item.status == CheckStatus.PASS else ("yellow" if item.status == CheckStatus.WARNING else "red")
        risk_text.append(f"{idx}. {item.name}: ", style="bold")
        risk_text.append(f"[{item.status.value}] ", style=f"bold {status_color}")
        risk_text.append(f"{item.detail}\n")

    risk_text.append("\nThe \"Bear Case\":\n", style="bold underline red")
    risk_text.append(f"{risk.bear_case}\n\n")

    risk_text.append("Worst Case Scenario (Max Loss):\n", style="bold underline")
    risk_text.append(f" - Option Buyer: {risk.worst_case_option_buyer}\n")
    risk_text.append(f" - Equity Holder: {risk.worst_case_equity_holder}\n\n")

    risk_text.append("Suggested Stop-Loss Levels:\n", style="bold underline")
    risk_text.append(f" - Short-term Exit: ${risk.suggested_stop_short:.2f}\n")
    risk_text.append(f" - Hard Stop:       ${risk.suggested_stop_hard:.2f}\n")

    console.print(Panel(risk_text, title="[bold]3. Risk Audit & Compliance Checklist[/bold]", border_style="red", box=box.ROUNDED))

    # --- Section 4: Final Verdict ---
    verdict_colors = {
        VerdictType.GO: "bold green",
        VerdictType.CAUTION: "bold yellow",
        VerdictType.NO_GO: "bold white on red",
    }
    verdict_panel_border = "green" if risk.verdict == VerdictType.GO else ("yellow" if risk.verdict == VerdictType.CAUTION else "red")

    verdict_text = Text()
    verdict_text.append("FINAL VERDICT: ", style="bold")
    verdict_text.append(f"{risk.verdict_subtitle or risk.verdict.value}\n\n", style=verdict_colors[risk.verdict])
    verdict_text.append(f"{risk.verdict_rationale}\n")

    console.print(Panel(verdict_text, title="[bold]Trading Desk Recommendation[/bold]", border_style=verdict_panel_border, box=box.DOUBLE))
