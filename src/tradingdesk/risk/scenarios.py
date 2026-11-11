"""Scenario loss calculations and stop-loss levels."""

from typing import Tuple


def calculate_worst_case_scenarios(
    spot: float,
    straddle_cost: float,
    expected_move: float,
) -> Tuple[str, str, float, float]:
    """Calculate worst case max loss scenarios and stop-loss prices.

    Returns:
        worst_case_option_buyer, worst_case_equity_holder, stop_loss_short, stop_loss_hard
    """
    option_buyer_loss = (
        f"Total loss of premium paid (${straddle_cost:.2f}/share) if the underlying remains range-bound through expiration."
    )

    downside_2sd = round(spot - (2.0 * expected_move), 2)
    pct_drawdown = round(((spot - downside_2sd) / spot) * 100, 1) if spot > 0 else 0.0
    equity_holder_loss = (
        f"Drawdown to ${downside_2sd:.2f} (-2 SD / -{pct_drawdown}%) if macro or downside tail-risk triggers a sharp correction."
    )

    # Stop-Loss levels:
    # Short-term exit: at -1 SD boundary
    # Hard stop: halfway between -1 SD and -2 SD (or at -1.5 SD)
    stop_loss_short = round(spot - (1.0 * expected_move), 2)
    stop_loss_hard = round(spot - (1.5 * expected_move), 2)

    return option_buyer_loss, equity_holder_loss, stop_loss_short, stop_loss_hard
