"""Trading Desk orchestrator engine."""

from datetime import datetime
from tradingdesk.data.market_data import fetch_market_quote
from tradingdesk.data.options_data import fetch_options_chain_data
from tradingdesk.data.news_data import fetch_ticker_news_rss
from tradingdesk.research.context import generate_market_research
from tradingdesk.quant.black_scholes import calculate_greeks
from tradingdesk.quant.expected_move import calculate_expected_move
from tradingdesk.quant.pnl_table import calculate_pnl_table
from tradingdesk.risk.verdict import synthesize_risk_audit
from tradingdesk.models.options import OptionsAnalysis
from tradingdesk.models.report import DeskReport
from tradingdesk.config import config


def run_desk_review(ticker_symbol: str) -> DeskReport:
    """Execute complete 3-role offline Trading Desk review for a ticker symbol."""
    symbol = ticker_symbol.strip().replace("$", "").upper()

    # Step 1: Market Data
    quote, extra_meta = fetch_market_quote(symbol)

    # Step 2: Market Researcher (offline)
    news_articles = fetch_ticker_news_rss(symbol, max_items=5)
    research = generate_market_research(quote, news_articles, extra_meta)

    # Step 3: Mathematical Analyst / Quant
    options_meta = fetch_options_chain_data(symbol, quote.last_price)
    dte = options_meta.get("dte", 8)
    t_years = max(dte, 1) / 365.0
    iv = options_meta.get("implied_volatility", 0.25)
    atm_strike = options_meta.get("atm_strike", quote.last_price)
    call_price = options_meta.get("atm_call_price", 0.0)
    put_price = options_meta.get("atm_put_price", 0.0)
    straddle_cost = options_meta.get("straddle_price", call_price + put_price)
    target_exp = options_meta.get("target_expiration", "N/A")

    # Greeks
    greeks = calculate_greeks(
        spot=quote.last_price,
        strike=atm_strike,
        time_to_exp_years=t_years,
        risk_free_rate=config.quant.risk_free_rate,
        sigma=iv,
    )

    # Expected Move
    expected_move = calculate_expected_move(
        spot=quote.last_price,
        implied_volatility=iv,
        dte=dte,
        target_expiration=target_exp,
        straddle_price=straddle_cost,
    )

    # PnL Table
    pnl_table = calculate_pnl_table(
        spot=quote.last_price,
        strike=atm_strike,
        straddle_cost=straddle_cost,
        expected_move=expected_move.expected_move_dollar,
    )

    quant = OptionsAnalysis(
        atm_strike=atm_strike,
        atm_call_price=call_price,
        atm_put_price=put_price,
        straddle_cost=straddle_cost,
        expected_move=expected_move,
        greeks=greeks,
        pnl_table=pnl_table,
    )

    # Step 4: Risk Officer
    risk = synthesize_risk_audit(
        quote=quote,
        quant=quant,
        options_meta=options_meta,
        extra_meta=extra_meta,
    )

    return DeskReport(
        symbol=symbol,
        date_str=datetime.now().strftime("%B %d, %Y"),
        market_quote=quote,
        research=research,
        quant=quant,
        risk=risk,
    )
