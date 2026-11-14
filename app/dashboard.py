"""Streamlit dashboard for the SPY EMA research results.

Run from the project root:
    streamlit run app/dashboard.py

Every number on the page comes from a SQL view in sql/analytics_views.sql.
"""

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics_db import build_database  # noqa: E402

BENCHMARK = "10% SPY Buy & Hold"
STRATEGY_ORDER = ["Adaptive Walk-Forward", "Fixed 20/75/2", BENCHMARK]
COLORS = ["#2a6fdb", "#e07b39", "#6b7280"]

st.set_page_config(page_title="SPY EMA Research", layout="wide")


@st.cache_resource
def get_connection():
    # In-memory database rebuilt from the CSVs, so the app never goes stale.
    return build_database(":memory:")


@st.cache_data
def query(sql: str) -> pd.DataFrame:
    return get_connection().sql(sql).df()


def color_scale() -> alt.Scale:
    return alt.Scale(domain=STRATEGY_ORDER, range=COLORS)


st.title("SPY EMA Trend-Following Research")
st.caption(
    "Out-of-sample period Dec 2020 – Dec 2025 · $1,000 starting equity · "
    "all metrics computed in DuckDB SQL from the backtest outputs"
)

# Headline metrics ---------------------------------------------------------
summary = query(
    """
    SELECT * FROM strategy_summary
    ORDER BY CASE strategy
        WHEN 'Adaptive Walk-Forward' THEN 1
        WHEN 'Fixed 20/75/2' THEN 2
        ELSE 3 END
    """
)

columns = st.columns(len(summary))
for column, row in zip(columns, summary.itertuples()):
    with column:
        st.subheader(row.strategy)
        st.metric("Total return", f"{row.total_return_pct:.2f}%")
        st.metric("Max drawdown", f"{row.max_drawdown_pct:.2f}%")
        st.metric("Return / MDD", f"{row.return_to_mdd:.2f}")

with st.expander("Full summary table"):
    st.dataframe(
        summary.round(3),
        hide_index=True,
        width="stretch",
    )

selected = st.multiselect(
    "Strategies",
    STRATEGY_ORDER,
    default=STRATEGY_ORDER,
)
if not selected:
    st.info("Select at least one strategy.")
    st.stop()

selected_sql = ", ".join("'" + s.replace("'", "''") + "'" for s in selected)

# Equity and drawdown ------------------------------------------------------
curves = query(
    "SELECT strategy, trade_date, equity, drawdown * 100 AS drawdown_pct "
    "FROM drawdowns"
)
curves = curves[curves["strategy"].isin(selected)]

left, right = st.columns(2)
with left:
    st.markdown("#### Equity curve")
    st.altair_chart(
        alt.Chart(curves)
        .mark_line()
        .encode(
            x=alt.X("trade_date:T", title=None),
            y=alt.Y("equity:Q", title="Equity ($)", scale=alt.Scale(zero=False)),
            color=alt.Color("strategy:N", scale=color_scale(), title=None, legend=alt.Legend(orient="bottom")),
            tooltip=["strategy", "trade_date:T", alt.Tooltip("equity:Q", format=",.2f")],
        )
        .properties(height=320),
        width="stretch",
    )
with right:
    st.markdown("#### Drawdown from peak")
    st.altair_chart(
        alt.Chart(curves)
        .mark_line()
        .encode(
            x=alt.X("trade_date:T", title=None),
            y=alt.Y("drawdown_pct:Q", title="Drawdown (%)"),
            color=alt.Color("strategy:N", scale=color_scale(), title=None, legend=alt.Legend(orient="bottom")),
            tooltip=["strategy", "trade_date:T", alt.Tooltip("drawdown_pct:Q", format=".2f")],
        )
        .properties(height=320),
        width="stretch",
    )

# Yearly and monthly -------------------------------------------------------
st.markdown("#### Calendar-year performance")
yearly = query(
    f"SELECT * FROM yearly_performance WHERE strategy IN ({selected_sql}) "
    "ORDER BY year, strategy"
)
st.altair_chart(
    alt.Chart(yearly)
    .mark_bar()
    .encode(
        x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
        xOffset="strategy:N",
        y=alt.Y("return_pct:Q", title="Return (%)"),
        color=alt.Color("strategy:N", scale=color_scale(), title=None, legend=alt.Legend(orient="bottom")),
        tooltip=[
            "strategy",
            "year",
            alt.Tooltip("return_pct:Q", format=".2f"),
            alt.Tooltip("max_drawdown_pct:Q", format=".2f"),
            alt.Tooltip("excess_vs_benchmark_pct:Q", format=".2f"),
        ],
    )
    .properties(height=300),
    width="stretch",
)

st.markdown("#### Monthly returns")
heat_strategy = st.selectbox("Strategy", selected, key="heatmap_strategy")
monthly = query(
    "SELECT YEAR(month) AS year, MONTH(month) AS month, return_pct "
    "FROM monthly_returns WHERE strategy = '"
    + heat_strategy.replace("'", "''")
    + "'"
)
st.altair_chart(
    alt.Chart(monthly)
    .mark_rect()
    .encode(
        x=alt.X(
            "month:O",
            title="Month",
            axis=alt.Axis(labelAngle=0),
            scale=alt.Scale(paddingInner=0, paddingOuter=0),
        ),
        y=alt.Y("year:O", title=None, scale=alt.Scale(paddingInner=0, paddingOuter=0)),
        color=alt.Color(
            "return_pct:Q",
            title="Return (%)",
            scale=alt.Scale(scheme="redblue", domainMid=0),
        ),
        tooltip=["year", "month", alt.Tooltip("return_pct:Q", format=".2f")],
    )
    .properties(height=alt.Step(30)),
    width="stretch",
)

# Parameter sweep and walk-forward -----------------------------------------
left, right = st.columns(2)
with left:
    st.markdown("#### Parameter sweep: best stop-loss per EMA pair")
    best = query(
        "SELECT fast_span, slow_span, stop_loss_pct, return_to_mdd "
        "FROM best_stop_per_ema_pair"
    )
    st.altair_chart(
        alt.Chart(best)
        .mark_rect()
        .encode(
            x=alt.X("slow_span:O", title="Slow EMA", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("fast_span:O", title="Fast EMA"),
            color=alt.Color("return_to_mdd:Q", title="Return / MDD"),
            tooltip=[
                "fast_span",
                "slow_span",
                "stop_loss_pct",
                alt.Tooltip("return_to_mdd:Q", format=".2f"),
            ],
        )
        .properties(height=300),
        width="stretch",
    )
with right:
    st.markdown("#### Walk-forward folds")
    folds = query("SELECT * FROM fold_stability ORDER BY fold")
    folds["validation_start"] = pd.to_datetime(
        folds["validation_start"]
    ).dt.strftime("%Y-%m-%d")
    st.dataframe(
        folds[
            [
                "fold",
                "validation_start",
                "fast_span",
                "slow_span",
                "stop_loss_pct",
                "parameters_changed",
                "return_pct",
                "cumulative_return_pct",
            ]
        ]
        .round(2)
        .rename(
            columns={
                "validation_start": "test from",
                "fast_span": "fast",
                "slow_span": "slow",
                "stop_loss_pct": "stop %",
                "parameters_changed": "changed",
                "return_pct": "return %",
                "cumulative_return_pct": "cumulative %",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    changed = int(folds["parameters_changed"].fillna(False).sum())
    st.caption(
        f"Parameters changed in {changed} of {len(folds) - 1} re-optimizations."
    )

with st.expander("Top 10 parameter combinations (SQL)"):
    st.dataframe(
        query(
            "SELECT * FROM parameter_ranking ORDER BY overall_rank LIMIT 10"
        ).round(3),
        hide_index=True,
        width="stretch",
    )
