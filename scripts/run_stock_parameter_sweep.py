from pathlib import Path

from src.backtester import BacktestConfig
from src.data_loader import load_price_data
from src.parameter_sweep import (
    run_parameter_sweep,
    split_time_series,
)
from src.risk_manager import RiskConfig


DATA_PATH = Path(
    "data/spy_daily.csv"
)

OUTPUT_PATH = Path(
    "data/results/"
    "spy_long_cash_parameter_sweep.csv"
)


def main() -> None:
    # ---------------------------------------------
    # 1. 실제 SPY 데이터
    # ---------------------------------------------

    full_data = load_price_data(
        DATA_PATH
    )

    print(
        f"Total rows: "
        f"{len(full_data)}"
    )

    print(
        f"Period: "
        f"{full_data['timestamp'].iloc[0]} "
        f"to "
        f"{full_data['timestamp'].iloc[-1]}"
    )

    # ---------------------------------------------
    # 2. 70% 훈련 / 30% 검증
    # ---------------------------------------------

    train_data, validation_data = (
        split_time_series(
            data=full_data,
            train_ratio=0.70,
        )
    )

    print(
        f"\nTraining rows: "
        f"{len(train_data)}"
    )

    print(
        f"Validation rows: "
        f"{len(validation_data)}"
    )

    print(
        f"Training period: "
        f"{train_data['timestamp'].iloc[0]} "
        f"to "
        f"{train_data['timestamp'].iloc[-1]}"
    )

    print(
        f"Validation period: "
        f"{validation_data['timestamp'].iloc[0]} "
        f"to "
        f"{validation_data['timestamp'].iloc[-1]}"
    )

    # ---------------------------------------------
    # 3. 거래 조건
    # ---------------------------------------------

    base_config = BacktestConfig(
        initial_equity=1000.0,
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
    # 4. Parameter Sweep
    # ---------------------------------------------

    results = run_parameter_sweep(
        data=train_data,

        fast_spans=[
            5,
            10,
            20,
            30,
        ],

        slow_spans=[
            40,
            50,
            75,
            100,
            150,
            200,
        ],

        stop_loss_pcts=[
            2.0,
            3.0,
            5.0,
            8.0,
            10.0,
        ],

        base_config=base_config,

        minimum_trades=5,

        strategy_mode="LONG_CASH",
    )

    # ---------------------------------------------
    # 5. 상위 결과 출력
    # ---------------------------------------------

    columns = [
        "fast_span",
        "slow_span",
        "stop_loss_pct",
        "total_return_pct",
        "maximum_drawdown_pct",
        "total_trades",
        "win_rate_pct",
        "profit_factor",
    ]

    print(
        "\n=== TOP 15 TRAINING RESULTS ==="
    )

    print(
        results[
            columns
        ].head(15).to_string(
            index=False
        )
    )

    # ---------------------------------------------
    # 6. 최고 파라미터
    # ---------------------------------------------

    eligible_results = (
        results[
            results["eligible"]
        ]
        .reset_index(drop=True)
    )

    if eligible_results.empty:
        raise RuntimeError(
            "No eligible strategy was found."
        )

    best = eligible_results.iloc[0]

    print(
        "\n=== BEST TRAINING PARAMETERS ==="
    )

    print(
        f"Fast EMA: "
        f"{int(best['fast_span'])}"
    )

    print(
        f"Slow EMA: "
        f"{int(best['slow_span'])}"
    )

    print(
        f"Stop loss: "
        f"{float(best['stop_loss_pct']):.2f}%"
    )

    print(
        f"Training return: "
        f"{float(best['total_return_pct']):.2f}%"
    )

    print(
        f"Training max drawdown: "
        f"{float(best['maximum_drawdown_pct']):.2f}%"
    )

    # ---------------------------------------------
    # 7. CSV 저장
    # ---------------------------------------------

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"\nSaved to: "
        f"{OUTPUT_PATH}"
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "We have NOT evaluated the "
        "validation period yet."
    )

    print(
        "The validation data remains untouched."
    )


if __name__ == "__main__":
    main()