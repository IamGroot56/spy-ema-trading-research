from dataclasses import dataclass
from enum import Enum


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
    """현재 가격과 EMA를 이용해 매매 신호를 만든다."""

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