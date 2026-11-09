"""Expected Move and volatility calculations."""

import math
from tradingdesk.models.options import ExpectedMove


def calculate_expected_move(
    spot: float,
    implied_volatility: float,
    dte: int,
    target_expiration: str,
    straddle_price: float = 0.0,
) -> ExpectedMove:
    """Calculate the 1-standard deviation expected move.

    Formula 1 (IV rule): EM = Spot * IV * sqrt(DTE / 365)
    Formula 2 (Straddle rule): EM = 0.85 * (Call + Put)

    If straddle price is available and IV is reasonable, blends both formulas
    to provide the market-consensus expected move.
    """
    raw_iv = max(implied_volatility, 0.001)
    if raw_iv > 2.0:
        iv = raw_iv / 100.0
        iv_display = raw_iv
    else:
        iv = raw_iv
        iv_display = raw_iv * 100.0

    t_years = max(dte, 1) / 365.0

    # IV-based expected move
    iv_em = spot * iv * math.sqrt(t_years)

    # If straddle price is provided, use the options market market-maker rule: ~0.85 * straddle
    if straddle_price > 0:
        straddle_em = 0.85 * straddle_price
        # Prefer straddle implied move if available, fallback to IV expected move
        em_dollar = (straddle_em + iv_em) / 2.0 if iv > 0 else straddle_em
    else:
        em_dollar = iv_em

    range_low = round(spot - em_dollar, 2)
    range_high = round(spot + em_dollar, 2)

    return ExpectedMove(
        target_expiration=target_expiration,
        dte=dte,
        implied_volatility=round(iv_display, 1),
        expected_move_dollar=round(em_dollar, 2),
        range_low=range_low,
        range_high=range_high,
    )
