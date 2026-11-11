"""Market context and summary generator."""

from typing import List, Dict, Any
from tradingdesk.models.market import MarketQuote
from tradingdesk.models.report import MarketResearch
from tradingdesk.research.sentiment import evaluate_market_sentiment


def generate_market_research(
    quote: MarketQuote,
    articles: List[Dict[str, str]],
    extra_meta: Dict[str, Any],
) -> MarketResearch:
    """Generate structured market research offline.

    Synthesizes narrative overview, corporate calendar dates, and top news drivers.
    """
    sentiment_label, score = evaluate_market_sentiment(
        articles=articles,
        extra_meta=extra_meta,
        last_price=quote.last_price,
        fifty_two_week_high=quote.fifty_two_week_high or 0.0,
        fifty_two_week_low=quote.fifty_two_week_low or 0.0,
    )

    headlines = []
    for art in articles[:4]:
        title = art.get("title", "").strip()
        if title:
            headlines.append(title)

    # Narrative summary
    company = quote.company_name or quote.symbol
    sector_str = f" in the {quote.sector} sector" if quote.sector else ""
    summary = (
        f"{company} ({quote.symbol}){sector_str} is currently exhibiting a {sentiment_label.lower()} posture. "
        f"The stock is trading at ${quote.last_price:.2f} relative to its day range of "
        f"${quote.day_low:.2f} - ${quote.day_high:.2f}."
    )

    if quote.fifty_two_week_high and quote.fifty_two_week_low:
        pct_from_high = ((quote.fifty_two_week_high - quote.last_price) / quote.fifty_two_week_high) * 100
        if pct_from_high > 15:
            summary += f" Shares remain approximately {pct_from_high:.1f}% below their 52-week peak (${quote.fifty_two_week_high:.2f}), presenting valuation support but elevated volatility."

    earnings_date = extra_meta.get("earnings_date")
    dividend_date = extra_meta.get("dividend_date")

    return MarketResearch(
        sentiment=sentiment_label,
        summary=summary,
        key_headlines=headlines,
        earnings_date=earnings_date,
        dividend_date=dividend_date,
    )
