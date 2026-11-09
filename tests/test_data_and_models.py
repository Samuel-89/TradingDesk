"""Unit tests for domain models, configuration, and market data ingestion."""

from datetime import date
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from tradingdesk.config import AppConfig, QuantConfig, RiskConfig, config
from tradingdesk.models import (
    ChecklistItem,
    CheckStatus,
    DeskReport,
    ExpectedMove,
    Greeks,
    MarketQuote,
    MarketResearch,
    OptionsAnalysis,
    PnLRow,
    RiskAudit,
    RiskRating,
    VerdictType,
)
from tradingdesk.data.market_data import (
    fetch_market_quote,
    get_fast_info_val,
    safe_float,
    safe_int,
)
from tradingdesk.data.news_data import fetch_ticker_news_rss
from tradingdesk.data.options_data import (
    fetch_options_chain_data,
    select_target_expiration,
)


# =====================================================================
# 1. Configuration Tests
# =====================================================================

def test_default_config():
    """Verify default parameters for quant, risk, and app configs."""
    assert config.quant.risk_free_rate == 0.045
    assert config.quant.target_dte_min == 5
    assert config.quant.target_dte_max == 16
    assert config.quant.std_dev_multipliers == [-2.0, -1.0, 0.0, 1.0, 2.0]

    assert config.risk.min_option_volume == 50
    assert config.risk.min_open_interest == 100
    assert config.risk.max_bid_ask_spread_pct == 0.15
    assert config.risk.earnings_warning_days == 14
    assert config.risk.dividend_warning_days == 7

    assert config.reports_dir.name == "reports"


def test_custom_config():
    """Verify custom values can be supplied to config models."""
    custom_quant = QuantConfig(risk_free_rate=0.05, target_dte_min=7, target_dte_max=21)
    custom_risk = RiskConfig(min_option_volume=100)
    app = AppConfig(quant=custom_quant, risk=custom_risk)

    assert app.quant.risk_free_rate == 0.05
    assert app.risk.min_option_volume == 100


# =====================================================================
# 2. Domain Models Validation Tests
# =====================================================================

def test_market_quote_valid():
    """Verify MarketQuote instantiation with valid data."""
    quote = MarketQuote(
        symbol="AAPL",
        company_name="Apple Inc.",
        last_price=220.50,
        day_high=222.00,
        day_low=219.00,
        previous_close=220.00,
        volume=50000000,
        beta=1.12,
        pe_ratio=32.5,
        sector="Technology",
        industry="Consumer Electronics",
    )
    assert quote.symbol == "AAPL"
    assert quote.last_price == 220.50
    assert quote.beta == 1.12


def test_market_quote_validation_error():
    """Verify MarketQuote raises ValidationError when required fields are missing."""
    with pytest.raises(ValidationError):
        MarketQuote(symbol="AAPL")  # Missing required prices


def test_greeks_valid():
    """Verify Greeks model creation and field validation."""
    greeks = Greeks(
        delta_call=0.51,
        delta_put=-0.49,
        gamma=0.035,
        theta_call=-0.15,
        theta_put=-0.12,
        theta_straddle=-0.27,
        vega=0.25,
    )
    assert greeks.delta_call == 0.51
    assert greeks.theta_straddle == -0.27


def test_expected_move_and_options_analysis():
    """Verify ExpectedMove and full OptionsAnalysis model hierarchy."""
    em = ExpectedMove(
        target_expiration="2026-11-20",
        dte=8,
        implied_volatility=0.28,
        expected_move_dollar=7.50,
        range_low=212.50,
        range_high=227.50,
    )
    greeks = Greeks(
        delta_call=0.50,
        delta_put=-0.50,
        gamma=0.03,
        theta_call=-0.10,
        theta_put=-0.10,
        theta_straddle=-0.20,
        vega=0.20,
    )
    pnl_table = [
        PnLRow(scenario_label="-1 SD", underlying_price=212.50, pnl_per_share=0.50),
        PnLRow(scenario_label="ATM", underlying_price=220.00, pnl_per_share=-7.00),
        PnLRow(scenario_label="+1 SD", underlying_price=227.50, pnl_per_share=0.50),
    ]

    analysis = OptionsAnalysis(
        atm_strike=220.0,
        atm_call_price=4.20,
        atm_put_price=3.80,
        straddle_cost=8.00,
        expected_move=em,
        greeks=greeks,
        pnl_table=pnl_table,
    )

    assert analysis.atm_strike == 220.0
    assert analysis.expected_move.dte == 8
    assert len(analysis.pnl_table) == 3
    assert analysis.pnl_table[1].pnl_per_share == -7.00


def test_risk_models():
    """Verify CheckStatus, RiskRating, VerdictType enums and RiskAudit model."""
    checklist = [
        ChecklistItem(name="Liquidity", status=CheckStatus.PASS, detail="Good volume"),
        ChecklistItem(name="Event Risk", status=CheckStatus.WARNING, detail="Earnings in 12 days"),
    ]

    audit = RiskAudit(
        risk_rating=RiskRating.MEDIUM,
        checklist=checklist,
        bear_case="Multiple contraction risk if guidance slows.",
        worst_case_option_buyer="100% loss of straddle premium ($8.00)",
        worst_case_equity_holder="-2 SD decline to $205.00 (-6.8%)",
        suggested_stop_short=212.50,
        suggested_stop_hard=208.75,
        verdict=VerdictType.CAUTION,
        verdict_subtitle="Wait for catalyst clearance",
        verdict_rationale="Imminent earnings call presents binary gap risk.",
    )

    assert audit.risk_rating == RiskRating.MEDIUM
    assert audit.verdict == VerdictType.CAUTION
    assert len(audit.checklist) == 2


def test_desk_report_unified():
    """Verify complete DeskReport creation combining all sub-models."""
    quote = MarketQuote(
        symbol="MSFT",
        company_name="Microsoft Corp",
        last_price=415.00,
        day_high=418.00,
        day_low=412.00,
        previous_close=414.00,
    )
    research = MarketResearch(
        sentiment="Bullish / Moderate Buy",
        summary="Positive momentum in Azure cloud segment.",
        key_headlines=["MSFT expands cloud AI infrastructure", "Tech earnings preview"],
        earnings_date="2026-11-25",
    )
    em = ExpectedMove(
        target_expiration="2026-11-20",
        dte=8,
        implied_volatility=0.22,
        expected_move_dollar=12.0,
        range_low=403.0,
        range_high=427.0,
    )
    greeks = Greeks(
        delta_call=0.52,
        delta_put=-0.48,
        gamma=0.02,
        theta_call=-0.18,
        theta_put=-0.15,
        theta_straddle=-0.33,
        vega=0.35,
    )
    quant = OptionsAnalysis(
        atm_strike=415.0,
        atm_call_price=7.50,
        atm_put_price=6.50,
        straddle_cost=14.00,
        expected_move=em,
        greeks=greeks,
        pnl_table=[],
    )
    risk = RiskAudit(
        risk_rating=RiskRating.LOW,
        checklist=[],
        bear_case="High valuation multiple.",
        worst_case_option_buyer="Premium loss",
        worst_case_equity_holder="Downside risk",
        suggested_stop_short=403.0,
        suggested_stop_hard=397.0,
        verdict=VerdictType.GO,
        verdict_rationale="Metrics within parameters.",
    )

    report = DeskReport(
        symbol="MSFT",
        market_quote=quote,
        research=research,
        quant=quant,
        risk=risk,
    )

    assert report.symbol == "MSFT"
    assert report.market_quote.last_price == 415.00
    assert report.research.sentiment == "Bullish / Moderate Buy"
    assert report.quant.straddle_cost == 14.00
    assert report.risk.verdict == VerdictType.GO
    assert len(report.date_str) > 0


# =====================================================================
# 3. Market Data Helpers and FastInfo Tests
# =====================================================================

def test_safe_conversions():
    """Verify safe_float and safe_int with various edge-case inputs."""
    assert safe_float(12.34) == 12.34
    assert safe_float("45.67") == 45.67
    assert safe_float(None) is None
    assert safe_float(None, 0.0) == 0.0
    assert safe_float(float("nan"), 5.0) == 5.0
    assert safe_float(np.nan, 0.0) == 0.0
    assert safe_float("invalid", 10.0) == 10.0

    assert safe_int(42) == 42
    assert safe_int(42.8) == 42
    assert safe_int("99") == 99
    assert safe_int("99.0") == 99
    assert safe_int(None) is None
    assert safe_int(None, 0) == 0
    assert safe_int(float("nan"), 10) == 10
    assert safe_int(np.nan, 0) == 0
    assert safe_int("bad_int", 5) == 5


def test_get_fast_info_val_variations():
    """Verify get_fast_info_val handles attributes, dictionary indexing, and camelCase keys."""
    # 1. Attribute access (snake_case)
    class FastInfoObj:
        last_price = 150.25
        year_high = np.nan
        yearHigh = 160.0

    obj = FastInfoObj()
    assert get_fast_info_val(obj, "last_price", "lastPrice") == 150.25
    assert get_fast_info_val(obj, "year_high", "yearHigh") == 160.0
    assert get_fast_info_val(obj, "missing_key", "missingKey", 99.0) == 99.0

    # 2. Dict-like access (camelCase key)
    dict_info = {"lastPrice": 275.50, "dayHigh": 280.0, "day_low": 270.0}
    assert get_fast_info_val(dict_info, "last_price", "lastPrice") == 275.50
    assert get_fast_info_val(dict_info, "day_high", "dayHigh") == 280.0
    assert get_fast_info_val(dict_info, "day_low", "dayLow") == 270.0

    # 3. None fast_info
    assert get_fast_info_val(None, "foo", "bar", "fallback") == "fallback"


@patch("tradingdesk.data.market_data.yf.Ticker")
def test_fetch_market_quote(mock_ticker_cls):
    """Verify fetch_market_quote extracts quote and metadata correctly from yf.Ticker."""
    mock_instance = MagicMock()
    mock_ticker_cls.return_value = mock_instance

    # Mock fast_info
    mock_fast_info = MagicMock()
    mock_fast_info.last_price = 185.50
    mock_fast_info.day_high = 187.00
    mock_fast_info.day_low = 184.20
    mock_fast_info.previous_close = 184.80
    mock_fast_info.last_volume = 45000000
    mock_fast_info.year_high = 199.62
    mock_fast_info.year_low = 145.20
    mock_instance.fast_info = mock_fast_info

    # Mock info dict
    mock_instance.info = {
        "shortName": "Apple Inc.",
        "beta": 1.05,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "trailingPE": 31.5,
        "targetMeanPrice": 210.0,
        "recommendationKey": "buy",
        "earningsGrowth": 0.08,
    }

    # Mock calendar dict
    mock_instance.calendar = {
        "Earnings Date": ["2026-11-20"],
        "Dividend Date": "2026-11-14",
    }

    quote, extra_meta = fetch_market_quote("AAPL")

    assert quote.symbol == "AAPL"
    assert quote.company_name == "Apple Inc."
    assert quote.last_price == 185.50
    assert quote.day_high == 187.00
    assert quote.day_low == 184.20
    assert quote.previous_close == 184.80
    assert quote.volume == 45000000
    assert quote.fifty_two_week_high == 199.62
    assert quote.beta == 1.05
    assert quote.pe_ratio == 31.5
    assert extra_meta["target_mean_price"] == 210.0
    assert extra_meta["recommendation_key"] == "buy"
    assert extra_meta["earnings_date"] == "2026-11-20"
    assert extra_meta["dividend_date"] == "2026-11-14"


# =====================================================================
# 4. News RSS Fetcher Tests
# =====================================================================

@patch("tradingdesk.data.news_data.requests.get")
def test_fetch_ticker_news_rss_success(mock_get):
    """Verify parsing valid Yahoo Finance RSS XML headlines."""
    sample_xml = b"""<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
        <channel>
            <title>Yahoo! Finance: AAPL News</title>
            <item>
                <title>Apple Announces New Silicon Breakthrough</title>
                <description>Detailed report on new chip architecture.</description>
                <link>https://finance.yahoo.com/news/apple-silicon-1234.html</link>
                <pubDate>Mon, 10 Nov 2026 14:30:00 GMT</pubDate>
            </item>
            <item>
                <title>Tech Giants Rally Ahead of Economic Data</title>
                <description>Nasdaq rises led by megacap technology stocks.</description>
                <link>https://finance.yahoo.com/news/tech-rally-5678.html</link>
                <pubDate>Mon, 10 Nov 2026 12:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = sample_xml
    mock_get.return_value = mock_resp

    articles = fetch_ticker_news_rss("AAPL", max_items=2)
    assert len(articles) == 2
    assert articles[0]["title"] == "Apple Announces New Silicon Breakthrough"
    assert "apple-silicon-1234" in articles[0]["link"]
    assert articles[0]["pub_date"] == "Mon, 10 Nov 2026 14:30:00 GMT"
    assert articles[1]["title"] == "Tech Giants Rally Ahead of Economic Data"


@patch("tradingdesk.data.news_data.requests.get")
def test_fetch_ticker_news_rss_network_failure(mock_get):
    """Verify graceful fallback to empty list when RSS request encounters an error."""
    mock_get.side_effect = Exception("Connection timeout")
    articles = fetch_ticker_news_rss("MSFT")
    assert articles == []


# =====================================================================
# 5. Options Chain and Strike Selection Tests
# =====================================================================

def test_select_target_expiration():
    """Verify target weekly expiration (~8 DTE) selection logic."""
    ref_date = date(2026, 11, 10)
    expirations = (
        "2026-11-13",  # 3 DTE (< min_dte of 5)
        "2026-11-18",  # 8 DTE (exact match for 8 DTE)
        "2026-11-25",  # 15 DTE (in window 5-16, abs diff = 7)
        "2026-12-18",  # 38 DTE (> max_dte)
    )

    selected_exp, dte = select_target_expiration(
        expirations, min_dte=5, max_dte=16, reference_date=ref_date
    )
    assert selected_exp == "2026-11-18"
    assert dte == 8


def test_select_target_expiration_fallback():
    """Verify expiration selection falls back when no dates fall in standard window."""
    ref_date = date(2026, 11, 10)
    # Only expiration far out
    expirations = ("2026-12-25",)
    selected_exp, dte = select_target_expiration(
        expirations, min_dte=5, max_dte=16, reference_date=ref_date
    )
    assert selected_exp == "2026-12-25"
    assert dte == 45

    # Empty expirations
    exp_none, dte_none = select_target_expiration([], reference_date=ref_date)
    assert exp_none is None
    assert dte_none == 0


@patch("tradingdesk.data.options_data.yf.Ticker")
def test_fetch_options_chain_data_success(mock_ticker_cls):
    """Verify ATM strike extraction, price calculations, and IV blending."""
    mock_instance = MagicMock()
    mock_ticker_cls.return_value = mock_instance

    # Next Friday expiration (~8 DTE from mock date)
    mock_instance.options = ("2026-11-20", "2026-11-27")

    # Mock option chain calls and puts
    calls_df = pd.DataFrame([
        {"strike": 215.0, "bid": 7.80, "ask": 8.00, "lastPrice": 7.90, "impliedVolatility": 0.28, "volume": 120, "openInterest": 500},
        {"strike": 220.0, "bid": 4.10, "ask": 4.30, "lastPrice": 4.20, "impliedVolatility": 0.26, "volume": 350, "openInterest": 1200},
        {"strike": 225.0, "bid": 1.90, "ask": 2.10, "lastPrice": 2.00, "impliedVolatility": 0.25, "volume": 180, "openInterest": 800},
    ])
    puts_df = pd.DataFrame([
        {"strike": 215.0, "bid": 1.70, "ask": 1.90, "lastPrice": 1.80, "impliedVolatility": 0.27, "volume": 90, "openInterest": 400},
        {"strike": 220.0, "bid": 3.70, "ask": 3.90, "lastPrice": 3.80, "impliedVolatility": 0.26, "volume": 280, "openInterest": 950},
        {"strike": 225.0, "bid": 6.80, "ask": 7.10, "lastPrice": 7.00, "impliedVolatility": 0.25, "volume": 110, "openInterest": 600},
    ])

    mock_chain = MagicMock()
    mock_chain.calls = calls_df
    mock_chain.puts = puts_df
    mock_instance.option_chain.return_value = mock_chain

    # Spot price is 221.0 -> closest strike is 220.0
    res = fetch_options_chain_data("AAPL", spot_price=221.0)

    assert res["has_options"] is True
    assert res["atm_strike"] == 220.0
    assert res["atm_call_price"] == 4.20  # (4.10 + 4.30) / 2
    assert res["atm_put_price"] == 3.80   # (3.70 + 3.90) / 2
    assert res["straddle_price"] == 8.00  # 4.20 + 3.80
    assert res["implied_volatility"] == 0.26
    assert res["call_volume"] == 350
    assert res["put_volume"] == 280
    assert res["call_oi"] == 1200
    assert res["put_oi"] == 950
    assert res["call_bid_ask_spread"] == 0.20  # 4.30 - 4.10
    assert res["put_bid_ask_spread"] == 0.20   # 3.90 - 3.70


@patch("tradingdesk.data.options_data.yf.Ticker")
def test_fetch_options_chain_data_no_options(mock_ticker_cls):
    """Verify fallback return structure when a symbol has no options chains."""
    mock_instance = MagicMock()
    mock_ticker_cls.return_value = mock_instance
    mock_instance.options = ()

    res = fetch_options_chain_data("NONEXISTENT", spot_price=100.0)
    assert res["has_options"] is False
    assert res["atm_strike"] == 100.0
    assert res["atm_call_price"] == 2.00
    assert res["atm_put_price"] == 2.00
    assert res["straddle_price"] == 4.00
