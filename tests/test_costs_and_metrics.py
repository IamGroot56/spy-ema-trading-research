import pandas as pd

from src.backtester import (
    BacktestConfig,
    run_backtest,
)
from src.metrics import (
    calculate_performance_metrics,
)


def make_profitable_long_data() -> pd.DataFrame:
    return pd.DataFrame(
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
                110.0,
            ],
            "high": [
                101.0,
                106.0,
                111.0,
            ],
            "low": [
                99.0,
                99.5,
                109.0,
            ],
            "close": [
                100.0,
                105.0,
                110.0,
            ],
            "signal": [
                "LONG",
                "HOLD",
                "HOLD",
            ],
        }
    )


def test_costs_reduce_final_equity() -> None:
    data = make_profitable_long_data()

    result_without_costs = run_backtest(
        data,
        BacktestConfig(
            fee_rate_bps=0.0,
            slippage_bps=0.0,
        ),
    )

    result_with_costs = run_backtest(
        data,
        BacktestConfig(
            fee_rate_bps=5.0,
            slippage_bps=2.0,
        ),
    )

    assert (
        result_with_costs.final_equity
        <
        result_without_costs.final_equity
    )

    trade = result_with_costs.trades[0]

    assert trade.fees > 0
    assert trade.pnl < trade.gross_pnl


def test_performance_metrics() -> None:
    data = make_profitable_long_data()

    result = run_backtest(
        data,
        BacktestConfig(
            fee_rate_bps=5.0,
            slippage_bps=2.0,
        ),
    )

    metrics = calculate_performance_metrics(
        result
    )

    assert metrics.total_trades == 1
    assert metrics.winning_trades == 1
    assert metrics.losing_trades == 0

    assert metrics.win_rate_pct == 100.0
    assert metrics.total_return_pct > 0
    assert metrics.gross_profit > 0