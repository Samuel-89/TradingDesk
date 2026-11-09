"""Hypothetical ATM Straddle P/L table calculation."""

from typing import List
from tradingdesk.models.options import PnLRow


def calculate_pnl_table(
    spot: float,
    strike: float,
    straddle_cost: float,
    expected_move: float,
) -> List[PnLRow]:
    """Calculate P/L at expiration for a Long ATM Straddle across standard deviation moves.

    A Long Straddle (Long 1 Call + Long 1 Put) payoff at expiration:
        Payoff = max(0, S_exp - K) + max(0, K - S_exp) = |S_exp - K|
        Net PnL = Payoff - Straddle Cost = |S_exp - K| - Straddle Cost
    """
    scenarios = [
        ("-2 SD", spot - 2.0 * expected_move),
        ("-1 SD", spot - 1.0 * expected_move),
        ("ATM", spot),
        ("+1 SD", spot + 1.0 * expected_move),
        ("+2 SD", spot + 2.0 * expected_move),
    ]

    rows: List[PnLRow] = []
    for label, target_price in scenarios:
        target_price_rounded = round(target_price, 2)
        # Expiration payoff of ATM straddle
        payoff = abs(target_price_rounded - strike)
        net_pnl = payoff - straddle_cost

        rows.append(
            PnLRow(
                scenario_label=f"${target_price_rounded:.2f} ({label})",
                underlying_price=target_price_rounded,
                pnl_per_share=round(net_pnl, 2),
            )
        )

    return rows
