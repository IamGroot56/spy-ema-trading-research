import pytest

from src.features import calculate_ema
from src.strategy import (
    Signal,
    StrategyInput,
    generate_signal,
)


def test_calculate_ema_returns_float() -> None:
    prices = [
        100.0,
        101.0,
        102.0,
        103.0,
        104.0,
    ]

    result = calculate_ema(
        prices=prices,
        span=3,
    )

    assert isinstance(result, float)


def test_calculate_ema_rejects_too_little_data() -> None:
    with pytest.raises(ValueError):
        calculate_ema(
            prices=[100.0, 101.0],
            span=3,
        )


def test_long_signal() -> None:
    data = StrategyInput(
        price=110.0,
        ema_fast=108.0,
        ema_slow=105.0,
    )

    result = generate_signal(data)

    assert result == Signal.LONG


def test_short_signal() -> None:
    data = StrategyInput(
        price=90.0,
        ema_fast=92.0,
        ema_slow=95.0,
    )

    result = generate_signal(data)

    assert result == Signal.SHORT


def test_hold_signal() -> None:
    data = StrategyInput(
        price=100.0,
        ema_fast=100.0,
        ema_slow=100.0,
    )

    result = generate_signal(data)

    assert result == Signal.HOLD