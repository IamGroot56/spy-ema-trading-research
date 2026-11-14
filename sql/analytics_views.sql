-- Analytics views built on top of the raw research tables.
--
-- Raw tables (created by src/analytics_db.py):
--   equity_raw(strategy, ts, equity)        one row per strategy per trading day
--   parameter_sweep                          spy_long_cash_parameter_sweep.csv
--   walk_forward_folds                       spy_long_cash_walk_forward_folds.csv
--   oos_comparison                           spy_final_oos_comparison.csv
--   spy_prices (optional)                    data/spy_daily.csv


-- 1. Daily returns ---------------------------------------------------------
-- The first day of each curve is measured against the $1,000 starting equity,
-- which matches how src/metrics.py treats the initial equity.
CREATE OR REPLACE VIEW daily_returns AS
SELECT
    strategy,
    ts,
    CAST(ts AS DATE) AS trade_date,
    equity,
    equity
        / LAG(equity, 1, 1000.0) OVER (PARTITION BY strategy ORDER BY ts)
        - 1 AS daily_return
FROM equity_raw;


-- 2. Drawdowns -------------------------------------------------------------
-- Running peak via a window MAX; the peak starts at the initial equity.
CREATE OR REPLACE VIEW drawdowns AS
SELECT
    strategy,
    ts,
    trade_date,
    equity,
    running_peak,
    (equity - running_peak) / running_peak AS drawdown
FROM (
    SELECT
        *,
        GREATEST(
            1000.0,
            MAX(equity) OVER (
                PARTITION BY strategy
                ORDER BY ts
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS running_peak
    FROM daily_returns
);


-- 3. Strategy summary ------------------------------------------------------
-- Recomputes the headline table from the equity curves alone, so it can be
-- checked against the CSVs that the Python backtester wrote.
CREATE OR REPLACE VIEW strategy_summary AS
WITH curve AS (
    SELECT
        strategy,
        MIN(trade_date) AS start_date,
        MAX(trade_date) AS end_date,
        -- Calendar years between first and last bar, the same convention as
        -- calculate_cagr() in scripts/run_stock_walk_forward.py.
        EPOCH(MAX(ts) - MIN(ts)) / 86400.0 / 365.25 AS years,
        COUNT(*) AS trading_days,
        ARG_MAX(equity, ts) AS final_equity,
        STDDEV_SAMP(daily_return) * SQRT(252) AS annual_volatility,
        AVG(daily_return) / NULLIF(STDDEV_SAMP(daily_return), 0) * SQRT(252)
            AS sharpe_ratio
    FROM daily_returns
    GROUP BY strategy
),
dd AS (
    SELECT strategy, -MIN(drawdown) AS max_drawdown
    FROM drawdowns
    GROUP BY strategy
)
SELECT
    c.strategy,
    c.start_date,
    c.end_date,
    c.trading_days,
    c.final_equity,
    (c.final_equity / 1000.0 - 1) * 100 AS total_return_pct,
    (POWER(c.final_equity / 1000.0, 1.0 / c.years) - 1) * 100 AS cagr_pct,
    d.max_drawdown * 100 AS max_drawdown_pct,
    ((c.final_equity / 1000.0 - 1) * 100) / NULLIF(d.max_drawdown * 100, 0)
        AS return_to_mdd,
    c.annual_volatility * 100 AS annual_volatility_pct,
    c.sharpe_ratio
FROM curve c
JOIN dd d USING (strategy);


-- 4. Monthly returns -------------------------------------------------------
-- Month return = compounded daily returns inside the month.
CREATE OR REPLACE VIEW monthly_returns AS
SELECT
    strategy,
    DATE_TRUNC('month', trade_date) AS month,
    (EXP(SUM(LN(1 + daily_return))) - 1) * 100 AS return_pct,
    COUNT(*) AS trading_days
FROM daily_returns
GROUP BY strategy, DATE_TRUNC('month', trade_date);


-- 5. Yearly performance ----------------------------------------------------
CREATE OR REPLACE VIEW yearly_performance AS
WITH yearly AS (
    SELECT
        strategy,
        YEAR(trade_date) AS year,
        (EXP(SUM(LN(1 + daily_return))) - 1) * 100 AS return_pct,
        STDDEV_SAMP(daily_return) * SQRT(252) * 100 AS annual_volatility_pct
    FROM daily_returns
    GROUP BY strategy, YEAR(trade_date)
),
yearly_dd AS (
    -- Drawdown measured from the peak reached within the same calendar year.
    SELECT
        strategy,
        year,
        -MIN(equity / year_peak - 1) * 100 AS max_drawdown_pct
    FROM (
        SELECT
            strategy,
            YEAR(trade_date) AS year,
            equity,
            MAX(equity) OVER (
                PARTITION BY strategy, YEAR(trade_date)
                ORDER BY ts
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS year_peak
        FROM daily_returns
    )
    GROUP BY strategy, year
)
SELECT
    y.strategy,
    y.year,
    y.return_pct,
    d.max_drawdown_pct,
    y.annual_volatility_pct,
    y.return_pct
        - FIRST_VALUE(y.return_pct) OVER (
            PARTITION BY y.year
            ORDER BY CASE WHEN y.strategy = '10% SPY Buy & Hold' THEN 0 ELSE 1 END
        ) AS excess_vs_benchmark_pct
FROM yearly y
JOIN yearly_dd d USING (strategy, year);


-- 6. Rolling 63-day (about one quarter) volatility and return --------------
CREATE OR REPLACE VIEW rolling_quarter AS
SELECT
    strategy,
    trade_date,
    STDDEV_SAMP(daily_return) OVER w * SQRT(252) * 100 AS rolling_volatility_pct,
    (EXP(SUM(LN(1 + daily_return)) OVER w) - 1) * 100 AS rolling_return_pct,
    COUNT(*) OVER w AS window_days
FROM daily_returns
WINDOW w AS (
    PARTITION BY strategy
    ORDER BY ts
    ROWS BETWEEN 62 PRECEDING AND CURRENT ROW
);


-- 7. Parameter sweep ranking -----------------------------------------------
-- Ranks every eligible EMA/stop combination by return-to-drawdown, and also
-- keeps the best stop-loss for each EMA pair (QUALIFY filters on the window).
CREATE OR REPLACE VIEW parameter_ranking AS
SELECT
    fast_span,
    slow_span,
    stop_loss_pct,
    total_return_pct,
    maximum_drawdown_pct,
    total_return_pct / NULLIF(maximum_drawdown_pct, 0) AS return_to_mdd,
    total_trades,
    win_rate_pct,
    profit_factor,
    RANK() OVER (ORDER BY total_return_pct / NULLIF(maximum_drawdown_pct, 0) DESC)
        AS overall_rank
FROM parameter_sweep
WHERE eligible;

CREATE OR REPLACE VIEW best_stop_per_ema_pair AS
SELECT *
FROM parameter_ranking
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY fast_span, slow_span
    ORDER BY return_to_mdd DESC
) = 1;


-- 8. Walk-forward parameter stability --------------------------------------
-- Shows which parameters each fold picked and whether they changed from the
-- previous fold, which is the main reason adaptive re-optimization lagged.
CREATE OR REPLACE VIEW fold_stability AS
SELECT
    fold,
    CAST(validation_start AS DATE) AS validation_start,
    CAST(validation_end AS DATE) AS validation_end,
    fast_span,
    slow_span,
    stop_loss_pct,
    return_pct,
    maximum_drawdown_pct,
    total_trades,
    -- NULL for the first fold, which has nothing to compare against.
    CASE
        WHEN LAG(fold) OVER (ORDER BY fold) IS NULL THEN NULL
        ELSE LAG(fast_span) OVER (ORDER BY fold) <> fast_span
            OR LAG(slow_span) OVER (ORDER BY fold) <> slow_span
            OR LAG(stop_loss_pct) OVER (ORDER BY fold) <> stop_loss_pct
    END AS parameters_changed,
    (EXP(SUM(LN(1 + return_pct / 100)) OVER (ORDER BY fold)) - 1) * 100
        AS cumulative_return_pct
FROM walk_forward_folds;
