from typing import Sequence 
import pandas as pd 

def calculate_ema(prices: Sequence[float], span: int,) -> float: 
    """가격 목록의 가장 최근 EMA 값을 계산"""
    if span <= 0: 
        raise ValueError("span must be greater than 0")
    
    if len(prices) <= span: 
        raise ValueError(f"Not enough price data. Need at least {span} values.")
    
    series = pd.Series(prices, dtype="float64")

    ema_series = series.ewm(span=span, adjust=False,).mean()

    return float(ema_series.iloc[-1])

def add_ema_columns(
    data: pd.DataFrame,
    fast_span: int, 
    slow_span: int,
    price_column: str = "close",
) -> pd.DataFrame: 
    """가격 데이터에 빠른 EMA와 느린 EMA 열을 추가한다."""

    if fast_span <= 0: 
        raise ValueError(
            "fast_span must be greater than 0"
        )

    if slow_span <= 0: 
        raise ValueError(
            "slow_span must be greater than 0"
        )
    
    if fast_span >= slow_span: 
        raise ValueError(
            "fast_span must be smaller than slow_span"
        )
    
    if price_column not in data.columns: 
        raise ValueError(
            f"Price column was not found: {price_column}"
        )
    
    result = data.copy() 

    result['ema_fast'] = result[
        price_column
    ].ewm(
        span=fast_span, 
        adjust=False,
        min_periods=fast_span,
    ).mean()

    result['ema_slow'] = result[
        price_column
    ].ewm(
        span=slow_span,
        adjust=False,
        min_periods=slow_span,
    ).mean()

    return result 

    