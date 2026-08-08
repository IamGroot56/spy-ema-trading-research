from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.backtester import (
    BacktestConfig,
    run_backtest,
)
from src.data_loader import load_price_data
from src.features import add_ema_columns
from src.metrics import calculate_performance_metrics
from src.strategy import add_signal_column


DATA_PATH = Path("data/spy_daily.csv")

FAST_SPAN = 20
SLOW_SPAN = 50
STOP_LOSS_PCT = 5.0


def main() -> None:
    # 1. 실제 SPY 일봉 데이터를 읽는다.
    price_data = load_price_data(DATA_PATH)

    print(f"Loaded rows: {len(price_data)}")
    print(
        f"Data period: "
        f"{price_data['timestamp'].iloc[0]} "
        f"to {price_data['timestamp'].iloc[-1]}"
    )

    # 2. 20일 EMA와 50일 EMA를 추가한다.
    data_with_ema = add_ema_columns(
        data=price_data,
        fast_span=FAST_SPAN,
        slow_span=SLOW_SPAN,
    )

    # 3. LONG, SHORT, HOLD 신호를 만든다.
    data_with_signals = add_signal_column(
        data_with_ema
    )

    # 4. 수수료와 슬리피지를 포함해 백테스트한다.
    result = run_backtest(
        data=data_with_signals,
        config=BacktestConfig(
            initial_equity=1000.0,
            stop_loss_pct=STOP_LOSS_PCT,
            fee_rate_bps=5.0,
            slippage_bps=2.0,
        ),
    )

    # 5. 성과지표를 계산한다.
    metrics = calculate_performance_metrics(
        result
    )

    # 단순히 첫날 사고 마지막 날까지 보유한 수익률
    buy_and_hold_return_pct = (
        (
            price_data["close"].iloc[-1]
            / price_data["close"].iloc[0]
        )
        - 1
    ) * 100

    print("\n=== STRATEGY SETTINGS ===")
    print(f"Fast EMA: {FAST_SPAN}")
    print(f"Slow EMA: {SLOW_SPAN}")
    print(f"Stop loss: {STOP_LOSS_PCT:.2f}%")

    print("\n=== BACKTEST RESULT ===")
    print(
        f"Initial equity: "
        f"{result.initial_equity:.2f}"
    )
    print(
        f"Final equity: "
        f"{result.final_equity:.2f}"
    )
    print(
        f"Strategy return: "
        f"{metrics.total_return_pct:.2f}%"
    )
    print(
        f"Buy-and-hold return: "
        f"{buy_and_hold_return_pct:.2f}%"
    )
    print(
        f"Total trades: "
        f"{metrics.total_trades}"
    )
    print(
        f"Win rate: "
        f"{metrics.win_rate_pct:.2f}%"
    )
    print(
        f"Maximum drawdown: "
        f"{metrics.maximum_drawdown_pct:.2f}%"
    )
    print(
        f"Average trade PnL: "
        f"{metrics.average_trade_pnl:.4f}"
    )

    if metrics.profit_factor is None:
        profit_factor_text = "N/A"
    else:
        profit_factor_text = (
            f"{metrics.profit_factor:.2f}"
        )

    print(
        f"Profit factor: "
        f"{profit_factor_text}"
    )

    # 6. 결과를 CSV로 저장한다.
    output_directory = Path("data/results")
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    trades_data = pd.DataFrame(
        [
            asdict(trade)
            for trade in result.trades
        ]
    )

    trades_path = (
        output_directory
        / "spy_trades.csv"
    )

    equity_path = (
        output_directory
        / "spy_equity_curve.csv"
    )

    signals_path = (
        output_directory
        / "spy_signals.csv"
    )

    trades_data.to_csv(
        trades_path,
        index=False,
    )

    result.equity_curve.to_csv(
        equity_path,
        index=False,
    )

    data_with_signals.to_csv(
        signals_path,
        index=False,
    )

    print("\n=== SAVED FILES ===")
    print(trades_path)
    print(equity_path)
    print(signals_path)

    if not trades_data.empty:
        print("\nFirst five trades:")
        print(
            trades_data.head().to_string(
                index=False
            )
        )


if __name__ == "__main__":
    main()