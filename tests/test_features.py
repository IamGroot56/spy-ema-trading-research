import pandas as pd
import pytest

from src.features import add_ema_columns


def make_price_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [
                100.0,
                101.0,
                102.0,
                103.0,
                104.0,
                105.0,
            ]
        }
    )


def test_add_ema_columns() -> None:
    data = make_price_data()

    result = add_ema_columns(
        data=data,
        fast_span=2,
        slow_span=3,
    )

    assert "ema_fast" in result.columns
    assert "ema_slow" in result.columns

    assert result["ema_fast"].notna().sum() == 5
    assert result["ema_slow"].notna().sum() == 4


def test_original_data_is_not_changed() -> None:
    data = make_price_data()

    add_ema_columns(
        data=data,
        fast_span=2,
        slow_span=3,
    )

    assert "ema_fast" not in data.columns
    assert "ema_slow" not in data.columns


def test_fast_span_must_be_smaller() -> None:
    data = make_price_data()

    with pytest.raises(
        ValueError,
        match="fast_span must be smaller",
    ):
        add_ema_columns(
            data=data,
            fast_span=5,
            slow_span=3,
        )


def test_missing_price_column_raises_error() -> None:
    data = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0]
        }
    )

    with pytest.raises(
        ValueError,
        match="Price column was not found",
    ):
        add_ema_columns(
            data=data,
            fast_span=2,
            slow_span=3,
        )