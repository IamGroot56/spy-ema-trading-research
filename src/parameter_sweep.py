from dataclasses import replace
from itertools import product
from typing import Literal, Sequence

import pandas as pd

from src.backtester import (
    BacktestConfig,
    run_backtest,
)
from src.features import add_ema_columns
from src.metrics import calculate_performance_metrics
from src.strategy import add_signal_column


StrategyMode = Literal[
    "LONG_SHORT",
    "LONG_CASH",
]


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
}


def split_time_series(
    data: pd.DataFrame,
    train_ratio: float = 0.7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """가격 데이터를 과거 훈련 구간과 미래 검증 구간으로 나눈다."""

    if not 0 < train_ratio < 1:
        raise ValueError(
            "train_ratio must be between 0 and 1"
        )

    if len(data) < 4:
        raise ValueError(
            "At least four rows are required to split data."
        )

    if "timestamp" not in data.columns:
        raise ValueError(
            "timestamp column is required"
        )

    sorted_data = (
        data.copy()
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    split_index = int(
        len(sorted_data) * train_ratio
    )

    if split_index <= 0:
        raise ValueError(
            "Training data would be empty."
        )

    if split_index >= len(sorted_data):
        raise ValueError(
            "Validation data would be empty."
        )

    train_data = (
        sorted_data
        .iloc[:split_index]
        .copy()
        .reset_index(drop=True)
    )

    validation_data = (
        sorted_data
        .iloc[split_index:]
        .copy()
        .reset_index(drop=True)
    )

    return train_data, validation_data


def apply_strategy_mode(
    data: pd.DataFrame,
    strategy_mode: StrategyMode,
) -> pd.DataFrame:
    """
    기본 LONG/SHORT/HOLD 신호를
    원하는 전략 방식으로 변환한다.
    """

    if strategy_mode not in {
        "LONG_SHORT",
        "LONG_CASH",
    }:
        raise ValueError(
            f"Unknown strategy mode: {strategy_mode}"
        )

    result = data.copy()

    if strategy_mode == "LONG_CASH":
        result["signal"] = (
            result["signal"]
            .replace(
                {
                    "SHORT": "EXIT",
                }
            )
        )

    return result


def run_parameter_sweep(
    data: pd.DataFrame,
    fast_spans: Sequence[int],
    slow_spans: Sequence[int],
    stop_loss_pcts: Sequence[float],
    base_config: BacktestConfig | None = None,
    minimum_trades: int = 1,
    strategy_mode: StrategyMode = "LONG_SHORT",
) -> pd.DataFrame:
    """
    여러 EMA 기간과 손절률을 백테스트하고
    결과를 표로 반환한다.
    """

    missing_columns = (
        REQUIRED_COLUMNS - set(data.columns)
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"Missing columns for parameter sweep: {missing_text}"
        )

    if len(fast_spans) == 0:
        raise ValueError(
            "fast_spans cannot be empty"
        )

    if len(slow_spans) == 0:
        raise ValueError(
            "slow_spans cannot be empty"
        )

    if len(stop_loss_pcts) == 0:
        raise ValueError(
            "stop_loss_pcts cannot be empty"
        )

    if strategy_mode not in {
        "LONG_SHORT",
        "LONG_CASH",
    }:
        raise ValueError(
            f"Unknown strategy mode: {strategy_mode}"
        )

    if any(
        span <= 0
        for span in fast_spans
    ):
        raise ValueError(
            "All fast spans must be greater than 0"
        )

    if any(
        span <= 0
        for span in slow_spans
    ):
        raise ValueError(
            "All slow spans must be greater than 0"
        )

    if any(
        stop_loss_pct <= 0
        or stop_loss_pct >= 100
        for stop_loss_pct in stop_loss_pcts
    ):
        raise ValueError(
            "Stop-loss percentages must be between 0 and 100"
        )

    if minimum_trades < 0:
        raise ValueError(
            "minimum_trades cannot be negative"
        )

    if base_config is None:
        base_config = BacktestConfig()

    result_rows: list[
        dict[str, object]
    ] = []

    parameter_combinations = product(
        fast_spans,
        slow_spans,
        stop_loss_pcts,
    )

    for (
        fast_span,
        slow_span,
        stop_loss_pct,
    ) in parameter_combinations:

        # 빠른 EMA가 느린 EMA보다
        # 짧아야 한다.
        if fast_span >= slow_span:
            continue

        # 느린 EMA를 계산할 만큼
        # 데이터가 없으면 건너뛴다.
        if len(data) < slow_span:
            continue

        # 1. EMA 계산
        data_with_ema = add_ema_columns(
            data=data,
            fast_span=fast_span,
            slow_span=slow_span,
        )

        # 2. 기본 LONG / SHORT / HOLD 신호
        data_with_signals = (
            add_signal_column(
                data_with_ema
            )
        )

        # 3. 전략 종류에 맞게 신호 변경
        strategy_data = apply_strategy_mode(
            data=data_with_signals,
            strategy_mode=strategy_mode,
        )

        # 4. 현재 손절률 적용
        current_config = replace(
            base_config,
            stop_loss_pct=float(
                stop_loss_pct
            ),
        )

        # 5. 백테스트
        backtest_result = run_backtest(
            data=strategy_data,
            config=current_config,
        )

        # 6. 성과지표
        metrics = (
            calculate_performance_metrics(
                backtest_result
            )
        )

        eligible = (
            metrics.total_trades
            >= minimum_trades
        )

        result_rows.append(
            {
                "strategy_mode": (
                    strategy_mode
                ),
                "fast_span": fast_span,
                "slow_span": slow_span,
                "stop_loss_pct": float(
                    stop_loss_pct
                ),
                "final_equity": (
                    backtest_result.final_equity
                ),
                "total_return_pct": (
                    metrics.total_return_pct
                ),
                "total_trades": (
                    metrics.total_trades
                ),
                "winning_trades": (
                    metrics.winning_trades
                ),
                "losing_trades": (
                    metrics.losing_trades
                ),
                "win_rate_pct": (
                    metrics.win_rate_pct
                ),
                "profit_factor": (
                    metrics.profit_factor
                ),
                "maximum_drawdown_pct": (
                    metrics.maximum_drawdown_pct
                ),
                "eligible": eligible,
            }
        )

    if not result_rows:
        raise ValueError(
            "No valid parameter combinations were tested."
        )

    results = pd.DataFrame(
        result_rows
    )

    results = results.sort_values(
        by=[
            "eligible",
            "total_return_pct",
            "maximum_drawdown_pct",
            "total_trades",
        ],
        ascending=[
            False,
            False,
            True,
            False,
        ],
    )

    return results.reset_index(
        drop=True
    )