from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def load_price_data(csv_path: str | Path) -> pd.DataFrame:
    """CSV 가격 데이터를 읽고 백테스트에 맞게 정리한다."""

    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(
            f"CSV file was not found: {path}"
        )

    if path.suffix.lower() != ".csv":
        raise ValueError(
            "Price data file must be a CSV file."
        )

    data = pd.read_csv(path)

    data.columns = [
        str(column).strip().lower()
        for column in data.columns
    ]

    missing_columns = (
        REQUIRED_COLUMNS - set(data.columns)
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"Missing required columns: {missing_text}"
        )

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce",
        utc=True,
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    data = data.dropna(
        subset=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    data = data[
        (data["open"] > 0)
        & (data["high"] > 0)
        & (data["low"] > 0)
        & (data["close"] > 0)
        & (data["volume"] >= 0)
    ]

    data = data.sort_values(
        by="timestamp"
    )

    data = data.drop_duplicates(
        subset="timestamp",
        keep="last",
    )

    data = data.reset_index(
        drop=True
    )

    return data