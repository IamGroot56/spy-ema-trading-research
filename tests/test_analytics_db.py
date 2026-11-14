import math

import pandas as pd
import pytest

from src.analytics_db import EQUITY_CURVES, RESULTS_DIR, build_database
from src.metrics import calculate_maximum_drawdown


@pytest.fixture(scope="module")
def connection():
    con = build_database(":memory:")
    yield con
    con.close()


def test_all_views_are_created(connection) -> None:
    views = {
        row[0]
        for row in connection.sql(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_type = 'VIEW'"
        ).fetchall()
    }

    assert {
        "daily_returns",
        "drawdowns",
        "strategy_summary",
        "monthly_returns",
        "yearly_performance",
        "rolling_quarter",
        "parameter_ranking",
        "best_stop_per_ema_pair",
        "fold_stability",
    } <= views


def test_sql_summary_matches_python_backtest_outputs(connection) -> None:
    """SQL recomputation must reproduce the numbers the backtester saved."""

    sql = connection.sql(
        "SELECT * FROM strategy_summary ORDER BY strategy"
    ).df().set_index("strategy")
    saved = pd.read_csv(
        RESULTS_DIR / "spy_final_oos_comparison.csv"
    ).set_index("strategy")

    for strategy, row in saved.iterrows():
        assert sql.loc[strategy, "final_equity"] == pytest.approx(
            row["final_equity"]
        )
        assert sql.loc[strategy, "total_return_pct"] == pytest.approx(
            row["return_pct"]
        )
        assert sql.loc[strategy, "cagr_pct"] == pytest.approx(row["cagr_pct"])
        assert sql.loc[strategy, "max_drawdown_pct"] == pytest.approx(
            row["max_drawdown_pct"]
        )
        assert sql.loc[strategy, "return_to_mdd"] == pytest.approx(
            row["return_mdd"]
        )


@pytest.mark.parametrize("strategy, file_name", EQUITY_CURVES.items())
def test_sql_drawdown_matches_metrics_module(
    connection, strategy, file_name
) -> None:
    curve = pd.read_csv(RESULTS_DIR / file_name)
    expected = calculate_maximum_drawdown(1000.0, curve)

    actual = connection.execute(
        "SELECT max_drawdown_pct FROM strategy_summary WHERE strategy = ?",
        [strategy],
    ).fetchall()[0][0]

    assert actual == pytest.approx(expected)


def test_monthly_returns_compound_to_total_return(connection) -> None:
    rows = connection.sql(
        """
        SELECT
            m.strategy,
            EXP(SUM(LN(1 + m.return_pct / 100))) - 1 AS compounded,
            ANY_VALUE(s.total_return_pct) / 100 AS total
        FROM monthly_returns m
        JOIN strategy_summary s USING (strategy)
        GROUP BY m.strategy
        """
    ).fetchall()

    assert len(rows) == len(EQUITY_CURVES)
    for _, compounded, total in rows:
        assert compounded == pytest.approx(total)


def test_yearly_returns_compound_to_total_return(connection) -> None:
    rows = connection.sql(
        """
        SELECT
            strategy,
            EXP(SUM(LN(1 + return_pct / 100))) - 1 AS compounded
        FROM yearly_performance
        GROUP BY strategy
        """
    ).fetchall()
    totals = dict(
        connection.sql(
            "SELECT strategy, total_return_pct / 100 FROM strategy_summary"
        ).fetchall()
    )

    for strategy, compounded in rows:
        assert compounded == pytest.approx(totals[strategy])


def test_benchmark_has_zero_excess_return(connection) -> None:
    excess = connection.sql(
        "SELECT MAX(ABS(excess_vs_benchmark_pct)) FROM yearly_performance "
        "WHERE strategy = '10% SPY Buy & Hold'"
    ).fetchall()[0][0]

    assert excess == pytest.approx(0.0, abs=1e-9)


def test_parameter_ranking_orders_by_return_to_drawdown(connection) -> None:
    ranking = connection.sql(
        "SELECT overall_rank, return_to_mdd FROM parameter_ranking "
        "ORDER BY overall_rank"
    ).df()

    assert ranking["overall_rank"].iloc[0] == 1
    assert ranking["return_to_mdd"].is_monotonic_decreasing


def test_best_stop_keeps_one_row_per_ema_pair(connection) -> None:
    counts = connection.sql(
        """
        SELECT
            (SELECT COUNT(*) FROM best_stop_per_ema_pair) AS best_rows,
            (SELECT COUNT(DISTINCT (fast_span, slow_span))
             FROM parameter_ranking) AS pairs
        """
    ).fetchall()[0]

    assert counts[0] == counts[1]


def test_fold_stability_flags_parameter_changes(connection) -> None:
    folds = connection.sql(
        "SELECT * FROM fold_stability ORDER BY fold"
    ).df()

    assert pd.isna(folds["parameters_changed"].iloc[0])

    for i in range(1, len(folds)):
        previous = folds.iloc[i - 1]
        current = folds.iloc[i]
        expected = (
            previous["fast_span"] != current["fast_span"]
            or previous["slow_span"] != current["slow_span"]
            or previous["stop_loss_pct"] != current["stop_loss_pct"]
        )
        assert bool(current["parameters_changed"]) == expected

    final = folds["cumulative_return_pct"].iloc[-1]
    summary = pd.read_csv(
        RESULTS_DIR / "spy_long_cash_walk_forward_summary.csv"
    )
    assert final == pytest.approx(summary["overall_return_pct"].iloc[0])


def test_rolling_window_is_capped_at_63_days(connection) -> None:
    max_days = connection.sql(
        "SELECT MAX(window_days) FROM rolling_quarter"
    ).fetchall()[0][0]

    assert max_days == 63


def test_missing_results_raise_clear_error(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        build_database(":memory:", results_dir=tmp_path)


def test_optional_price_file_is_loaded(tmp_path) -> None:
    prices = tmp_path / "spy_daily.csv"
    prices.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-02 05:00:00+00:00,470,472,468,471,1000\n"
        "2024-01-03 05:00:00+00:00,471,473,469,470,1200\n",
        encoding="utf-8",
    )

    con = build_database(":memory:", prices_path=prices)
    count, last_close = con.sql(
        "SELECT COUNT(*), ARG_MAX(close, ts) FROM spy_prices"
    ).fetchall()[0]
    con.close()

    assert count == 2
    assert math.isclose(last_close, 470.0)
