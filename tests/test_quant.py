"""Unit tests for quantitative math and offline research modules."""

import pytest
from tradingdesk.models.market import MarketQuote
from tradingdesk.quant.black_scholes import calc_d1_d2, calculate_greeks
from tradingdesk.quant.expected_move import calculate_expected_move
from tradingdesk.quant.pnl_table import calculate_pnl_table
from tradingdesk.research.sentiment import (
    score_text_sentiment,
    evaluate_market_sentiment,
)
from tradingdesk.research.context import generate_market_research


# =====================================================================
# 1. Black-Scholes-Merton Analytical Greeks Tests
# =====================================================================

def test_black_scholes_atm_greeks():
    """Verify ATM Greeks behavior (Call delta ~0.50, Put delta ~ -0.50, positive Gamma/Vega, negative Theta)."""
    spot = 100.0
    strike = 100.0
    t_years = 8.0 / 365.0
    r = 0.045
    sigma = 0.25

    greeks = calculate_greeks(spot, strike, t_years, r, sigma)

    # ATM Call Delta should be approximately 0.50 (slightly above due to drift r)
    assert 0.48 <= greeks.delta_call <= 0.55
    # ATM Put Delta should be approximately -0.50
    assert -0.52 <= greeks.delta_put <= -0.45
    # Delta relationship: Call Delta - Put Delta == 1.0
    assert pytest.approx(greeks.delta_call - greeks.delta_put, abs=0.01) == 1.0

    # Gamma and Vega must be positive for long options
    assert greeks.gamma > 0.0
    assert greeks.vega > 0.0

    # Theta must be negative (time decay hurts long positions)
    assert greeks.theta_call < 0.0
    assert greeks.theta_put < 0.0
    assert greeks.theta_straddle < 0.0
    assert pytest.approx(greeks.theta_straddle, abs=0.02) == (greeks.theta_call + greeks.theta_put)


def test_black_scholes_moneyness_delta():
    """Verify ITM and OTM call/put delta relationships."""
    spot = 120.0
    strike = 100.0  # Deep ITM Call, Deep OTM Put
    t_years = 30.0 / 365.0
    r = 0.045
    sigma = 0.20

    itm_call_greeks = calculate_greeks(spot, strike, t_years, r, sigma)
    assert itm_call_greeks.delta_call > 0.85
    assert itm_call_greeks.delta_put > -0.15

    otm_call_greeks = calculate_greeks(80.0, strike, t_years, r, sigma)
    assert otm_call_greeks.delta_call < 0.15
    assert otm_call_greeks.delta_put < -0.85


def test_black_scholes_edge_cases():
    """Verify BSM behavior when inputs are zero or invalid."""
    # Zero or negative inputs should return safe fallback Greeks without crashing
    zero_spot = calculate_greeks(0.0, 100.0, 0.1, 0.045, 0.25)
    assert zero_spot.delta_call == 0.50
    assert zero_spot.delta_put == -0.50
    assert zero_spot.gamma == 0.0

    zero_time = calculate_greeks(100.0, 100.0, 0.0, 0.045, 0.25)
    assert zero_time.gamma == 0.0
    assert zero_time.vega == 0.0

    d1, d2 = calc_d1_d2(0.0, 100.0, 0.1, 0.045, 0.25)
    assert d1 == 0.0 and d2 == 0.0


# =====================================================================
# 2. Expected Move Engine Tests
# =====================================================================

def test_expected_move_calculation_iv_only():
    """Verify 1-SD expected move calculation using annualized IV."""
    spot = 400.0
    iv = 0.25
    dte = 8
    target_exp = "2026-05-29"

    em = calculate_expected_move(
        spot=spot,
        implied_volatility=iv,
        dte=dte,
        target_expiration=target_exp,
    )

    assert em.target_expiration == target_exp
    assert em.dte == dte
    assert em.expected_move_dollar > 0
    assert em.range_low < spot < em.range_high
    # Symmetric bounds around spot
    assert round(em.range_high - spot, 2) == round(spot - em.range_low, 2)
    assert em.implied_volatility == 25.0


def test_expected_move_straddle_blend():
    """Verify expected move calculation blending straddle market price."""
    spot = 200.0
    iv = 0.30
    dte = 14
    straddle_price = 12.0  # 85% rule -> 10.20

    em = calculate_expected_move(
        spot=spot,
        implied_volatility=iv,
        dte=dte,
        target_expiration="2026-06-05",
        straddle_price=straddle_price,
    )

    # Expected move should be average of IV-based move and straddle rule
    iv_move = spot * iv * ((dte / 365.0) ** 0.5)
    straddle_move = 0.85 * straddle_price
    expected_blend = (iv_move + straddle_move) / 2.0

    assert pytest.approx(em.expected_move_dollar, abs=0.05) == expected_blend
    assert em.range_high == round(spot + em.expected_move_dollar, 2)
    assert em.range_low == round(spot - em.expected_move_dollar, 2)


# =====================================================================
# 3. P/L Scenario Matrix Tests
# =====================================================================

def test_pnl_table_straddle():
    """Verify ATM straddle payoff table at expiration across standard deviation moves."""
    spot = 400.0
    strike = 400.0
    straddle_cost = 12.0
    expected_move = 15.0

    rows = calculate_pnl_table(spot, strike, straddle_cost, expected_move)
    assert len(rows) == 5

    # Check scenarios present
    labels = [r.scenario_label for r in rows]
    assert any("-2 SD" in l for l in labels)
    assert any("-1 SD" in l for l in labels)
    assert any("ATM" in l for l in labels)
    assert any("+1 SD" in l for l in labels)
    assert any("+2 SD" in l for l in labels)

    # At ATM (underlying = 400.00), payoff is 0, net PnL is -straddle_cost (-12.00)
    atm_row = [r for r in rows if "ATM" in r.scenario_label][0]
    assert atm_row.underlying_price == 400.00
    assert atm_row.pnl_per_share == -straddle_cost

    # At +1 SD (underlying = 415.00), payoff is 15.00, net PnL is 15 - 12 = +3.00
    plus_1sd = [r for r in rows if "+1 SD" in r.scenario_label][0]
    assert plus_1sd.underlying_price == 415.00
    assert plus_1sd.pnl_per_share == (expected_move - straddle_cost)

    # At -2 SD (underlying = 370.00), payoff is 30.00, net PnL is 30 - 12 = +18.00
    minus_2sd = [r for r in rows if "-2 SD" in r.scenario_label][0]
    assert minus_2sd.underlying_price == 370.00
    assert minus_2sd.pnl_per_share == (2.0 * expected_move - straddle_cost)


# =====================================================================
# 4. Sentiment & Catalyst Scoring Tests
# =====================================================================

def test_text_sentiment_scoring():
    """Verify word-level sentiment scoring."""
    bullish_headline = "Company reports record profit, surge in revenue, and massive dividend boost"
    bearish_headline = "Stock plunges following revenue miss, regulatory probe, and lawsuit warning"
    neutral_headline = "Company announces annual shareholder meeting date and agenda"

    assert score_text_sentiment(bullish_headline) > 0.5
    assert score_text_sentiment(bearish_headline) < -0.5
    assert score_text_sentiment(neutral_headline) == 0.0


def test_market_sentiment_evaluation():
    """Verify multi-factor composite sentiment weighting and label assignment."""
    articles = [
        {"title": "Record earnings beat estimates", "description": "Strong cloud revenue growth"},
        {"title": "Analyst upgrades stock after rally", "description": "Bullish momentum accelerates"},
    ]
    extra_meta = {"recommendation_key": "strong_buy"}

    label, score = evaluate_market_sentiment(
        articles=articles,
        extra_meta=extra_meta,
        last_price=240.0,
        fifty_two_week_high=250.0,
        fifty_two_week_low=150.0,
    )

    assert label == "Bullish / Strong Buy"
    assert score >= 0.4

    # Test Bearish / Sell scenario
    bearish_articles = [
        {"title": "Warning on recession and headwind", "description": "Major loss and downgrade reported"},
        {"title": "Investigation and lawsuit probe launched", "description": "Stock plunges to multi-year low"},
    ]
    bear_meta = {"recommendation_key": "underperform"}

    bear_label, bear_score = evaluate_market_sentiment(
        articles=bearish_articles,
        extra_meta=bear_meta,
        last_price=105.0,
        fifty_two_week_high=200.0,
        fifty_two_week_low=100.0,
    )

    assert bear_label == "Bearish / Sell"
    assert bear_score < -0.4


# =====================================================================
# 5. Market Context Narrative Tests
# =====================================================================

def test_generate_market_research_narrative():
    """Verify narrative synthesis, corporate dates, and headline limiting."""
    quote = MarketQuote(
        symbol="MSFT",
        company_name="Microsoft Corporation",
        last_price=420.0,
        day_high=425.0,
        day_low=418.0,
        previous_close=419.0,
        fifty_two_week_high=500.0,
        fifty_two_week_low=350.0,
        sector="Technology",
    )
    articles = [
        {"title": f"Headline {i}", "description": f"Description {i}"}
        for i in range(10)
    ]
    extra_meta = {
        "recommendation_key": "buy",
        "earnings_date": "2026-07-23",
        "dividend_date": "2026-08-15",
    }

    research = generate_market_research(quote, articles, extra_meta)

    assert "Microsoft Corporation (MSFT) in the Technology sector" in research.summary
    assert "$420.00" in research.summary
    # 52w discount check: (500 - 420) / 500 = 16% (> 15%)
    assert "16.0%" in research.summary
    # Max 4 headlines retained
    assert len(research.key_headlines) == 4
    assert research.key_headlines[0] == "Headline 0"
    assert research.earnings_date == "2026-07-23"
    assert research.dividend_date == "2026-08-15"
