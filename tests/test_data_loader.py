from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_price_data


def test_load_price_data() -> None:
    result = load_price_data(
        "data/sample_prices.csv"
    )

    assert len(result) == 5

    assert list(result.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    assert pd.api.types.is_datetime64_any_dtype(
        result["timestamp"]
    )

    assert result["timestamp"].is_monotonic_increasing


def test_missing_file_raises_error() -> None:
    with pytest.raises(FileNotFoundError):
        load_price_data(
            "data/file_that_does_not_exist.csv"
        )


def test_non_csv_file_raises_error(
    tmp_path: Path,
) -> None:
    text_file = tmp_path / "prices.txt"

    text_file.write_text(
        "not a csv file",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_price_data(text_file)


def test_missing_column_raises_error(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "bad_prices.csv"

    csv_file.write_text(
        "timestamp,close\n"
        "2026-01-01 00:00:00,100\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Missing required columns",
    ):
        load_price_data(csv_file)