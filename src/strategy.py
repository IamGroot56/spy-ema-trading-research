from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Signal(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    HOLD = "HOLD"


@dataclass(frozen=True)
class StrategyInput:
    price: float
    ema_fast: float
    ema_slow: float


def generate_signal(data: StrategyInput) -> Signal:
    """가격 하나와 EMA 두 개를 보고 신호 하나를 만든다."""

    long_condition = (
        data.ema_fast > data.ema_slow
        and data.price > data.ema_fast
    )

    if long_condition:
        return Signal.LONG

    short_condition = (
        data.ema_fast < data.ema_slow
        and data.price < data.ema_fast
    )

    if short_condition:
        return Signal.SHORT

    return Signal.HOLD


def add_signal_column(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """가격표의 모든 행에 LONG, SHORT, HOLD 신호를 추가한다."""

    required_columns = {
        "close",
        "ema_fast",
        "ema_slow",
    }

    missing_columns = (
        required_columns - set(data.columns)
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"Missing columns for signal calculation: {missing_text}"
        )

    result = data.copy()

    signals: list[str] = []

    for price, ema_fast, ema_slow in zip(
        result["close"],
        result["ema_fast"],
        result["ema_slow"],
    ):
        if pd.isna(ema_fast) or pd.isna(ema_slow):
            signals.append(
                Signal.HOLD.value
            )
            continue

        strategy_input = StrategyInput(
            price=float(price),
            ema_fast=float(ema_fast),
            ema_slow=float(ema_slow),
        )

        signal = generate_signal(
            strategy_input
        )

        signals.append(
            signal.value
        )

    result["signal"] = signals

    return result