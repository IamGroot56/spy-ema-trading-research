from dataclasses import dataclass

import pandas as pd

from src.backtester import BacktestResult


@dataclass(frozen=True)
class PerformanceMetrics:
    total_return_pct: float

    total_trades: int
    winning_trades: int
    losing_trades: int

    win_rate_pct: float

    gross_profit: float
    gross_loss: float
    profit_factor: float | None

    average_trade_pnl: float
    maximum_drawdown_pct: float


def calculate_maximum_drawdown(
    initial_equity: float,
    equity_curve: pd.DataFrame,
) -> float:
    """최고점 대비 가장 크게 떨어진 비율을 계산한다."""

    equity_values = pd.Series(
        [initial_equity],
        dtype="float64",
    )

    if not equity_curve.empty:
        equity_values = pd.concat(
            [
                equity_values,
                equity_curve["equity"].astype(
                    "float64"
                ),
            ],
            ignore_index=True,
        )

    running_peak = (
        equity_values.cummax()
    )

    drawdown = (
        equity_values - running_peak
    ) / running_peak

    maximum_drawdown = (
        -drawdown.min() * 100
    )

    return float(
        maximum_drawdown
    )


def calculate_performance_metrics(
    result: BacktestResult,
) -> PerformanceMetrics:
    """백테스트 결과에서 주요 성과지표를 계산한다."""

    total_return_pct = (
        (
            result.final_equity
            / result.initial_equity
        )
        - 1
    ) * 100

    trade_pnls = [
        trade.pnl
        for trade in result.trades
    ]

    winning_pnls = [
        pnl
        for pnl in trade_pnls
        if pnl > 0
    ]

    losing_pnls = [
        pnl
        for pnl in trade_pnls
        if pnl < 0
    ]

    total_trades = len(
        trade_pnls
    )

    winning_trades = len(
        winning_pnls
    )

    losing_trades = len(
        losing_pnls
    )

    if total_trades > 0:
        win_rate_pct = (
            winning_trades
            / total_trades
        ) * 100

        average_trade_pnl = (
            sum(trade_pnls)
            / total_trades
        )
    else:
        win_rate_pct = 0.0
        average_trade_pnl = 0.0

    gross_profit = sum(
        winning_pnls
    )

    gross_loss = abs(
        sum(losing_pnls)
    )

    if gross_loss > 0:
        profit_factor = (
            gross_profit / gross_loss
        )
    else:  
        profit_factor = None

    maximum_drawdown_pct = (
        calculate_maximum_drawdown(
            initial_equity=result.initial_equity,
            equity_curve=result.equity_curve,
        )
    )

    return PerformanceMetrics(
        total_return_pct=total_return_pct,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate_pct=win_rate_pct,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        average_trade_pnl=average_trade_pnl,
        maximum_drawdown_pct=maximum_drawdown_pct,
    )