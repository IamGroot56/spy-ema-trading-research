from pathlib import Path

import pandas as pd

from src.backtester import (
    BacktestConfig,
    apply_slippage,
    calculate_fee,
    run_backtest,
)
from src.data_loader import load_price_data
from src.features import add_ema_columns
from src.metrics import (
    calculate_maximum_drawdown,
    calculate_performance_metrics,
)
from src.parameter_sweep import apply_strategy_mode
from src.strategy import add_signal_column
from src.risk_manager import RiskConfig
from src.walk_forward import run_walk_forward

DATA_PATH = Path(
    "data/spy_daily.csv"
)

FIXED_EQUITY_OUTPUT_PATH = Path(
    "data/results/"
    "spy_fixed_20_75_2_equity.csv"
)

FOLDS_OUTPUT_PATH = Path(
    "data/results/"
    "spy_long_cash_walk_forward_folds.csv"
)

SUMMARY_OUTPUT_PATH = Path(
    "data/results/"
    "spy_long_cash_walk_forward_summary.csv"
)


INITIAL_EQUITY = 1000.0

TRAIN_SIZE = 750
VALIDATION_SIZE = 250
STEP_SIZE = 250

FIXED_FAST_SPAN = 20
FIXED_SLOW_SPAN = 75
FIXED_STOP_LOSS_PCT = 2.0

FAST_SPANS = [
    5,
    10,
    20,
    30,
]

SLOW_SPANS = [
    40,
    50,
    75,
    100,
    150,
    200,
]

STOP_LOSS_PCTS = [
    2.0,
    3.0,
    5.0,
    8.0,
    10.0,
]

MINIMUM_TRADES = 3

BENCHMARK_ALLOCATION_PCT = 10.0

def calculate_cagr(
    initial_equity: float,
    final_equity: float,
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
) -> float:
    days = (
        end_time - start_time
    ).total_seconds() / 86400

    years = days / 365.25

    if years <= 0:
        return 0.0

    return (
        (
            final_equity
            / initial_equity
        )
        ** (1 / years)
        - 1
    ) * 100


def calculate_trade_statistics(
    trades,
) -> dict[str, float | int]:
    pnl_values = [
        float(trade.pnl)
        for trade in trades
    ]

    winning = [
        pnl
        for pnl in pnl_values
        if pnl > 0
    ]

    losing = [
        pnl
        for pnl in pnl_values
        if pnl < 0
    ]

    total_trades = len(
        pnl_values
    )

    if total_trades == 0:
        win_rate_pct = 0.0
    else:
        win_rate_pct = (
            len(winning)
            / total_trades
        ) * 100

    gross_profit = sum(
        winning
    )

    gross_loss = abs(
        sum(losing)
    )

    if gross_loss == 0:
        profit_factor = float("nan")
    else:
        profit_factor = (
            gross_profit
            / gross_loss
        )

    return {
        "total_trades": (
            total_trades
        ),
        "win_rate_pct": (
            win_rate_pct
        ),
        "profit_factor": (
            profit_factor
        ),
    }


def run_buy_and_hold_benchmark(
    data: pd.DataFrame,
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
) -> dict[str, object]:
    benchmark_data = (
        data[
            (
                data["timestamp"]
                >= start_time
            )
            & (
                data["timestamp"]
                <= end_time
            )
        ]
        .copy()
        .reset_index(drop=True)
    )

    if benchmark_data.empty:
        raise ValueError(
            "Benchmark period contains no data."
        )

    allocation_rate = (
        BENCHMARK_ALLOCATION_PCT
        / 100
    )

    position_notional = (
        INITIAL_EQUITY
        * allocation_rate
    )

    first_open = float(
        benchmark_data[
            "open"
        ].iloc[0]
    )

    entry_price = apply_slippage(
        side="LONG",
        market_price=first_open,
        is_entry=True,
        slippage_bps=2.0,
    )

    quantity = (
        position_notional
        / entry_price
    )

    entry_fee = calculate_fee(
        price=entry_price,
        quantity=quantity,
        fee_rate_bps=5.0,
    )

    cash = (
        INITIAL_EQUITY
        - position_notional
        - entry_fee
    )

    equity_rows = []

    for _, row in (
        benchmark_data.iterrows()
    ):
        equity_rows.append(
            {
                "timestamp": (
                    row["timestamp"]
                ),
                "equity": (
                    cash
                    + quantity
                    * float(
                        row["close"]
                    )
                ),
            }
        )

    last_close = float(
        benchmark_data[
            "close"
        ].iloc[-1]
    )

    exit_price = apply_slippage(
        side="LONG",
        market_price=last_close,
        is_entry=False,
        slippage_bps=2.0,
    )

    exit_fee = calculate_fee(
        price=exit_price,
        quantity=quantity,
        fee_rate_bps=5.0,
    )

    final_equity = (
        cash
        + quantity * exit_price
        - exit_fee
    )

    equity_curve = pd.DataFrame(
        equity_rows
    )

    equity_curve.loc[
        equity_curve.index[-1],
        "equity",
    ] = final_equity

    return_pct = (
        (
            final_equity
            / INITIAL_EQUITY
        )
        - 1
    ) * 100

    maximum_drawdown_pct = (
        calculate_maximum_drawdown(
            initial_equity=(
                INITIAL_EQUITY
            ),
            equity_curve=(
                equity_curve
            ),
        )
    )

    cagr_pct = calculate_cagr(
        initial_equity=(
            INITIAL_EQUITY
        ),
        final_equity=(
            final_equity
        ),
        start_time=start_time,
        end_time=end_time,
    )

    return {
        "final_equity": (
            final_equity
        ),
        "return_pct": (
            return_pct
        ),
        "maximum_drawdown_pct": (
            maximum_drawdown_pct
        ),
        "cagr_pct": (
            cagr_pct
        ),
        "equity_curve": (
            equity_curve
        ),
    }

def run_fixed_long_cash(
    data: pd.DataFrame,
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
):
    """
    Walk-Forward 첫 Training window에서 선택된
    20/75/2 파라미터를 이후 전체 OOS 기간에 고정한다.
    """

    data_with_ema = add_ema_columns(
        data=data,
        fast_span=FIXED_FAST_SPAN,
        slow_span=FIXED_SLOW_SPAN,
    )

    data_with_signals = add_signal_column(
        data_with_ema
    )

    strategy_data = apply_strategy_mode(
        data=data_with_signals,
        strategy_mode="LONG_CASH",
    )

    start_matches = data.index[
        data["timestamp"] >= start_time
    ]

    end_matches = data.index[
        data["timestamp"] <= end_time
    ]

    if len(start_matches) == 0 or len(end_matches) == 0:
        raise ValueError(
            "Fixed strategy OOS period not found."
        )

    start_index = int(
        start_matches[0]
    )

    end_index = int(
        end_matches[-1]
    )

    # OOS 첫날 open에서 실행할 수 있도록
    # 바로 전날 신호를 한 행 포함한다.
    slice_start = max(
        0,
        start_index - 1,
    )

    fixed_data = (
        strategy_data
        .iloc[
            slice_start:
            end_index + 1
        ]
        .copy()
        .reset_index(drop=True)
    )

    config = BacktestConfig(
        initial_equity=INITIAL_EQUITY,
        stop_loss_pct=(
            FIXED_STOP_LOSS_PCT
        ),
        fee_rate_bps=5.0,
        slippage_bps=2.0,
        risk_config=RiskConfig(
            risk_per_trade_pct=0.50,
            max_position_notional_pct=10.0,
            minimum_equity=900.0,
        ),
    )

    result = run_backtest(
        data=fixed_data,
        config=config,
    )

    metrics = calculate_performance_metrics(
        result
    )

    return result, metrics

def main() -> None:
    # ---------------------------------------------
    # 1. 실제 SPY 데이터 불러오기
    # ---------------------------------------------

    data = load_price_data(
        DATA_PATH
    )

    print(
        "=== SPY LONG+CASH WALK-FORWARD ==="
    )

    print(
        f"Total rows: {len(data)}"
    )

    print(
        f"Full period: "
        f"{data['timestamp'].iloc[0]} "
        f"to "
        f"{data['timestamp'].iloc[-1]}"
    )

    print(
        "\n=== WALK-FORWARD SETTINGS ==="
    )

    print(
        f"Training window: "
        f"{TRAIN_SIZE} trading days"
    )

    print(
        f"Validation window: "
        f"{VALIDATION_SIZE} trading days"
    )

    print(
        f"Step size: "
        f"{STEP_SIZE} trading days"
    )

    print(
        f"Fast EMA candidates: "
        f"{FAST_SPANS}"
    )

    print(
        f"Slow EMA candidates: "
        f"{SLOW_SPANS}"
    )

    print(
        f"Stop-loss candidates: "
        f"{STOP_LOSS_PCTS}"
    )

    print(
        "Strategy mode: LONG_CASH"
    )

    # ---------------------------------------------
    # 2. 동일한 거래/위험 설정
    # ---------------------------------------------

    base_config = BacktestConfig(
        initial_equity=INITIAL_EQUITY,
        stop_loss_pct=5.0,
        fee_rate_bps=5.0,
        slippage_bps=2.0,
        risk_config=RiskConfig(
            risk_per_trade_pct=0.50,
            max_position_notional_pct=10.0,
            minimum_equity=900.0,
        ),
    )

    # ---------------------------------------------
    # 3. Walk-Forward 실행
    # ---------------------------------------------

    result = run_walk_forward(
        data=data,
        fast_spans=FAST_SPANS,
        slow_spans=SLOW_SPANS,
        stop_loss_pcts=STOP_LOSS_PCTS,
        train_size=TRAIN_SIZE,
        validation_size=VALIDATION_SIZE,
        step_size=STEP_SIZE,
        base_config=base_config,
        minimum_trades=MINIMUM_TRADES,
        strategy_mode="LONG_CASH",
    )

    folds = result.folds.copy()

    # ---------------------------------------------
    # 4. 전체 결과 계산
    # ---------------------------------------------

    overall_return_pct = (
        (
            result.final_equity
            / result.initial_equity
        )
        - 1
    ) * 100

    total_trades = int(
        folds["total_trades"].sum()
    )

    profitable_folds = int(
        (
            folds["return_pct"] > 0
        ).sum()
    )

    losing_folds = int(
        (
            folds["return_pct"] < 0
        ).sum()
    )

    flat_folds = int(
        (
            folds["return_pct"] == 0
        ).sum()
    )

    worst_fold_drawdown = float(
        folds[
            "maximum_drawdown_pct"
        ].max()
    )

    oos_start = pd.Timestamp(
    folds[
            "validation_start"
        ].iloc[0]
    )

    oos_end = pd.Timestamp(
        folds[
            "validation_end"
        ].iloc[-1]
    )

    fixed_result, fixed_metrics = (
        run_fixed_long_cash(
            data=data,
            start_time=oos_start,
            end_time=oos_end,
        )
    )

    fixed_cagr = calculate_cagr(
        initial_equity=INITIAL_EQUITY,
        final_equity=fixed_result.final_equity,
        start_time=oos_start,
        end_time=oos_end,
    )

    true_oos_drawdown = (
        calculate_maximum_drawdown(
            initial_equity=(
                result.initial_equity
            ),
            equity_curve=(
                result.equity_curve
            ),
        )
    )

    oos_cagr = calculate_cagr(
        initial_equity=(
            result.initial_equity
        ),
        final_equity=(
            result.final_equity
        ),
        start_time=oos_start,
        end_time=oos_end,
    )

    trade_stats = (
        calculate_trade_statistics(
            result.trades
        )
    )

    benchmark = (
        run_buy_and_hold_benchmark(
            data=data,
            start_time=oos_start,
            end_time=oos_end,
        )
    )

    average_fold_return = float(
        folds[
            "return_pct"
        ].mean()
    )

    comparison = pd.DataFrame(
        [
            {
                "strategy": "Adaptive Walk-Forward",
                "final_equity": result.final_equity,
                "return_pct": overall_return_pct,
                "cagr_pct": oos_cagr,
                "max_drawdown_pct": true_oos_drawdown,
                "total_trades": len(result.trades),
            },
            {
                "strategy": "Fixed 20/75/2",
                "final_equity": fixed_result.final_equity,
                "return_pct": fixed_metrics.total_return_pct,
                "cagr_pct": fixed_cagr,
                "max_drawdown_pct": (
                    fixed_metrics.maximum_drawdown_pct
                ),
                "total_trades": (
                    fixed_metrics.total_trades
                ),
            },
            {
                "strategy": "10% SPY Buy & Hold",
                "final_equity": benchmark["final_equity"],
                "return_pct": benchmark["return_pct"],
                "cagr_pct": benchmark["cagr_pct"],
                "max_drawdown_pct": (
                    benchmark[
                        "maximum_drawdown_pct"
                    ]
                ),
                "total_trades": 1,
            },
        ]
    )

    comparison["return_mdd"] = (
        comparison["return_pct"]
        / comparison["max_drawdown_pct"]
    )

    print(
        "\n=== FINAL OOS COMPARISON ==="
    )

    print(
        comparison.to_string(
            index=False
        )
    )

    # -------------------------------------------------
    # FINAL TAIL TEST
    #
    # 주의:
    # 이 기간은 과거 단일 validation 실행에서
    # 이미 한 번 확인했으므로 완전한 untouched
    # holdout은 아니다.
    # -------------------------------------------------

    tail_data = (
        data[
            data["timestamp"] > oos_end
        ]
        .copy()
        .reset_index(drop=True)
    )

    if not tail_data.empty:
        tail_start = pd.Timestamp(
            tail_data["timestamp"].iloc[0]
        )

        tail_end = pd.Timestamp(
            tail_data["timestamp"].iloc[-1]
        )

        # Fixed 20/75/2 LONG+CASH
        tail_fixed_result, tail_fixed_metrics = (
            run_fixed_long_cash(
                data=data,
                start_time=tail_start,
                end_time=tail_end,
            )
        )

        tail_fixed_cagr = calculate_cagr(
            initial_equity=INITIAL_EQUITY,
            final_equity=(
                tail_fixed_result.final_equity
            ),
            start_time=tail_start,
            end_time=tail_end,
        )

        # 같은 기간 10% SPY Buy & Hold
        tail_benchmark = (
            run_buy_and_hold_benchmark(
                data=data,
                start_time=tail_start,
                end_time=tail_end,
            )
        )

        # Return / MDD
        if (
            tail_fixed_metrics.maximum_drawdown_pct
            > 0
        ):
            tail_fixed_return_mdd = (
                tail_fixed_metrics.total_return_pct
                / tail_fixed_metrics.maximum_drawdown_pct
            )
        else:
            tail_fixed_return_mdd = float("nan")

        tail_benchmark_mdd = float(
            tail_benchmark[
                "maximum_drawdown_pct"
            ]
        )

        if tail_benchmark_mdd > 0:
            tail_benchmark_return_mdd = (
                float(
                    tail_benchmark[
                        "return_pct"
                    ]
                )
                / tail_benchmark_mdd
            )
        else:
            tail_benchmark_return_mdd = float(
                "nan"
            )

        tail_comparison = pd.DataFrame(
            [
                {
                    "strategy": (
                        "Fixed 20/75/2 LONG+CASH"
                    ),
                    "final_equity": (
                        tail_fixed_result.final_equity
                    ),
                    "return_pct": (
                        tail_fixed_metrics.total_return_pct
                    ),
                    "cagr_pct": (
                        tail_fixed_cagr
                    ),
                    "max_drawdown_pct": (
                        tail_fixed_metrics
                        .maximum_drawdown_pct
                    ),
                    "total_trades": (
                        tail_fixed_metrics.total_trades
                    ),
                    "win_rate_pct": (
                        tail_fixed_metrics.win_rate_pct
                    ),
                    "profit_factor": (
                        tail_fixed_metrics.profit_factor
                    ),
                    "return_mdd": (
                        tail_fixed_return_mdd
                    ),
                },
                {
                    "strategy": (
                        "10% SPY Buy & Hold"
                    ),
                    "final_equity": (
                        tail_benchmark[
                            "final_equity"
                        ]
                    ),
                    "return_pct": (
                        tail_benchmark[
                            "return_pct"
                        ]
                    ),
                    "cagr_pct": (
                        tail_benchmark[
                            "cagr_pct"
                        ]
                    ),
                    "max_drawdown_pct": (
                        tail_benchmark[
                            "maximum_drawdown_pct"
                        ]
                    ),
                    "total_trades": 1,
                    "win_rate_pct": float("nan"),
                    "profit_factor": float("nan"),
                    "return_mdd": (
                        tail_benchmark_return_mdd
                    ),
                },
            ]
        )

        print(
            "\n=== POST-WALK-FORWARD TAIL TEST ==="
        )

        print(
            f"Period: "
            f"{tail_start} to {tail_end}"
        )

        print(
            "\nNOTE:"
        )

        print(
            "This period was previously included "
            "in an earlier validation run, so it "
            "is not a fully untouched holdout."
        )

        print()

        print(
            tail_comparison.to_string(
                index=False
            )
        )

        tail_output_path = Path(
            "data/results/"
            "spy_tail_test_comparison.csv"
        )

        tail_comparison.to_csv(
            tail_output_path,
            index=False,
        )

        print(
            f"\nSaved tail comparison to: "
            f"{tail_output_path}"
        )

    else:
        print(
            "\nNo data exists after the final "
            "walk-forward validation period."
        )

    # ---------------------------------------------
    # 5. 각 Fold 결과 출력
    # ---------------------------------------------

    display_columns = [
        "fold",
        "validation_start",
        "validation_end",
        "fast_span",
        "slow_span",
        "stop_loss_pct",
        "start_equity",
        "final_equity",
        "return_pct",
        "total_trades",
        "win_rate_pct",
        "maximum_drawdown_pct",
        "profit_factor",
    ]

    print(
        "\n=== OUT-OF-SAMPLE FOLDS ==="
    )

    print(
        folds[
            display_columns
        ].to_string(
            index=False
        )
    )

    # ---------------------------------------------
    # 6. 최종 요약
    # ---------------------------------------------

    print(
        "\n=== WALK-FORWARD SUMMARY ==="
    )

    print(
        f"Initial equity: "
        f"${result.initial_equity:.2f}"
    )

    print(
        f"Final equity: "
        f"${result.final_equity:.2f}"
    )

    print(
        f"Overall return: "
        f"{overall_return_pct:.2f}%"
    )

    print(
        f"Number of folds: "
        f"{len(folds)}"
    )

    print(
        f"Profitable folds: "
        f"{profitable_folds}"
    )

    print(
        f"Losing folds: "
        f"{losing_folds}"
    )

    print(
        f"Flat folds: "
        f"{flat_folds}"
    )

    print(
        f"Total OOS trades: "
        f"{total_trades}"
    )

    print(
        f"Average fold return: "
        f"{average_fold_return:.2f}%"
    )

    print(
        f"Worst fold drawdown: "
        f"{worst_fold_drawdown:.2f}%"
    )


    # ---------------------------------------------
    # 7. 어떤 파라미터가 선택됐는지 확인
    # ---------------------------------------------

    print(
        "\n=== PARAMETERS SELECTED BY FOLD ==="
    )

    parameter_columns = [
        "fold",
        "fast_span",
        "slow_span",
        "stop_loss_pct",
    ]

    print(
        folds[
            parameter_columns
        ].to_string(
            index=False
        )
    )

    # ---------------------------------------------
    # 8. 결과 저장
    # ---------------------------------------------

    fixed_result.equity_curve.to_csv(
        FIXED_EQUITY_OUTPUT_PATH,
        index=False,
    )

    print(
        f"Saved fixed strategy equity curve to: "
        f"{FIXED_EQUITY_OUTPUT_PATH}"
    )

    comparison_path = Path(
        "data/results/"
        "spy_final_oos_comparison.csv"
    )

    comparison.to_csv(
        comparison_path,
        index=False,
    )

    print(
        f"\nSaved final comparison to: "
        f"{comparison_path}"
    )

    FOLDS_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    folds.to_csv(
        FOLDS_OUTPUT_PATH,
        index=False,
    )

    summary = pd.DataFrame(
        [
            {
                "initial_equity": (
                    result.initial_equity
                ),
                "final_equity": (
                    result.final_equity
                ),
                "overall_return_pct": (
                    overall_return_pct
                ),
                "number_of_folds": (
                    len(folds)
                ),
                "profitable_folds": (
                    profitable_folds
                ),
                "losing_folds": (
                    losing_folds
                ),
                "flat_folds": (
                    flat_folds
                ),
                "total_oos_trades": (
                    total_trades
                ),
                "average_fold_return_pct": (
                    average_fold_return
                ),
                "worst_fold_drawdown_pct": (
                    worst_fold_drawdown
                ),
            }
        ]
    )

    summary.to_csv(
        SUMMARY_OUTPUT_PATH,
        index=False,
    )

    print(
        f"\nSaved folds to: "
        f"{FOLDS_OUTPUT_PATH}"
    )

    print(
        f"Saved summary to: "
        f"{SUMMARY_OUTPUT_PATH}"
    )

    print(
    f"True overall OOS drawdown: "
    f"{true_oos_drawdown:.2f}%"
)

    print(
        f"OOS CAGR: "
        f"{oos_cagr:.2f}%"
    )

    print(
        f"Overall OOS win rate: "
        f"{trade_stats['win_rate_pct']:.2f}%"
    )

    profit_factor = (
        trade_stats["profit_factor"]
    )

    if pd.isna(
        profit_factor
    ):
        print(
            "Overall OOS profit factor: N/A"
        )
    else:
        print(
            f"Overall OOS profit factor: "
            f"{profit_factor:.2f}"
        )

    print(
    "\n=== SAME-PERIOD 10% SPY BENCHMARK ==="
)

    print(
        f"Period: "
        f"{oos_start} to {oos_end}"
    )

    print(
        f"Final equity: "
        f"${benchmark['final_equity']:.2f}"
    )

    print(
        f"Return: "
        f"{benchmark['return_pct']:.2f}%"
    )

    print(
        f"CAGR: "
        f"{benchmark['cagr_pct']:.2f}%"
    )

    print(
        f"Maximum drawdown: "
        f"{benchmark['maximum_drawdown_pct']:.2f}%"
    )

    if true_oos_drawdown > 0:
        strategy_return_mdd = (
            overall_return_pct
            / true_oos_drawdown
        )
    else:
        strategy_return_mdd = float(
            "nan"
        )

    benchmark_mdd = float(
        benchmark[
            "maximum_drawdown_pct"
        ]
    )

    if benchmark_mdd > 0:
        benchmark_return_mdd = (
            float(
                benchmark[
                    "return_pct"
                ]
            )
            / benchmark_mdd
        )
    else:
        benchmark_return_mdd = float(
            "nan"
        )

    print(
        "\n=== RISK / RETURN COMPARISON ==="
    )

    print(
        f"Walk-forward Return/MDD: "
        f"{strategy_return_mdd:.2f}"
    )

    print(
        f"10% SPY Return/MDD: "
        f"{benchmark_return_mdd:.2f}"
    )

    EQUITY_OUTPUT_PATH = Path(
        "data/results/"
        "spy_long_cash_walk_forward_equity.csv"
    )

    BENCHMARK_EQUITY_OUTPUT_PATH = Path(
        "data/results/"
        "spy_10pct_buy_hold_equity.csv"
    )

    result.equity_curve.to_csv(
        EQUITY_OUTPUT_PATH,
        index=False,
    )

    benchmark[
        "equity_curve"
    ].to_csv(
        BENCHMARK_EQUITY_OUTPUT_PATH,
        index=False,
    )

    print(
        f"Saved OOS equity curve to: "
        f"{EQUITY_OUTPUT_PATH}"
    )

    print(
        f"Saved benchmark equity curve to: "
        f"{BENCHMARK_EQUITY_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()