"""Unit tests for Markdown and reporting output."""

from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from tradingdesk.models.market import MarketQuote
from tradingdesk.models.options import OptionsAnalysis, ExpectedMove, Greeks, PnLRow
from tradingdesk.models.risk import RiskAudit, RiskRating, VerdictType, ChecklistItem, CheckStatus
from tradingdesk.models.report import MarketResearch, DeskReport
from tradingdesk.reporters.markdown import generate_markdown_report, save_markdown_report
from tradingdesk.reporters.terminal import render_terminal_report
from tradingdesk.cli import app
from tradingdesk.engine import run_desk_review

runner = CliRunner()


def _create_sample_report() -> DeskReport:
    quote = MarketQuote(
        symbol="MSFT",
        last_price=419.09,
        day_high=426.34,
        day_low=415.72,
        previous_close=418.46,
    )
    research = MarketResearch(
        sentiment="Bullish / Moderate Buy",
        summary="Microsoft Inc. continues to be viewed as a leader in AI and cloud computing.",
        key_headlines=["CapEx Spending Anxiety", "Regulatory Scrutiny"],
    )
    em = ExpectedMove(
        target_expiration="2026-05-29",
        dte=8,
        implied_volatility=25.9,
        expected_move_dollar=16.09,
        range_low=403.00,
        range_high=435.18,
    )
    greeks = Greeks(
        delta_call=0.50,
        delta_put=-0.50,
        gamma=0.0248,
        theta_call=-0.43,
        theta_put=-0.37,
        theta_straddle=-0.80,
        vega=0.25,
    )
    pnl_table = [
        PnLRow(scenario_label="$386.91 (-2 SD)", underlying_price=386.91, pnl_per_share=19.79),
        PnLRow(scenario_label="$403.00 (-1 SD)", underlying_price=403.00, pnl_per_share=3.70),
        PnLRow(scenario_label="$419.09 (ATM)", underlying_price=419.09, pnl_per_share=-12.39),
        PnLRow(scenario_label="$435.18 (+1 SD)", underlying_price=435.18, pnl_per_share=1.88),
        PnLRow(scenario_label="$451.27 (+2 SD)", underlying_price=451.27, pnl_per_share=17.97),
    ]
    quant = OptionsAnalysis(
        atm_strike=419.09,
        atm_call_price=6.50,
        atm_put_price=5.89,
        straddle_cost=12.39,
        expected_move=em,
        greeks=greeks,
        pnl_table=pnl_table,
    )
    risk = RiskAudit(
        risk_rating=RiskRating.HIGH,
        checklist=[
            ChecklistItem(name="Liquidity Check", status=CheckStatus.PASS, detail="Tight spreads."),
            ChecklistItem(name="Event Risk", status=CheckStatus.FAIL, detail="Holding through PCE inflation data."),
            ChecklistItem(name="Over-Leverage", status=CheckStatus.WARNING, detail="Capped risk for buyer, uncapped for seller."),
        ],
        bear_case="Aggressive CapEx spending and hot inflation print could push price below $403 support.",
        worst_case_option_buyer="Total loss of premium paid ($12.39/share).",
        worst_case_equity_holder="Significant drawdown to $386.91 range (-2 SD).",
        suggested_stop_short=403.00,
        suggested_stop_hard=395.00,
        verdict=VerdictType.NO_GO,
        verdict_subtitle="NO-GO (Wait for PCE)",
        verdict_rationale="The risk-to-reward ratio is unfavorable for initiating new positions.",
    )

    return DeskReport(
        symbol="MSFT",
        date_str="May 21, 2026",
        market_quote=quote,
        research=research,
        quant=quant,
        risk=risk,
    )


def test_markdown_report_generation(tmp_path: Path):
    """Verify markdown output structure matches expected sections."""
    report = _create_sample_report()
    md_text = generate_markdown_report(report)

    # Validate essential sections
    assert "# MSFT Analysis Report - May 21, 2026" in md_text
    assert "## Market Research" in md_text
    assert "## Financial Analysis" in md_text
    assert "## Risk Audit" in md_text
    assert "### Final Verdict: NO-GO (Wait for PCE)" in md_text
    assert "| $386.91 (-2 SD)" in md_text

    # Test saving
    saved_path = save_markdown_report(report, output_dir=tmp_path)
    assert saved_path.exists()
    assert saved_path.name == "MSFT_analysis.md"
    assert saved_path.read_text(encoding="utf-8") == md_text


def test_render_terminal_report():
    """Verify terminal report rendering does not crash."""
    report = _create_sample_report()
    # Test rendering to terminal console
    render_terminal_report(report)


def test_cli_help():
    """Verify CLI help option works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Analyze a stock ticker" in result.stdout


def test_cli_review_with_mock(tmp_path: Path):
    """Verify CLI review command runs end-to-end with mocked engine."""
    sample_report = _create_sample_report()
    with patch("tradingdesk.cli.run_desk_review", return_value=sample_report):
        result = runner.invoke(app, ["MSFT", "--reports-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Report generated successfully" in result.stdout
        assert (tmp_path / "MSFT_analysis.md").exists()


def test_orchestrator_engine_mocked():
    """Verify run_desk_review orchestrates all pipeline steps correctly."""
    mock_quote = MarketQuote(
        symbol="TEST",
        last_price=100.0,
        day_high=105.0,
        day_low=95.0,
        previous_close=99.0,
    )
    mock_extra = {"earnings_date": "2026-06-01", "dividend_date": None}
    mock_news = [{"title": "Test Headline", "description": "Desc", "link": "http", "pub_date": "Date"}]
    mock_options = {
        "dte": 8,
        "implied_volatility": 0.20,
        "atm_strike": 100.0,
        "atm_call_price": 2.50,
        "atm_put_price": 2.30,
        "straddle_price": 4.80,
        "target_expiration": "2026-05-29",
        "atm_call_volume": 500,
        "atm_call_oi": 1000,
        "atm_call_spread": 0.10,
    }

    with patch("tradingdesk.engine.fetch_market_quote", return_value=(mock_quote, mock_extra)), \
         patch("tradingdesk.engine.fetch_ticker_news_rss", return_value=mock_news), \
         patch("tradingdesk.engine.fetch_options_chain_data", return_value=mock_options):

        report = run_desk_review("TEST")
        assert report.symbol == "TEST"
        assert report.market_quote.last_price == 100.0
        assert report.quant.atm_strike == 100.0
        assert report.quant.straddle_cost == 4.80
        assert report.risk.risk_rating is not None
        assert report.research.sentiment is not None
