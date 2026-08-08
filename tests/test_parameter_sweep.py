import pandas as pd
import pytest

from src.backtester import BacktestConfig
from src.parameter_sweep import (
    run_parameter_sweep,
    split_time_series,
    apply_strategy_mode,
)


def make_market_data(
    rows: int = 40,
) -> pd.DataFrame:
    timestamps = pd.date_range(
        start="2026-01-01",
        periods=rows,
        freq="min",
        tz="UTC",
    )

    closes: list[float] = []

    for index in range(rows):
        if index < rows // 2:
            close = 100 + index * 0.3
        else:
            close = (
                100
                + rows // 2 * 0.3
                - (index - rows // 2) * 0.25
            )

        closes.append(
            float(close)
        )

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


def test_split_time_series_preserves_order() -> None:
    data = make_market_data(
        rows=40
    )

    train_data, validation_data = (
        split_time_series(
            data=data,
            train_ratio=0.75,
        )
    )

    assert len(train_data) == 30
    assert len(validation_data) == 10

    assert (
        train_data["timestamp"].max()
        <
        validation_data["timestamp"].min()
    )


def test_parameter_sweep_tests_all_valid_combinations() -> None:
    data = make_market_data(
        rows=40
    )

    results = run_parameter_sweep(
        data=data,
        fast_spans=[2, 3],
        slow_spans=[4],
        stop_loss_pcts=[1.0, 2.0],
        base_config=BacktestConfig(
            fee_rate_bps=5.0,
            slippage_bps=2.0,
        ),
        minimum_trades=0,
    )

    assert len(results) == 4

    assert set(
        results["fast_span"]
    ) == {2, 3}

    assert set(
        results["slow_span"]
    ) == {4}

    assert set(
        results["stop_loss_pct"]
    ) == {1.0, 2.0}


def test_parameter_sweep_returns_metrics() -> None:
    data = make_market_data(
        rows=40
    )

    results = run_parameter_sweep(
        data=data,
        fast_spans=[2],
        slow_spans=[4],
        stop_loss_pcts=[1.0],
        minimum_trades=0,
    )

    expected_columns = {
        "fast_span",
        "slow_span",
        "stop_loss_pct",
        "final_equity",
        "total_return_pct",
        "total_trades",
        "win_rate_pct",
        "profit_factor",
        "maximum_drawdown_pct",
        "eligible",
    }

    assert expected_columns.issubset(
        set(results.columns)
    )


def test_invalid_train_ratio_raises_error() -> None:
    data = make_market_data(
        rows=40
    )

    with pytest.raises(
        ValueError,
        match="train_ratio",
    ):
        split_time_series(
            data=data,
            train_ratio=1.5,
        )

def test_long_cash_replaces_short_with_exit() -> None:
    data = pd.DataFrame(
        {
            "signal": [
                "LONG",
                "SHORT",
                "HOLD",
                "SHORT",
            ]
        }
    )

    result = apply_strategy_mode(
        data=data,
        strategy_mode="LONG_CASH",
    )

    assert result["signal"].tolist() == [
        "LONG",
        "EXIT",
        "HOLD",
        "EXIT",
    ]


def test_long_short_keeps_original_signals() -> None:
    data = pd.DataFrame(
        {
            "signal": [
                "LONG",
                "SHORT",
                "HOLD",
            ]
        }
    )

    result = apply_strategy_mode(
        data=data,
        strategy_mode="LONG_SHORT",
    )

    assert result["signal"].tolist() == [
        "LONG",
        "SHORT",
        "HOLD",
    ]


def test_parameter_sweep_supports_long_cash() -> None:
    data = make_market_data(
        rows=40
    )

    results = run_parameter_sweep(
        data=data,
        fast_spans=[2],
        slow_spans=[4],
        stop_loss_pcts=[1.0],
        minimum_trades=0,
        strategy_mode="LONG_CASH",
    )

    assert len(results) == 1

    assert (
        results.iloc[0]["strategy_mode"]
        == "LONG_CASH"
    )


def test_invalid_strategy_mode_raises_error() -> None:
    data = make_market_data(
        rows=40
    )

    with pytest.raises(
        ValueError,
        match="Unknown strategy mode",
    ):
        run_parameter_sweep(
            data=data,
            fast_spans=[2],
            slow_spans=[4],
            stop_loss_pcts=[1.0],
            minimum_trades=0,
            strategy_mode="BAD_MODE",  # type: ignore[arg-type]
        )