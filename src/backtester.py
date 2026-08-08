from dataclasses import dataclass, field
from typing import cast

import pandas as pd

from src.risk_manager import (
    RiskConfig,
    TradeSide,
    evaluate_trade,
)


@dataclass(frozen=True)
class BacktestConfig:
    initial_equity: float = 1000.0
    stop_loss_pct: float = 1.0

    fee_rate_bps: float = 0.0
    slippage_bps: float = 0.0

    risk_config: RiskConfig = field(
        default_factory=RiskConfig
    )


@dataclass(frozen=True)
class ActivePosition:
    side: TradeSide
    entry_time: pd.Timestamp

    entry_price: float
    stop_price: float
    quantity: float

    entry_fee: float


@dataclass(frozen=True)
class Trade:
    side: TradeSide

    entry_time: pd.Timestamp
    exit_time: pd.Timestamp

    entry_price: float
    exit_price: float
    stop_price: float
    quantity: float

    gross_pnl: float
    entry_fee: float
    exit_fee: float
    fees: float
    pnl: float

    exit_reason: str


@dataclass(frozen=True)
class BacktestResult:
    initial_equity: float
    final_equity: float
    trades: list[Trade]
    equity_curve: pd.DataFrame


def bps_to_rate(bps: float) -> float:
    """Basis points를 소수 비율로 변환한다."""

    if bps < 0:
        raise ValueError(
            "bps cannot be negative"
        )

    return bps / 10_000


def calculate_fee(
    price: float,
    quantity: float,
    fee_rate_bps: float,
) -> float:
    """가격과 수량을 이용해 거래 수수료를 계산한다."""

    if price <= 0:
        raise ValueError(
            "price must be greater than 0"
        )

    if quantity <= 0:
        raise ValueError(
            "quantity must be greater than 0"
        )

    fee_rate = bps_to_rate(
        fee_rate_bps
    )

    position_notional = (
        price * quantity
    )

    return (
        position_notional * fee_rate
    )


def apply_slippage(
    side: TradeSide,
    market_price: float,
    is_entry: bool,
    slippage_bps: float,
) -> float:
    """포지션 방향과 진입·종료 여부에 따라 불리한 체결가를 계산한다."""

    if market_price <= 0:
        raise ValueError(
            "market_price must be greater than 0"
        )

    slippage_rate = bps_to_rate(
        slippage_bps
    )

    is_buy_order = (
        (side == "LONG" and is_entry)
        or
        (side == "SHORT" and not is_entry)
    )

    if is_buy_order:
        return market_price * (
            1 + slippage_rate
        )

    return market_price * (
        1 - slippage_rate
    )


def calculate_position_pnl(
    side: TradeSide,
    entry_price: float,
    exit_price: float,
    quantity: float,
) -> float:
    """수수료를 제외한 포지션 손익을 계산한다."""

    if side == "LONG":
        return (
            exit_price - entry_price
        ) * quantity

    return (
        entry_price - exit_price
    ) * quantity


def close_position(
    position: ActivePosition,
    exit_time: pd.Timestamp,
    market_exit_price: float,
    exit_reason: str,
    fee_rate_bps: float,
    slippage_bps: float,
) -> Trade:
    """포지션을 종료하고 비용까지 포함한 거래 기록을 만든다."""

    exit_price = apply_slippage(
        side=position.side,
        market_price=market_exit_price,
        is_entry=False,
        slippage_bps=slippage_bps,
    )

    gross_pnl = calculate_position_pnl(
        side=position.side,
        entry_price=position.entry_price,
        exit_price=exit_price,
        quantity=position.quantity,
    )

    exit_fee = calculate_fee(
        price=exit_price,
        quantity=position.quantity,
        fee_rate_bps=fee_rate_bps,
    )

    total_fees = (
        position.entry_fee + exit_fee
    )

    net_pnl = (
        gross_pnl - total_fees
    )

    return Trade(
        side=position.side,
        entry_time=position.entry_time,
        exit_time=exit_time,
        entry_price=position.entry_price,
        exit_price=exit_price,
        stop_price=position.stop_price,
        quantity=position.quantity,
        gross_pnl=gross_pnl,
        entry_fee=position.entry_fee,
        exit_fee=exit_fee,
        fees=total_fees,
        pnl=net_pnl,
        exit_reason=exit_reason,
    )


def run_backtest(
    data: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """신호 다음 캔들의 시가에서 거래하는 백테스트를 실행한다."""

    if config is None:
        config = BacktestConfig()

    required_columns = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "signal",
    }

    missing_columns = (
        required_columns - set(data.columns)
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"Missing columns for backtest: {missing_text}"
        )

    if len(data) < 2:
        raise ValueError(
            "Backtest requires at least two rows."
        )

    if config.initial_equity <= 0:
        raise ValueError(
            "initial_equity must be greater than 0"
        )

    if not 0 < config.stop_loss_pct < 100:
        raise ValueError(
            "stop_loss_pct must be between 0 and 100"
        )

    if config.fee_rate_bps < 0:
        raise ValueError(
            "fee_rate_bps cannot be negative"
        )

    if config.slippage_bps < 0:
        raise ValueError(
            "slippage_bps cannot be negative"
        )

    working_data = (
        data.copy()
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    realized_equity = (
        config.initial_equity
    )

    position: ActivePosition | None = None

    trades: list[Trade] = []

    equity_records: list[
        dict[str, object]
    ] = []

    for row_index in range(
        1,
        len(working_data),
    ):
        previous_row = working_data.iloc[
            row_index - 1
        ]

        current_row = working_data.iloc[
            row_index
        ]

        signal = str(
            previous_row["signal"]
        ).upper()

        if signal not in {
            "LONG",
            "SHORT",
            "HOLD",
            "EXIT",
        }:
            raise ValueError(
                f"Unknown signal: {signal}"
            )

        current_time = pd.Timestamp(
            current_row["timestamp"]
        )

        current_open = float(
            current_row["open"]
        )

        current_high = float(
            current_row["high"]
        )

        current_low = float(
            current_row["low"]
        )

        current_close = float(
            current_row["close"]
        )

        exit_signal = (
            position is not None
            and signal == "EXIT"
        )

        if exit_signal:
            trade = close_position(
                position=position,
                exit_time=current_time,
                market_exit_price=current_open,
                exit_reason="EXIT_SIGNAL",
                fee_rate_bps=config.fee_rate_bps,
                slippage_bps=config.slippage_bps,
            )

            realized_equity += trade.pnl
            trades.append(trade)

            position = None

        opposite_signal = (
            position is not None
            and (
                (
                    position.side == "LONG"
                    and signal == "SHORT"
                )
                or
                (
                    position.side == "SHORT"
                    and signal == "LONG"
                )
            )
        )

        if opposite_signal:
            trade = close_position(
                position=position,
                exit_time=current_time,
                market_exit_price=current_open,
                exit_reason="OPPOSITE_SIGNAL",
                fee_rate_bps=config.fee_rate_bps,
                slippage_bps=config.slippage_bps,
            )

            realized_equity += trade.pnl

            trades.append(trade)
            position = None

        if (
            position is None
            and signal in {"LONG", "SHORT"}
        ):
            side = cast(
                TradeSide,
                signal,
            )

            entry_price = apply_slippage(
                side=side,
                market_price=current_open,
                is_entry=True,
                slippage_bps=config.slippage_bps,
            )

            if side == "LONG":
                stop_price = entry_price * (
                    1
                    - config.stop_loss_pct / 100
                )
            else:
                stop_price = entry_price * (
                    1
                    + config.stop_loss_pct / 100
                )

            decision = evaluate_trade(
                equity=realized_equity,
                side=side,
                entry_price=entry_price,
                stop_price=stop_price,
                config=config.risk_config,
            )

            if (
                decision.approved
                and decision.quantity > 0
            ):
                entry_fee = calculate_fee(
                    price=entry_price,
                    quantity=decision.quantity,
                    fee_rate_bps=config.fee_rate_bps,
                )

                position = ActivePosition(
                    side=side,
                    entry_time=current_time,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    quantity=decision.quantity,
                    entry_fee=entry_fee,
                )

        if position is not None:
            long_stop_reached = (
                position.side == "LONG"
                and current_low
                <= position.stop_price
            )

            short_stop_reached = (
                position.side == "SHORT"
                and current_high
                >= position.stop_price
            )

            if (
                long_stop_reached
                or short_stop_reached
            ):
                trade = close_position(
                    position=position,
                    exit_time=current_time,
                    market_exit_price=position.stop_price,
                    exit_reason="STOP_LOSS",
                    fee_rate_bps=config.fee_rate_bps,
                    slippage_bps=config.slippage_bps,
                )

                realized_equity += trade.pnl

                trades.append(trade)
                position = None

        current_equity = (
            realized_equity
        )

        if position is not None:
            unrealized_pnl = (
                calculate_position_pnl(
                    side=position.side,
                    entry_price=position.entry_price,
                    exit_price=current_close,
                    quantity=position.quantity,
                )
            )

            current_equity += (
                unrealized_pnl
                - position.entry_fee
            )

        equity_records.append(
            {
                "timestamp": current_time,
                "equity": current_equity,
            }
        )

    if position is not None:
        final_row = working_data.iloc[-1]

        trade = close_position(
            position=position,
            exit_time=pd.Timestamp(
                final_row["timestamp"]
            ),
            market_exit_price=float(
                final_row["close"]
            ),
            exit_reason="END_OF_DATA",
            fee_rate_bps=config.fee_rate_bps,
            slippage_bps=config.slippage_bps,
        )

        realized_equity += trade.pnl

        trades.append(trade)

    equity_curve = pd.DataFrame(
        equity_records
    )

    if not equity_curve.empty:
        equity_curve.loc[
            equity_curve.index[-1],
            "equity",
        ] = realized_equity

    return BacktestResult(
        initial_equity=config.initial_equity,
        final_equity=realized_equity,
        trades=trades,
        equity_curve=equity_curve,
    )