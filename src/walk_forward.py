from dataclasses import dataclass, replace
from typing import Sequence

import pandas as pd

from src.backtester import (
    BacktestConfig,
    Trade,
    run_backtest,
)
from src.features import add_ema_columns
from src.metrics import calculate_performance_metrics
from src.parameter_sweep import (
    StrategyMode,
    apply_strategy_mode,
    run_parameter_sweep,
)
from src.strategy import add_signal_column


@dataclass(frozen=True)
class WalkForwardResult:
    initial_equity: float
    final_equity: float
    folds: pd.DataFrame
    equity_curve: pd.DataFrame
    trades: list[Trade]


def run_walk_forward(
    data: pd.DataFrame,
    fast_spans: Sequence[int],
    slow_spans: Sequence[int],
    stop_loss_pcts: Sequence[float],
    train_size: int,
    validation_size: int,
    step_size: int | None = None,
    base_config: BacktestConfig | None = None,
    minimum_trades: int = 1,
    strategy_mode: StrategyMode = "LONG_SHORT",
) -> WalkForwardResult:
    """
    시간 창을 앞으로 이동시키면서
    Training 구간에서 파라미터를 선택하고
    바로 다음 Validation 구간에서 검증한다.
    """

    required_columns = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
    }

    missing_columns = (
        required_columns - set(data.columns)
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Missing columns for walk-forward test: "
            f"{missing_text}"
        )

    if train_size < 2:
        raise ValueError(
            "train_size must be at least 2"
        )

    if validation_size < 1:
        raise ValueError(
            "validation_size must be at least 1"
        )

    if step_size is None:
        step_size = validation_size

    if step_size < 1:
        raise ValueError(
            "step_size must be at least 1"
        )

    if len(data) < train_size + validation_size:
        raise ValueError(
            "Not enough data for one walk-forward fold."
        )

    if strategy_mode not in {
        "LONG_SHORT",
        "LONG_CASH",
    }:
        raise ValueError(
            f"Unknown strategy mode: {strategy_mode}"
        )

    if base_config is None:
        base_config = BacktestConfig()

    sorted_data = (
        data.copy()
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    current_equity = (
        base_config.initial_equity
    )

    fold_rows: list[
        dict[str, object]
    ] = []

    equity_curve_parts: list[pd.DataFrame] = []

    all_trades: list[Trade] = []

    window_start = 0
    fold_number = 1

    while (
        window_start
        + train_size
        + validation_size
        <= len(sorted_data)
    ):
        # -----------------------------------------
        # 1. Training / Validation 구간 결정
        # -----------------------------------------

        train_start = window_start

        train_end = (
            train_start + train_size
        )

        validation_start = train_end

        validation_end = (
            validation_start
            + validation_size
        )

        train_data = (
            sorted_data
            .iloc[
                train_start:
                train_end
            ]
            .copy()
            .reset_index(drop=True)
        )

        validation_data = (
            sorted_data
            .iloc[
                validation_start:
                validation_end
            ]
            .copy()
            .reset_index(drop=True)
        )

        # -----------------------------------------
        # 2. 현재 Fold의 Training 설정
        # -----------------------------------------

        training_config = replace(
            base_config,
            initial_equity=current_equity,
        )

        # -----------------------------------------
        # 3. Training 구간에서 Parameter Sweep
        # -----------------------------------------

        sweep_results = run_parameter_sweep(
            data=train_data,
            fast_spans=fast_spans,
            slow_spans=slow_spans,
            stop_loss_pcts=stop_loss_pcts,
            base_config=training_config,
            minimum_trades=minimum_trades,
            strategy_mode=strategy_mode,
        )

        eligible_results = (
            sweep_results[
                sweep_results["eligible"]
            ]
            .reset_index(drop=True)
        )

        if eligible_results.empty:
            raise ValueError(
                "No eligible parameter combination "
                f"was found for fold {fold_number}."
            )

        # -----------------------------------------
        # 4. Training에서 가장 좋은 파라미터 선택
        # -----------------------------------------

        best_row = (
            eligible_results.iloc[0]
        )

        best_fast_span = int(
            best_row["fast_span"]
        )

        best_slow_span = int(
            best_row["slow_span"]
        )

        best_stop_loss_pct = float(
            best_row["stop_loss_pct"]
        )

        # -----------------------------------------
        # 5. Validation용 EMA 계산
        #
        # Training 전체를 과거 context로 사용한다.
        # 미래 Validation 데이터로
        # Training 파라미터를 고르지는 않는다.
        # -----------------------------------------

        validation_with_context = (
            pd.concat(
                [
                    train_data,
                    validation_data,
                ],
                ignore_index=True,
            )
        )

        data_with_ema = (
            add_ema_columns(
                data=validation_with_context,
                fast_span=best_fast_span,
                slow_span=best_slow_span,
            )
        )

        data_with_signals = (
            add_signal_column(
                data_with_ema
            )
        )

        # LONG_CASH라면
        # SHORT 신호를 EXIT로 변환한다.
        strategy_data = (
            apply_strategy_mode(
                data=data_with_signals,
                strategy_mode=strategy_mode,
            )
        )

        # -----------------------------------------
        # 6. 마지막 Training 행부터 남긴다.
        #
        # 마지막 Training close에서 만들어진 신호를
        # Validation 첫날 open에서 실행하기 위해서다.
        # -----------------------------------------

        validation_ready_start = (
            len(train_data) - 1
        )

        validation_ready = (
            strategy_data
            .iloc[
                validation_ready_start:
            ]
            .copy()
            .reset_index(drop=True)
        )

        # -----------------------------------------
        # 7. Validation 설정
        # -----------------------------------------

        validation_config = replace(
            base_config,
            initial_equity=current_equity,
            stop_loss_pct=(
                best_stop_loss_pct
            ),
        )

        fold_start_equity = (
            current_equity
        )

        # -----------------------------------------
        # 8. 실제 Out-of-Sample Validation
        # -----------------------------------------

        validation_result = (
            run_backtest(
                data=validation_ready,
                config=validation_config,
            )
        )

        fold_equity_curve = (
            validation_result.equity_curve.copy()
        )

        fold_equity_curve["fold"] = (
            fold_number
        )

        equity_curve_parts.append(
            fold_equity_curve
        )

        all_trades.extend(
            validation_result.trades
        )

        metrics = (
            calculate_performance_metrics(
                validation_result
            )
        )

        # 이전 Fold 결과를
        # 다음 Fold의 시작 Equity로 사용한다.
        current_equity = (
            validation_result.final_equity
        )

        # -----------------------------------------
        # 9. Fold 결과 저장
        # -----------------------------------------

        fold_rows.append(
            {
                "fold": fold_number,
                "strategy_mode": (
                    strategy_mode
                ),
                "train_start": (
                    train_data.iloc[0][
                        "timestamp"
                    ]
                ),
                "train_end": (
                    train_data.iloc[-1][
                        "timestamp"
                    ]
                ),
                "validation_start": (
                    validation_data.iloc[0][
                        "timestamp"
                    ]
                ),
                "validation_end": (
                    validation_data.iloc[-1][
                        "timestamp"
                    ]
                ),
                "fast_span": (
                    best_fast_span
                ),
                "slow_span": (
                    best_slow_span
                ),
                "stop_loss_pct": (
                    best_stop_loss_pct
                ),
                "start_equity": (
                    fold_start_equity
                ),
                "final_equity": (
                    current_equity
                ),
                "return_pct": (
                    metrics.total_return_pct
                ),
                "total_trades": (
                    metrics.total_trades
                ),
                "win_rate_pct": (
                    metrics.win_rate_pct
                ),
                "maximum_drawdown_pct": (
                    metrics.maximum_drawdown_pct
                ),
                "profit_factor": (
                    metrics.profit_factor
                ),
            }
        )

        fold_number += 1
        window_start += step_size

    if not fold_rows:
        raise ValueError(
            "No walk-forward folds were completed."
        )

    combined_equity_curve = pd.concat(
        equity_curve_parts,
        ignore_index=True,
    )

    combined_equity_curve = (
        combined_equity_curve
        .sort_values("timestamp")
        .drop_duplicates(
            subset=['timestamp'],
            keep='last',
        )
        .reset_index(drop=True)
    )

    return WalkForwardResult(
        initial_equity=(
            base_config.initial_equity
        ),
        final_equity=current_equity,
        folds=pd.DataFrame(
            fold_rows
        ),
        equity_curve=(
            combined_equity_curve
        ),
        trades=all_trades,
    )