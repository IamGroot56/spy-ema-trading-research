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