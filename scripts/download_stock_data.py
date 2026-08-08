from pathlib import Path

import pandas as pd
import yfinance as yf


TICKER = "SPY"
START_DATE = "2018-01-01"

OUTPUT_PATH = Path(
    "data/spy_daily.csv"
)


def main() -> None:
    """Yahoo Finance에서 일봉 데이터를 내려받아 CSV로 저장한다."""

    ticker = yf.Ticker(TICKER)

    data = ticker.history(
        start=START_DATE,
        interval="1d",
        auto_adjust=True,
        actions=False,
    )

    if data.empty:
        raise RuntimeError(
            f"No price data was returned for {TICKER}."
        )

    data = data.reset_index()

    data.columns = [
        str(column).strip().lower()
        for column in data.columns
    ]

    if "date" in data.columns:
        data = data.rename(
            columns={"date": "timestamp"}
        )
    elif "datetime" in data.columns:
        data = data.rename(
            columns={"datetime": "timestamp"}
        )

    required_columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise RuntimeError(
            "Downloaded data is missing columns: "
            + ", ".join(missing_columns)
        )

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        utc=True,
    )

    data = data[required_columns]

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"Downloaded {len(data)} rows "
        f"for {TICKER}."
    )

    print(
        f"Saved to: {OUTPUT_PATH}"
    )

    print("\nFirst five rows:")
    print(data.head())

    print("\nLast five rows:")
    print(data.tail())


if __name__ == "__main__":
    main()