"""Build data/research.duckdb from the result CSVs and print a summary.

Usage:
    python -m scripts.build_analytics_db
"""

from src.analytics_db import DEFAULT_DB_PATH, build_database


def main() -> None:
    connection = build_database(DEFAULT_DB_PATH)

    tables = connection.sql(
        "SELECT table_name, table_type "
        "FROM information_schema.tables ORDER BY table_type, table_name"
    ).fetchall()

    print(f"Built {DEFAULT_DB_PATH}")
    for name, table_type in tables:
        print(f"  {table_type:<10} {name}")

    print()
    print(
        connection.sql(
            """
            SELECT
                strategy,
                ROUND(total_return_pct, 2) AS return_pct,
                ROUND(cagr_pct, 2) AS cagr_pct,
                ROUND(max_drawdown_pct, 2) AS mdd_pct,
                ROUND(return_to_mdd, 2) AS return_mdd,
                ROUND(sharpe_ratio, 2) AS sharpe
            FROM strategy_summary
            ORDER BY return_to_mdd DESC
            """
        )
    )

    connection.close()


if __name__ == "__main__":
    main()
