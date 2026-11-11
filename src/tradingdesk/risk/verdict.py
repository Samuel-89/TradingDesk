"""Risk verdict and synthesis engine."""

from typing import List, Dict, Any
from tradingdesk.models.market import MarketQuote
from tradingdesk.models.options import OptionsAnalysis
from tradingdesk.models.risk import (
    RiskAudit,
    RiskRating,
    VerdictType,
    ChecklistItem,
    CheckStatus,
)
from tradingdesk.risk.audit import evaluate_liquidity, evaluate_event_risk, evaluate_leverage_risk
from tradingdesk.risk.scenarios import calculate_worst_case_scenarios


def synthesize_risk_audit(
    quote: MarketQuote,
    quant: OptionsAnalysis,
    options_meta: Dict[str, Any],
    extra_meta: Dict[str, Any],
) -> RiskAudit:
    """Run full risk audit checklist, generate bear case, and determine final Go/No-Go verdict."""
    # Run checks
    liquidity_item = evaluate_liquidity(options_meta)
    event_item = evaluate_event_risk(options_meta, extra_meta)
    leverage_item = evaluate_leverage_risk(quant.straddle_cost, quote.last_price)
    checklist: List[ChecklistItem] = [liquidity_item, event_item, leverage_item]

    # Calculate worst cases and stop loss
    opt_loss, eq_loss, stop_short, stop_hard = calculate_worst_case_scenarios(
        spot=quote.last_price,
        straddle_cost=quant.straddle_cost,
        expected_move=quant.expected_move.expected_move_dollar,
    )

    # Determine Risk Rating
    fail_count = sum(1 for item in checklist if item.status == CheckStatus.FAIL)
    warn_count = sum(1 for item in checklist if item.status == CheckStatus.WARNING)

    if fail_count >= 2:
        risk_rating = RiskRating.EXTREME
    elif fail_count == 1:
        risk_rating = RiskRating.HIGH
    elif warn_count >= 2:
        risk_rating = RiskRating.HIGH
    elif warn_count == 1:
        risk_rating = RiskRating.MEDIUM
    else:
        risk_rating = RiskRating.LOW

    # Synthesize the Bear Case
    reasons = []
    if event_item.status == CheckStatus.FAIL:
        reasons.append("looming corporate event risk threatens high IV collapse")
    if liquidity_item.status != CheckStatus.PASS:
        reasons.append("sub-optimal option market depth exposes positions to slippage")
    if quote.pe_ratio and quote.pe_ratio > 35:
        reasons.append(f"rich valuation multiple ({quote.pe_ratio:.1f}x P/E) magnifies sensitivity to interest rates")
    if quote.beta and quote.beta > 1.2:
        reasons.append(f"high beta ({quote.beta:.2f}) heightens vulnerability to broader market pullbacks")

    if not reasons:
        reasons.append(f"failure to hold key support at ${stop_short:.2f} could accelerate selling toward ${stop_hard:.2f}")

    bear_case = (
        f"{quote.symbol}'s vulnerability centers on {' and '.join(reasons)}; "
        f"a macro risk-off shock or sudden liquidity freeze could push shares swiftly below support at ${stop_short:.2f}."
    )

    # Final Verdict & Subtitle
    if risk_rating in (RiskRating.HIGH, RiskRating.EXTREME):
        verdict = VerdictType.NO_GO
        if event_item.status == CheckStatus.FAIL:
            subtitle = "NO-GO (Event Risk Ahead)"
            rationale = (
                f"The risk-to-reward ratio is unfavorable for initiating new positions due to imminent binary event risk. "
                f"Implied volatility ({quant.expected_move.implied_volatility}%) carries post-announcement crush risk. "
                f"Wait until after the event before establishing directional or volatility exposure."
            )
        else:
            subtitle = "NO-GO (Defensive Stance)"
            rationale = (
                f"Risk metrics indicate elevated fragility across liquidity and market parameters. "
                f"Preserve capital and monitor for price stabilization above ${stop_short:.2f}."
            )
    elif risk_rating == RiskRating.MEDIUM:
        verdict = VerdictType.CAUTION
        subtitle = "CAUTION (Define Sizing)"
        rationale = (
            f"Conditions are moderately supportive but require disciplined risk management. "
            f"Maintain strict stop-loss adherence at ${stop_short:.2f} and cap position sizing."
        )
    else:
        verdict = VerdictType.GO
        subtitle = "GO (Favorable Setup)"
        rationale = (
            f"Clean risk checklist with verified liquidity and no proximate event traps. "
            f"Expected move range of ${quant.expected_move.range_low:.2f} - ${quant.expected_move.range_high:.2f} offers favorable asymmetric profile."
        )

    return RiskAudit(
        risk_rating=risk_rating,
        checklist=checklist,
        bear_case=bear_case,
        worst_case_option_buyer=opt_loss,
        worst_case_equity_holder=eq_loss,
        suggested_stop_short=stop_short,
        suggested_stop_hard=stop_hard,
        verdict=verdict,
        verdict_subtitle=subtitle,
        verdict_rationale=rationale,
    )
