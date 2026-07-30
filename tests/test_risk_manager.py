import pytest

from src.risk_manager import (
    RiskConfig,
    evaluate_trade,
)


def test_long_trade_is_approved() -> None:
    decision = evaluate_trade(
        equity=1000.0,
        side="LONG",
        entry_price=100.0,
        stop_price=98.0,
        config=RiskConfig(),
    )

    assert decision.approved is True
    assert decision.quantity == pytest.approx(1.0)
    assert decision.risk_budget == pytest.approx(2.5)
    assert decision.actual_risk == pytest.approx(2.0)
    assert decision.position_notional == pytest.approx(100.0)


def test_trade_is_rejected_below_minimum_equity() -> None:
    decision = evaluate_trade(
        equity=899.0,
        side="LONG",
        entry_price=100.0,
        stop_price=98.0,
        config=RiskConfig(),
    )

    assert decision.approved is False
    assert decision.quantity == 0.0


def test_long_stop_must_be_below_entry() -> None:
    decision = evaluate_trade(
        equity=1000.0,
        side="LONG",
        entry_price=100.0,
        stop_price=102.0,
        config=RiskConfig(),
    )

    assert decision.approved is False
    assert decision.quantity == 0.0


def test_short_stop_must_be_above_entry() -> None:
    decision = evaluate_trade(
        equity=1000.0,
        side="SHORT",
        entry_price=100.0,
        stop_price=98.0,
        config=RiskConfig(),
    )

    assert decision.approved is False
    assert decision.quantity == 0.0


def test_short_trade_is_approved() -> None:
    decision = evaluate_trade(
        equity=1000.0,
        side="SHORT",
        entry_price=100.0,
        stop_price=102.0,
        config=RiskConfig(),
    )

    assert decision.approved is True
    assert decision.quantity == pytest.approx(1.0)


def test_invalid_side_raises_error() -> None:
    with pytest.raises(ValueError):
        evaluate_trade(
            equity=1000.0,
            side="UP",  # type: ignore[arg-type]
            entry_price=100.0,
            stop_price=98.0,
            config=RiskConfig(),
        )


