"""Load the backtest result files into DuckDB and build SQL analytics views.

The Python backtester writes its results as CSV files. This module loads
those files into a single DuckDB database so the results can be explored
with SQL (see sql/analytics_views.sql) and served to the Streamlit dashboard.
"""

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
PRICES_PATH = PROJECT_ROOT / "data" / "spy_daily.csv"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "research.duckdb"
VIEWS_SQL_PATH = PROJECT_ROOT / "sql" / "analytics_views.sql"

# Strategy name -> equity curve file written by the research scripts.
EQUITY_CURVES = {
    "Adaptive Walk-Forward": "spy_long_cash_walk_forward_equity.csv",
    "Fixed 20/75/2": "spy_fixed_20_75_2_equity.csv",
    "10% SPY Buy & Hold": "spy_10pct_buy_hold_equity.csv",
}

TABLE_FILES = {
    "parameter_sweep": "spy_long_cash_parameter_sweep.csv",
    "walk_forward_folds": "spy_long_cash_walk_forward_folds.csv",
    "oos_comparison": "spy_final_oos_comparison.csv",
}


def _sql_path(path: Path) -> str:
    """Quote a file path for use inside a SQL string literal."""

    return str(path).replace("'", "''")


def load_raw_tables(
    connection: duckdb.DuckDBPyConnection,
    results_dir: Path = RESULTS_DIR,
    prices_path: Path = PRICES_PATH,
) -> None:
    """Create the raw tables from the result CSV files."""

    curve_selects = []
    for strategy, file_name in EQUITY_CURVES.items():
        path = results_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing equity curve: {path}")
        curve_selects.append(
            f"""
            SELECT
                '{strategy.replace("'", "''")}' AS strategy,
                CAST(timestamp AS TIMESTAMPTZ) AS ts,
                CAST(equity AS DOUBLE) AS equity
            FROM read_csv_auto('{_sql_path(path)}')
            """
        )

    connection.execute(
        "CREATE OR REPLACE TABLE equity_raw AS "
        + " UNION ALL ".join(curve_selects)
    )

    for table_name, file_name in TABLE_FILES.items():
        path = results_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing result file: {path}")
        connection.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS "
            f"SELECT * FROM read_csv_auto('{_sql_path(path)}')"
        )

    # The raw price file is not committed (see .gitignore); load it when the
    # user has downloaded it with scripts/download_stock_data.py.
    if prices_path.exists():
        connection.execute(
            f"""
            CREATE OR REPLACE TABLE spy_prices AS
            SELECT
                CAST(timestamp AS TIMESTAMPTZ) AS ts,
                CAST(open AS DOUBLE) AS open,
                CAST(high AS DOUBLE) AS high,
                CAST(low AS DOUBLE) AS low,
                CAST(close AS DOUBLE) AS close,
                CAST(volume AS DOUBLE) AS volume
            FROM read_csv_auto('{_sql_path(prices_path)}')
            """
        )


def create_views(
    connection: duckdb.DuckDBPyConnection,
    views_sql_path: Path = VIEWS_SQL_PATH,
) -> None:
    """Run the analytics view definitions."""

    connection.execute(views_sql_path.read_text(encoding="utf-8"))


def build_database(
    db_path: Path | str = DEFAULT_DB_PATH,
    results_dir: Path = RESULTS_DIR,
    prices_path: Path = PRICES_PATH,
) -> duckdb.DuckDBPyConnection:
    """Build (or rebuild) the analytics database and return a connection.

    Pass ``":memory:"`` as ``db_path`` for a throwaway in-memory database.
    """

    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(db_path))
    load_raw_tables(connection, results_dir, prices_path)
    create_views(connection)
    return connection
