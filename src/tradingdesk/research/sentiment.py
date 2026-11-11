"""Offline market sentiment analysis using lexicon & financial indicators."""

from typing import List, Dict, Any, Tuple


# Financial sentiment word lists
BULLISH_WORDS = {
    "surge", "soar", "gain", "jump", "record", "beat", "rally", "growth",
    "profit", "strong", "outperform", "upgrade", "bull", "bullish", "high",
    "breakout", "positive", "expansion", "buy", "boost", "revenue", "dividend",
    "leadership", "accelerate", "win", "approval"
}

BEARISH_WORDS = {
    "fall", "drop", "plunge", "tumble", "miss", "loss", "slump", "concern",
    "anxiety", "risk", "warning", "probe", "investigation", "lawsuit", "cut",
    "downgrade", "bear", "bearish", "low", "headwind", "downside", "inflation",
    "recession", "overhang", "pressure", "cautious", "weakness"
}


def score_text_sentiment(text: str) -> float:
    """Calculate normalized sentiment score from -1.0 (bearish) to +1.0 (bullish)."""
    words = [w.strip(".,;:!?\"'()[]{}").lower() for w in text.split()]
    bull_count = sum(1 for w in words if w in BULLISH_WORDS)
    bear_count = sum(1 for w in words if w in BEARISH_WORDS)

    total = bull_count + bear_count
    if total == 0:
        return 0.0
    return (bull_count - bear_count) / total


def evaluate_market_sentiment(
    articles: List[Dict[str, str]],
    extra_meta: Dict[str, Any],
    last_price: float,
    fifty_two_week_high: float = 0.0,
    fifty_two_week_low: float = 0.0,
) -> Tuple[str, float]:
    """Determine market sentiment label and numeric score based on news and fundamentals.

    Weights:
        - 50% news headlines & description sentiment
        - 30% analyst recommendation key
        - 20% 52-week price position
    """
    scores = []
    for art in articles:
        combined = f"{art.get('title', '')} {art.get('description', '')}"
        scores.append(score_text_sentiment(combined))

    news_score = sum(scores) / len(scores) if scores else 0.0

    # Factor in recommendation key if available (e.g. "buy", "strong_buy", "hold")
    rec_score = 0.0
    rec_key = (extra_meta.get("recommendation_key") or "").lower()
    if "strong_buy" in rec_key or "strongbuy" in rec_key:
        rec_score = 0.8
    elif "buy" in rec_key:
        rec_score = 0.5
    elif "hold" in rec_key:
        rec_score = 0.0
    elif "underperform" in rec_key or "sell" in rec_key:
        rec_score = -0.5

    # Factor in 52-week price position
    range_score = 0.0
    if fifty_two_week_high and fifty_two_week_low and fifty_two_week_high > fifty_two_week_low:
        pct_range = (last_price - fifty_two_week_low) / (fifty_two_week_high - fifty_two_week_low)
        range_score = (pct_range - 0.5) * 2.0  # Normalized to [-1, 1]

    # Weighted blend
    composite_score = (0.5 * news_score) + (0.3 * rec_score) + (0.2 * range_score)

    if composite_score >= 0.4:
        label = "Bullish / Strong Buy"
    elif composite_score >= 0.15:
        label = "Bullish / Moderate Buy"
    elif composite_score >= -0.15:
        label = "Neutral / Hold"
    elif composite_score >= -0.4:
        label = "Cautious / Moderate Sell"
    else:
        label = "Bearish / Sell"

    return label, composite_score
