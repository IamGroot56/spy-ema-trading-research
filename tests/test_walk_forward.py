import math

import pandas as pd
import pytest

from src.backtester import BacktestConfig
from src.walk_forward import run_walk_forward


def make_walk_forward_data(
    rows: int = 100,
) -> pd.DataFrame:
    timestamps = pd.date_range(
        start="2026-01-01",
        periods=rows,
        freq="min",
        tz="UTC",
    )

    closes = [
        100.0
        + index * 0.02
        + 2.0 * math.sin(index / 5)
        for index in range(rows)
    ]

    opens = [
        closes[0],
        *closes[:-1],
    ]

    highs = [
        max(open_price, close_price) + 0.2
        for open_price, close_price
        in zip(opens, closes)
    ]

    lows = [
        min(open_price, close_price) - 0.2
        for open_price, close_price
        in zip(opens, closes)
    ]

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * rows,
        }
    )


def test_walk_forward_creates_expected_folds() -> None:
    data = make_walk_forward_data(
        rows=100
    )

    result = run_walk_forward(
        data=data,
        fast_spans=[2],
        slow_spans=[4],
        stop_loss_pcts=[1.0],
        train_size=40,
        validation_size=20,
        step_size=20,
        minimum_trades=0,
    )

    assert len(result.folds) == 3

    assert result.folds["fold"].tolist() == [
        1,
        2,
        3,
    ]


def test_walk_forward_uses_selected_parameters() -> None:
    data = make_walk_forward_data(
        rows=100
    )

    result = run_walk_forward(
        data=data,
        fast_spans=[2],
        slow_spans=[4],
        stop_loss_pcts=[1.0],
        train_size=40,
        validation_size=20,
        step_size=20,
        minimum_trades=0,
    )

    assert set(
        result.folds["fast_span"]
    ) == {2}

    assert set(
        result.folds["slow_span"]
    ) == {4}

    assert set(
        result.folds["stop_loss_pct"]
    ) == {1.0}


def test_walk_forward_preserves_time_order() -> None:
    data = make_walk_forward_data(
        rows=100
    )

    result = run_walk_forward(
        data=data,
        fast_spans=[2],
        slow_spans=[4],
        stop_loss_pcts=[1.0],
        train_size=40,
        validation_size=20,
        step_size=20,
        minimum_trades=0,
    )

    for _, fold in result.folds.iterrows():
        assert (
            fold["train_end"]
            <
            fold["validation_start"]
        )


def test_walk_forward_returns_valid_equity() -> None:
    data = make_walk_forward_data(
        rows=100
    )

    result = run_walk_forward(
        data=data,
        fast_spans=[2, 3],
        slow_spans=[4, 6],
        stop_loss_pcts=[0.5, 1.0],
        train_size=40,
        validation_size=20,
        step_size=20,
        base_config=BacktestConfig(
            initial_equity=1000.0,
            fee_rate_bps=5.0,
            slippage_bps=2.0,
        ),
        minimum_trades=0,
    )

    assert result.initial_equity == 1000.0
    assert math.isfinite(
        result.final_equity
    )

    assert result.final_equity > 0


def test_not_enough_data_raises_error() -> None:
    data = make_walk_forward_data(
        rows=30
    )

    with pytest.raises(
        ValueError,
        match="Not enough data",
    ):
        run_walk_forward(
            data=data,
            fast_spans=[2],
            slow_spans=[4],
            stop_loss_pcts=[1.0],
            train_size=25,
            validation_size=10,
        )

        