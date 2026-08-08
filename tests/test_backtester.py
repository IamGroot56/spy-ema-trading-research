import pandas as pd
import pytest

from src.backtester import (
    BacktestConfig,
    run_backtest,
)


def test_long_trade_uses_next_candle_open() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:01:00",
                    "2026-01-01 00:02:00",
                    "2026-01-01 00:03:00",
                ],
                utc=True,
            ),
            "open": [
                100.0,
                100.0,
                102.0,
                105.0,
            ],
            "high": [
                101.0,
                102.0,
                106.0,
                108.0,
            ],
            "low": [
                99.0,
                99.0,
                101.0,
                104.0,
            ],
            "close": [
                100.0,
                101.0,
                105.0,
                107.0,
            ],
            "signal": [
                "HOLD",
                "LONG",
                "HOLD",
                "HOLD",
            ],
        }
    )

    result = run_backtest(data)

    assert len(result.trades) == 1

    trade = result.trades[0]

    assert trade.entry_time == data.loc[
        2,
        "timestamp",
    ]

    assert trade.entry_price == pytest.approx(
        102.0
    )

    assert trade.exit_price == pytest.approx(
        107.0
    )

    assert trade.exit_reason == "END_OF_DATA"
    assert trade.pnl > 0
    assert result.final_equity > 1000.0


def test_long_stop_loss() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:01:00",
                    "2026-01-01 00:02:00",
                ],
                utc=True,
            ),
            "open": [
                100.0,
                100.0,
                100.0,
            ],
            "high": [
                101.0,
                101.0,
                101.0,
            ],
            "low": [
                99.0,
                99.0,
                98.0,
            ],
            "close": [
                100.0,
                100.0,
                98.5,
            ],
            "signal": [
                "HOLD",
                "LONG",
                "HOLD",
            ],
        }
    )

    result = run_backtest(
        data,
        BacktestConfig(
            stop_loss_pct=1.0,
        ),
    )

    assert len(result.trades) == 1

    trade = result.trades[0]

    assert trade.entry_price == pytest.approx(
        100.0
    )

    assert trade.exit_price == pytest.approx(
        99.0
    )

    assert trade.exit_reason == "STOP_LOSS"
    assert trade.pnl == pytest.approx(-1.0)
    assert result.final_equity == pytest.approx(
        999.0
    )


def test_missing_columns_raise_error() -> None:
    data = pd.DataFrame(
        {
            "timestamp": [
                "2026-01-01"
            ],
            "close": [
                100.0
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="Missing columns for backtest",
    ):
        run_backtest(data)

def test_exit_signal_closes_long_position() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:01:00",
                    "2026-01-01 00:02:00",
                    "2026-01-01 00:03:00",
                ],
                utc=True,
            ),
            "open": [
                100.0,
                100.0,
                105.0,
                110.0,
            ],
            "high": [
                101.0,
                106.0,
                111.0,
                112.0,
            ],
            "low": [
                99.0,
                99.5,
                104.0,
                109.0,
            ],
            "close": [
                100.0,
                105.0,
                110.0,
                111.0,
            ],
            "signal": [
                "LONG",
                "HOLD",
                "EXIT",
                "HOLD",
            ],
        }
    )

    result = run_backtest(
        data,
        BacktestConfig(
            fee_rate_bps=0.0,
            slippage_bps=0.0,
        ),
    )

    assert len(result.trades) == 1

    trade = result.trades[0]

    assert trade.entry_price == pytest.approx(
        100.0
    )

    assert trade.exit_price == pytest.approx(
        110.0
    )

    assert trade.exit_reason == "EXIT_SIGNAL"

    assert trade.pnl > 0

def test_exit_without_position_does_nothing() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:01:00",
                    "2026-01-01 00:02:00",
                ],
                utc=True,
            ),
            "open": [
                100.0,
                101.0,
                102.0,
            ],
            "high": [
                101.0,
                102.0,
                103.0,
            ],
            "low": [
                99.0,
                100.0,
                101.0,
            ],
            "close": [
                100.0,
                101.0,
                102.0,
            ],
            "signal": [
                "EXIT",
                "EXIT",
                "HOLD",
            ],
        }
    )

    result = run_backtest(data)

    assert len(result.trades) == 0

    assert result.final_equity == pytest.approx(
        1000.0
    )