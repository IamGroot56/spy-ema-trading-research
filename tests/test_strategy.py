import pandas as pd
import pytest

from src.features import calculate_ema
from src.strategy import (
    Signal,
    StrategyInput,
    add_signal_column,
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


def make_signal_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [
                100.0,
                101.0,
                102.0,
                99.0,
                97.0,
            ],
            "ema_fast": [
                float("nan"),
                100.5,
                101.5,
                100.0,
                98.0,
            ],
            "ema_slow": [
                float("nan"),
                float("nan"),
                101.0,
                101.0,
                99.0,
            ],
        }
    )


def test_add_signal_column() -> None:
    data = make_signal_data()

    result = add_signal_column(data)

    assert result["signal"].tolist() == [
        "HOLD",
        "HOLD",
        "LONG",
        "SHORT",
        "SHORT",
    ]


def test_add_signal_column_does_not_change_original() -> None:
    data = make_signal_data()

    add_signal_column(data)

    assert "signal" not in data.columns


def test_add_signal_column_rejects_missing_columns() -> None:
    data = pd.DataFrame(
        {
            "close": [100.0, 101.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="Missing columns for signal calculation",
    ):
        add_signal_column(data)