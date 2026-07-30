from dataclasses import dataclass
from typing import Literal


TradeSide = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade_pct: float = 0.25
    max_position_notional_pct: float = 10.0
    minimum_equity: float = 900.0


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    quantity: float
    risk_budget: float
    actual_risk: float
    position_notional: float
    reason: str


def evaluate_trade(
    equity: float,
    side: TradeSide,
    entry_price: float,
    stop_price: float,
    config: RiskConfig,
) -> RiskDecision:
    """거래가 안전한지 확인하고 최대 주문 수량을 계산한다."""

    if equity <= 0:
        raise ValueError("equity must be greater than 0")

    if entry_price <= 0:
        raise ValueError("entry_price must be greater than 0")

    if stop_price <= 0:
        raise ValueError("stop_price must be greater than 0")

    if side not in ("LONG", "SHORT"):
        raise ValueError("side must be LONG or SHORT")

    if not 0 < config.risk_per_trade_pct <= 100:
        raise ValueError(
            "risk_per_trade_pct must be between 0 and 100"
        )

    if not 0 < config.max_position_notional_pct <= 100:
        raise ValueError(
            "max_position_notional_pct must be between 0 and 100"
        )

    if config.minimum_equity < 0:
        raise ValueError(
            "minimum_equity cannot be negative"
        )

    if equity < config.minimum_equity:
        return RiskDecision(
            approved=False,
            quantity=0.0,
            risk_budget=0.0,
            actual_risk=0.0,
            position_notional=0.0,
            reason="Equity is below the minimum safety level.",
        )

    if side == "LONG" and stop_price >= entry_price:
        return RiskDecision(
            approved=False,
            quantity=0.0,
            risk_budget=0.0,
            actual_risk=0.0,
            position_notional=0.0,
            reason="A LONG stop price must be below entry.",
        )

    if side == "SHORT" and stop_price <= entry_price:
        return RiskDecision(
            approved=False,
            quantity=0.0,
            risk_budget=0.0,
            actual_risk=0.0,
            position_notional=0.0,
            reason="A SHORT stop price must be above entry.",
        )

    risk_budget = equity * (
        config.risk_per_trade_pct / 100
    )

    stop_distance = abs(
        entry_price - stop_price
    )

    quantity_by_risk = (
        risk_budget / stop_distance
    )

    max_position_notional = equity * (
        config.max_position_notional_pct / 100
    )

    quantity_by_position_limit = (
        max_position_notional / entry_price
    )

    quantity = min(
        quantity_by_risk,
        quantity_by_position_limit,
    )

    position_notional = (
        quantity * entry_price
    )

    actual_risk = (
        quantity * stop_distance
    )

    if quantity_by_position_limit < quantity_by_risk:
        reason = (
            "Approved, but quantity was capped "
            "by the position-size limit."
        )
    else:
        reason = (
            "Approved by the risk-per-trade limit."
        )

    return RiskDecision(
        approved=True,
        quantity=quantity,
        risk_budget=risk_budget,
        actual_risk=actual_risk,
        position_notional=position_notional,
        reason=reason,
    )