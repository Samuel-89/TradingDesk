"""Command Line Interface (CLI) for TradingDesk."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tradingdesk.engine import run_desk_review
from tradingdesk.reporters.terminal import render_terminal_report
from tradingdesk.reporters.markdown import save_markdown_report

app = typer.Typer(
    name="tradingdesk",
    help="Offline Algorithmic Trading Desk: Market Research, Quantitative Math, and Risk Audit",
    add_completion=False,
)
console = Console(force_terminal=True, legacy_windows=False)


@app.command()
def review(
    ticker: Optional[str] = typer.Argument(
        None,
        help="Stock ticker symbol (e.g. MSFT, AAPL, TSLA)",
    ),
    reports_dir: Optional[Path] = typer.Option(
        None,
        "--reports-dir",
        "-r",
        help="Custom directory to store markdown reports (defaults to ./reports)",
    ),
) -> None:
    """Analyze a stock ticker through Market Research, Quant Greeks/Expected Move, and Risk Audit."""
    if not ticker:
        ticker = typer.prompt("Enter stock ticker symbol (e.g. MSFT, AAPL)")

    symbol = ticker.strip().replace("$", "").upper()
    if not symbol:
        console.print("[bold red]Error: No valid ticker symbol provided.[/bold red]")
        raise typer.Exit(code=1)

    target_dir = reports_dir or Path.cwd() / "reports"

    try:
        with console.status(f"[bold cyan]Running Trading Desk analysis for {symbol}...[/bold cyan]", spinner="dots"):
            report = run_desk_review(symbol)
            saved_path = save_markdown_report(report, output_dir=target_dir)

        # Render rich output in CLI
        render_terminal_report(report)

        # Confirmation notice
        console.print(f"\n[bold green][SUCCESS] Report generated successfully:[/bold green] [underline]{saved_path}[/underline]\n")

    except Exception as e:
        console.print(f"\n[bold red]Error analyzing {symbol}:[/bold red] {e}")
        raise typer.Exit(code=1)


def main():
    """Main entrypoint for setuptools console script and direct execution."""
    app()


if __name__ == "__main__":
    main()
