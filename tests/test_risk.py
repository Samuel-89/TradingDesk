"""Unit tests for risk and compliance audit module."""

from datetime import date, timedelta
from tradingdesk.models.market import MarketQuote
from tradingdesk.models.options import OptionsAnalysis, ExpectedMove, Greeks
from tradingdesk.models.risk import CheckStatus, RiskRating, VerdictType
from tradingdesk.risk.audit import (
    evaluate_liquidity,
    evaluate_event_risk,
    evaluate_leverage_risk,
)
from tradingdesk.risk.scenarios import calculate_worst_case_scenarios
from tradingdesk.risk.verdict import synthesize_risk_audit


def test_liquidity_check_pass_and_fail():
    """Verify liquidity passes on high volume/tight spreads, fails on 0 volume."""
    good_options = {
        "call_volume": 120,
        "put_volume": 90,
        "call_oi": 500,
        "put_oi": 400,
        "call_bid_ask_spread": 0.05,
        "put_bid_ask_spread": 0.05,
        "atm_call_price": 4.0,
    }
    item = evaluate_liquidity(good_options)
    assert item.status == CheckStatus.PASS
    assert item.name == "Liquidity Check"
    assert "healthy liquidity" in item.detail

    moderate_options = {
        "call_volume": 10,
        "put_volume": 10,
        "call_oi": 20,
        "put_oi": 20,
        "call_bid_ask_spread": 0.05,
        "put_bid_ask_spread": 0.05,
        "atm_call_price": 4.0,
    }
    mod_item = evaluate_liquidity(moderate_options)
    assert mod_item.status == CheckStatus.WARNING
    assert "Moderate liquidity" in mod_item.detail

    wide_spread_options = {
        "call_volume": 200,
        "put_volume": 200,
        "call_oi": 500,
        "put_oi": 500,
        "call_bid_ask_spread": 1.50,  # 1.50 / 4.0 = 37.5% > 15%
        "put_bid_ask_spread": 1.50,
        "atm_call_price": 4.0,
    }
    wide_item = evaluate_liquidity(wide_spread_options)
    assert wide_item.status == CheckStatus.WARNING

    dry_options = {
        "call_volume": 0,
        "put_volume": 0,
        "call_oi": 0,
        "put_oi": 0,
        "call_bid_ask_spread": 2.0,
        "put_bid_ask_spread": 2.0,
        "atm_call_price": 4.0,
    }
    dry_item = evaluate_liquidity(dry_options)
    assert dry_item.status == CheckStatus.FAIL
    assert "Low or zero recorded option volume" in dry_item.detail


def test_event_risk_with_imminent_earnings():
    """Verify event risk fails when earnings date is within DTE window."""
    options_meta = {"dte": 8}
    imminent_date = str(date.today() + timedelta(days=3))
    extra_meta = {"earnings_date": imminent_date}

    item = evaluate_event_risk(options_meta, extra_meta)
    assert item.status == CheckStatus.FAIL
    assert "Upcoming earnings release" in item.detail
    assert "Binary event risk creates severe volatility" in item.detail


def test_event_risk_with_imminent_dividend():
    """Verify event risk fails when ex-dividend date is within DTE window."""
    options_meta = {"dte": 8}
    imminent_div = str(date.today() + timedelta(days=5))
    extra_meta = {"dividend_date": imminent_div}

    item = evaluate_event_risk(options_meta, extra_meta)
    assert item.status == CheckStatus.FAIL
    assert "Ex-dividend date" in item.detail


def test_event_risk_clean_and_distant():
    """Verify event risk passes when events are outside DTE or in the past."""
    options_meta = {"dte": 8}
    distant_date = str(date.today() + timedelta(days=30))
    past_date = str(date.today() - timedelta(days=10))
    extra_meta = {"earnings_date": distant_date, "dividend_date": past_date}

    item = evaluate_event_risk(options_meta, extra_meta)
    assert item.status == CheckStatus.PASS
    assert "No binary corporate earnings" in item.detail

    # Empty / None dates
    clean_item = evaluate_event_risk(options_meta, {})
    assert clean_item.status == CheckStatus.PASS


def test_leverage_risk_thresholds():
    """Verify leverage risk triggers warning if straddle cost > 6% of stock price."""
    # Under 6%: $5 on $100 stock = 5%
    item_normal = evaluate_leverage_risk(straddle_cost=5.0, spot_price=100.0)
    assert item_normal.status == CheckStatus.PASS
    assert item_normal.name == "Over-Leverage"

    # Over 6%: $8 on $100 stock = 8%
    item_high = evaluate_leverage_risk(straddle_cost=8.0, spot_price=100.0)
    assert item_high.status == CheckStatus.WARNING
    assert "High implied volatility premium (8.0%" in item_high.detail


def test_worst_case_scenarios_and_stops():
    """Verify scenario calculations, percentage drawdowns, and stop-loss levels."""
    spot = 100.0
    straddle_cost = 6.0
    expected_move = 5.0

    opt_loss, eq_loss, stop_short, stop_hard = calculate_worst_case_scenarios(
        spot=spot,
        straddle_cost=straddle_cost,
        expected_move=expected_move,
    )

    # Short stop = 100 - 1.0 * 5 = 95.0
    assert stop_short == 95.0
    # Hard stop = 100 - 1.5 * 5 = 92.5
    assert stop_hard == 92.5

    # -2 SD = 100 - 2*5 = 90.0, drawdown = 10.0%
    assert "$6.00/share" in opt_loss
    assert "$90.00" in eq_loss
    assert "-10.0%" in eq_loss


def test_risk_verdict_synthesis():
    """Verify end-to-end risk audit generation produces stops, bear case, and verdict."""
    quote = MarketQuote(
        symbol="TEST",
        last_price=100.0,
        day_high=102.0,
        day_low=99.0,
        previous_close=99.5,
        pe_ratio=40.0,
        beta=1.3,
    )
    em = ExpectedMove(
        target_expiration="2026-11-20",
        dte=8,
        implied_volatility=25.0,
        expected_move_dollar=5.0,
        range_low=95.0,
        range_high=105.0,
    )
    greeks = Greeks(
        delta_call=0.5,
        delta_put=-0.5,
        gamma=0.02,
        theta_call=-0.2,
        theta_put=-0.2,
        theta_straddle=-0.4,
        vega=0.1,
    )
    quant = OptionsAnalysis(
        atm_strike=100.0,
        atm_call_price=3.0,
        atm_put_price=3.0,
        straddle_cost=6.0,
        expected_move=em,
        greeks=greeks,
        pnl_table=[],
    )

    options_meta = {
        "dte": 8,
        "call_volume": 100,
        "put_volume": 100,
        "call_oi": 300,
        "put_oi": 300,
        "call_bid_ask_spread": 0.05,
        "put_bid_ask_spread": 0.05,
        "atm_call_price": 3.0,
    }
    extra_meta = {"earnings_date": None, "dividend_date": None}

    audit = synthesize_risk_audit(quote, quant, options_meta, extra_meta)
    assert audit.suggested_stop_short == 95.0
    assert audit.suggested_stop_hard == 92.5
    assert len(audit.bear_case) > 10
    assert audit.verdict == VerdictType.GO
    assert audit.risk_rating == RiskRating.LOW
    assert "rich valuation multiple (40.0x P/E)" in audit.bear_case
    assert "high beta (1.30)" in audit.bear_case


def test_risk_verdict_imminent_event_no_go():
    """Verify imminent event triggers NO-GO and event subtitle."""
    quote = MarketQuote(
        symbol="MSFT",
        last_price=400.0,
        day_high=405.0,
        day_low=398.0,
        previous_close=401.0,
    )
    em = ExpectedMove(
        target_expiration="2026-11-20",
        dte=8,
        implied_volatility=30.0,
        expected_move_dollar=12.0,
        range_low=388.0,
        range_high=412.0,
    )
    quant = OptionsAnalysis(
        atm_strike=400.0,
        atm_call_price=7.0,
        atm_put_price=7.0,
        straddle_cost=14.0,
        expected_move=em,
        greeks=Greeks(
            delta_call=0.5,
            delta_put=-0.5,
            gamma=0.01,
            theta_call=-0.5,
            theta_put=-0.5,
            theta_straddle=-1.0,
            vega=0.2,
        ),
        pnl_table=[],
    )
    options_meta = {
        "dte": 8,
        "call_volume": 200,
        "put_volume": 200,
        "call_oi": 1000,
        "put_oi": 1000,
        "call_bid_ask_spread": 0.10,
        "put_bid_ask_spread": 0.10,
        "atm_call_price": 7.0,
    }
    extra_meta = {"earnings_date": str(date.today() + timedelta(days=2))}

    audit = synthesize_risk_audit(quote, quant, options_meta, extra_meta)
    assert audit.verdict == VerdictType.NO_GO
    assert audit.risk_rating in [RiskRating.HIGH, RiskRating.EXTREME]
    assert "Event Risk Ahead" in audit.verdict_subtitle


def test_risk_verdict_caution_on_warning():
    """Verify single warning produces CAUTION and MEDIUM risk."""
    quote = MarketQuote(
        symbol="XYZ",
        last_price=100.0,
        day_high=101.0,
        day_low=99.0,
        previous_close=100.0,
    )
    em = ExpectedMove(
        target_expiration="2026-11-20",
        dte=8,
        implied_volatility=50.0,
        expected_move_dollar=8.0,
        range_low=92.0,
        range_high=108.0,
    )
    # Straddle cost 8.0 on 100.0 = 8.0% > 6.0% (WARNING for Over-Leverage)
    quant = OptionsAnalysis(
        atm_strike=100.0,
        atm_call_price=4.0,
        atm_put_price=4.0,
        straddle_cost=8.0,
        expected_move=em,
        greeks=Greeks(
            delta_call=0.5,
            delta_put=-0.5,
            gamma=0.01,
            theta_call=-0.5,
            theta_put=-0.5,
            theta_straddle=-1.0,
            vega=0.2,
        ),
        pnl_table=[],
    )
    options_meta = {
        "dte": 8,
        "call_volume": 200,
        "put_volume": 200,
        "call_oi": 1000,
        "put_oi": 1000,
        "call_bid_ask_spread": 0.10,
        "put_bid_ask_spread": 0.10,
        "atm_call_price": 4.0,
    }
    extra_meta = {}

    audit = synthesize_risk_audit(quote, quant, options_meta, extra_meta)
    assert audit.verdict == VerdictType.CAUTION
    assert audit.risk_rating == RiskRating.MEDIUM
    assert "Define Sizing" in audit.verdict_subtitle
