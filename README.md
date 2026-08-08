# SPY EMA Trend-Following Research

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Research](https://img.shields.io/badge/focus-systematic%20trading-orange)
![Status](https://img.shields.io/badge/status-V1%20complete-brightgreen)

A systematic trading research project that evaluates an EMA-based trend-following strategy on SPY using risk-based position sizing, realistic trading costs, parameter sweeps, chronological validation, and walk-forward testing.

The purpose of this project was not to maximize historical backtest returns.

Instead, the primary research question was:

> **Can an EMA-based market-timing strategy improve risk-adjusted performance relative to an equal-exposure SPY buy-and-hold benchmark?**

The final result was mixed.

The EMA strategies successfully reduced drawdowns, but they sacrificed enough upside that a simple equal-exposure SPY buy-and-hold benchmark remained superior in both absolute return and return-to-drawdown performance.

---

# Results at a Glance

Primary out-of-sample evaluation period:

**December 23, 2020 – December 15, 2025**

| Strategy | OOS Return | CAGR | Max Drawdown | Return / MDD | Trades |
|---|---:|---:|---:|---:|---:|
| Adaptive Walk-Forward | 4.67% | 0.92% | **1.92%** | 2.43 | 21 |
| Fixed EMA 20/75 + 2% Stop | 6.18% | 1.21% | 2.21% | 2.80 | 11 |
| 10% SPY Buy & Hold | **9.72%** | **1.88%** | 3.12% | **3.11** | 1 |

### Key Finding

> **EMA timing reduced portfolio drawdown, but the reduction in market exposure sacrificed enough upside that the equal-exposure SPY buy-and-hold benchmark retained superior absolute and return-to-drawdown performance.**

Another important result was that the simpler **fixed EMA 20/75 strategy outperformed the adaptive walk-forward parameter-selection approach**.

This suggests that repeatedly selecting the best recent parameters did not add value in this experiment and may have introduced additional sensitivity to market noise.

---

# Out-of-Sample Equity Curve

![Out-of-Sample Equity Curve](figures/oos_equity_curve.png)

The figure compares three approaches using the same initial portfolio equity:

- Adaptive walk-forward EMA strategy
- Fixed EMA 20/75 + 2% stop-loss strategy
- 10% SPY buy-and-hold benchmark

The EMA strategies generally maintained lower drawdowns, while the passive benchmark captured significantly more of SPY's upside.

---

# Walk-Forward Fold Performance

![Walk-Forward Fold Returns](figures/oos_fold_returns.png)

The adaptive strategy generated positive out-of-sample returns in **4 of 5 folds**.

| Fold | Fast EMA | Slow EMA | Stop Loss | OOS Return |
|---:|---:|---:|---:|---:|
| 1 | 20 | 75 | 2% | +2.50% |
| 2 | 20 | 75 | 2% | -1.05% |
| 3 | 5 | 100 | 2% | +0.95% |
| 4 | 5 | 40 | 5% | +1.63% |
| 5 | 30 | 200 | 2% | +0.59% |

The first two folds selected the same EMA 20/75 configuration, but later folds selected substantially different parameter combinations.

That instability was one reason to compare adaptive optimization against a simpler fixed-parameter strategy.

---

# Project Goals

This project was designed to explore several practical quantitative-research questions:

1. Does EMA trend following work better on SPY with short exposure or with cash during bearish regimes?
2. How does risk-based position sizing affect strategy return and drawdown?
3. Can parameter optimization improve performance without overfitting?
4. Do optimized parameters continue to work on unseen future data?
5. Does adaptive walk-forward re-optimization outperform a fixed strategy?
6. Does the strategy beat a simple passive benchmark when capital exposure is matched fairly?

---

# Strategy Overview

The strategy uses two exponential moving averages:

- Fast EMA
- Slow EMA

The original version supported both long and short positions.

## Original Long + Short Logic

```text
Fast EMA > Slow EMA
AND
Price > Fast EMA
→ LONG

Fast EMA < Slow EMA
AND
Price < Fast EMA
→ SHORT

Otherwise
→ HOLD
```

However, testing showed that short exposure significantly weakened performance on SPY.

The strategy was therefore modified to a **Long + Cash** structure.

## Long + Cash Logic

```text
Bullish trend
→ LONG

Bearish trend
→ EXIT existing position
→ remain in CASH

No actionable change
→ HOLD
```

Instead of betting against SPY during bearish signals, the strategy simply exits the market and waits for the next bullish signal.

---

# Long + Short vs Long + Cash

Using the same EMA 20/50 configuration and trading assumptions:

| Strategy | Return | Max Drawdown | Trades | Win Rate | Profit Factor |
|---|---:|---:|---:|---:|---:|
| Long + Short | 3.70% | 5.07% | 36 | 33.33% | 1.41 |
| Long + Cash | **8.72%** | **3.17%** | 18 | **50.00%** | **3.57** |

Removing short positions:

- Increased return
- Reduced maximum drawdown
- Reduced trading frequency
- Increased win rate
- Increased profit factor

For SPY, the Long + Cash structure was clearly superior in this experiment.

---

# Risk Management

The backtester includes explicit risk management rather than assigning a fixed number of shares to every trade.

The primary research configuration used:

```text
Initial Equity:              $1,000
Risk Per Trade:               0.50%
Maximum Position Notional:   10.00%
Minimum Equity:             $900.00
Transaction Fee:              5 bps
Slippage:                     2 bps
```

Position size is determined by the amount of equity that may be lost if the stop-loss is reached.

For example:

```text
Account Equity = $1,000
Risk Per Trade = 0.50%
Stop Distance  = 5%
```

Maximum acceptable loss:

```text
$1,000 × 0.50%
= $5
```

A 5% stop allows approximately:

```text
$5 / 5%
= $100
```

of position notional.

That corresponds to the configured 10% maximum position size.

The position-sizing system therefore applies the smaller of:

```text
Risk-based position size
vs
Maximum position-notional limit
```

This prevents position size from increasing simply because a strategy produces a signal.

---

# Risk-Sizing Experiment

Before strategy optimization, two different risk-per-trade settings were compared.

| Configuration | Average Position | Return | Max Drawdown | Win Rate | Profit Factor |
|---|---:|---:|---:|---:|---:|
| 0.25% Risk | ~$50 | 1.89% | 2.57% | 33.33% | 1.42 |
| 0.50% Risk | ~$101 | 3.70% | 5.07% | 33.33% | 1.41 |

Doubling the risk approximately doubled both return and drawdown while leaving the underlying trade quality almost unchanged.

This demonstrated an important distinction:

> **Increasing position size can increase backtest returns without improving the underlying strategy.**

The research configuration therefore used 0.50% risk per trade with a 10% maximum position cap.

---

# Data

Historical SPY daily data is downloaded programmatically using `yfinance`.

Research period:

```text
January 2, 2018
through
August 5, 2026
```

The dataset contains:

```text
timestamp
open
high
low
close
volume
```

Price data is validated, sorted chronologically, normalized, and deduplicated before being passed into the research pipeline.

The downloaded market-data CSV is intentionally excluded from Git because it can be reproduced using the provided download script.

---

# Feature Engineering

The primary features are exponential moving averages.

For each price series:

```text
Fast EMA
Slow EMA
```

are calculated from closing prices.

The strategy initially evaluated a 20/50 EMA configuration before moving to parameter search and validation.

EMA values require historical context, so validation periods are provided with past training data for indicator warm-up without using future observations for parameter selection.

---

# Backtesting Methodology

The backtester was designed to avoid a common look-ahead error.

A signal generated from today's completed candle is not executed at today's closing price.

Instead:

```text
Day T close
→ generate signal

Day T+1 open
→ execute signal
```

This prevents the strategy from trading at a price before the information used to generate the signal would actually have been available.

The backtester supports:

- LONG positions
- SHORT positions
- EXIT signals
- HOLD signals
- Stop losses
- Risk-based position sizing
- Transaction fees
- Adverse slippage
- Trade logging
- Equity-curve generation
- One active position at a time

---

# Transaction Costs

The primary experiments include:

```text
Transaction fee = 5 basis points
Slippage        = 2 basis points
```

Slippage is applied adversely:

```text
LONG entry
→ slightly higher execution price

LONG exit
→ slightly lower execution price
```

Trading costs are applied to both strategy simulations and the passive benchmark where applicable.

---

# Parameter Search

The parameter sweep evaluated combinations of:

### Fast EMA

```text
5
10
20
30
```

### Slow EMA

```text
40
50
75
100
150
200
```

### Stop Loss

```text
2%
3%
5%
8%
10%
```

Invalid combinations where:

```text
Fast EMA >= Slow EMA
```

are excluded automatically.

A minimum-trade requirement is also supported so that extremely low-sample parameter combinations can be filtered from selection.

---

# Training Parameter Sweep

The dataset was first divided chronologically into approximately:

```text
70% Training
30% Validation
```

Training period:

```text
January 2, 2018
through
January 3, 2024
```

Validation period:

```text
January 4, 2024
through
August 5, 2026
```

The best training candidate was:

```text
Fast EMA:    20
Slow EMA:    75
Stop Loss:   2%
Strategy:    LONG + CASH
```

Training performance:

```text
Return:            +7.29%
Maximum Drawdown:   2.43%
Trades:               11
Profit Factor:       6.87
```

These numbers were **not treated as final strategy performance** because they came from the same data used to select the parameters.

The training sweep was used only to select a candidate for future validation.

---

# Initial Out-of-Sample Validation

The frozen EMA 20/75 + 2% stop-loss configuration was evaluated on the future validation period without selecting new parameters from that data.

Validation result:

```text
Initial Equity:     $1,000.00
Final Equity:       $1,045.09

Return:                4.51%
Maximum Drawdown:      1.17%
Trades:                   4
Win Rate:              75.00%
Profit Factor:         21.81
```

Although the strategy remained profitable, only four trades occurred.

Metrics such as:

```text
75% win rate
21.81 profit factor
```

therefore have very low statistical reliability.

This small sample motivated the use of walk-forward evaluation rather than relying only on a single train/validation split.

---

# Walk-Forward Validation

Walk-forward validation repeatedly performs the following process:

```text
Historical Training Window
        ↓
Parameter Sweep
        ↓
Select Best Parameters
        ↓
Freeze Parameters
        ↓
Test on Next Unseen Period
        ↓
Move Forward in Time
        ↓
Repeat
```

The configuration used:

```text
Training Window:      750 trading days
Validation Window:    250 trading days
Step Size:            250 trading days
Number of Folds:      5
Strategy Mode:        LONG_CASH
```

Each validation period is out-of-sample relative to the training window directly preceding it.

---

# Adaptive Walk-Forward Results

Out-of-sample fold results:

| Fold | Validation Period | Fast | Slow | Stop | Return |
|---:|---|---:|---:|---:|---:|
| 1 | 2020-12-23 → 2021-12-20 | 20 | 75 | 2% | +2.50% |
| 2 | 2021-12-21 → 2022-12-16 | 20 | 75 | 2% | -1.05% |
| 3 | 2022-12-19 → 2023-12-15 | 5 | 100 | 2% | +0.95% |
| 4 | 2023-12-18 → 2024-12-13 | 5 | 40 | 5% | +1.63% |
| 5 | 2024-12-16 → 2025-12-15 | 30 | 200 | 2% | +0.59% |

Summary:

```text
Initial Equity:          $1,000.00
Final Equity:            $1,046.73

Overall OOS Return:          4.67%
OOS CAGR:                    0.92%
True OOS Max Drawdown:       1.92%

Profitable Folds:             4 / 5
Losing Folds:                 1 / 5

Total OOS Trades:                21
Overall OOS Win Rate:        28.57%
Overall Profit Factor:        2.58
```

The overall equity curve was constructed by connecting all validation-period equity curves.

This is important because calculating only the worst drawdown inside each individual fold can underestimate drawdown that spans fold boundaries.

---

# Fixed vs Adaptive Parameters

One of the most important findings from the project was that adaptive parameter optimization did **not** outperform a simple fixed strategy.

The EMA 20/75 + 2% stop configuration was selected from the initial historical training period and then kept unchanged through the same primary out-of-sample period.

| Strategy | Return | CAGR | Max Drawdown | Return / MDD |
|---|---:|---:|---:|---:|
| Adaptive Walk-Forward | 4.67% | 0.92% | **1.92%** | 2.43 |
| Fixed EMA 20/75 + 2% Stop | **6.18%** | **1.21%** | 2.21% | **2.80** |

Adaptive optimization reduced drawdown slightly:

```text
1.92%
vs
2.21%
```

but the fixed strategy achieved substantially higher return and a stronger return-to-drawdown ratio.

The later walk-forward folds also selected very different EMA combinations:

```text
20 / 75
20 / 75
5 / 100
5 / 40
30 / 200
```

This parameter instability suggests that repeated optimization may have been reacting to recent market noise rather than identifying a stable relationship.

---

# Equal-Exposure Benchmark

Comparing the trading strategy directly against a 100%-invested SPY portfolio would not be fair because the strategy limits position notional to approximately 10% of account equity.

The benchmark was therefore constructed as:

```text
10% SPY
90% Cash
```

This provides approximately comparable maximum market exposure.

The benchmark also includes transaction fees and slippage for entry and exit.

Primary OOS benchmark performance:

```text
Initial Equity:       $1,000.00
Final Equity:         $1,097.20

Return:                   9.72%
CAGR:                     1.88%
Maximum Drawdown:         3.12%
Return / MDD:             3.11
```

Compared with the fixed strategy:

```text
Fixed EMA 20/75/2
Return:       6.18%
MDD:          2.21%
Return/MDD:   2.80

10% SPY Buy & Hold
Return:       9.72%
MDD:          3.12%
Return/MDD:   3.11
```

The EMA strategy successfully reduced drawdown, but the reduction in upside was too large to outperform the passive benchmark on a return-to-drawdown basis.

---

# Final OOS Comparison

| Strategy | Final Equity | Return | CAGR | Max Drawdown | Return / MDD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Adaptive Walk-Forward | $1,046.73 | 4.67% | 0.92% | **1.92%** | 2.43 | 21 |
| Fixed EMA 20/75 + 2% Stop | $1,061.79 | 6.18% | 1.21% | 2.21% | 2.80 | 11 |
| 10% SPY Buy & Hold | **$1,097.20** | **9.72%** | **1.88%** | 3.12% | **3.11** | 1 |

The passive benchmark was ultimately the strongest performer.

---

# Post-Walk-Forward Tail Analysis

An additional analysis was performed on:

```text
December 16, 2025
through
August 5, 2026
```

Only the fixed EMA 20/75 + 2% strategy and the equal-exposure SPY benchmark were compared.

| Strategy | Return | CAGR | Max Drawdown | Return / MDD | Trades |
|---|---:|---:|---:|---:|---:|
| Fixed EMA 20/75 + 2% Stop | +0.70% | 1.11% | **0.51%** | 1.38 | 2 |
| 10% SPY Buy & Hold | **+1.41%** | **2.23%** | 0.91% | **1.55** | 1 |

The same general pattern remained:

```text
EMA strategy
→ lower drawdown
→ lower return

SPY benchmark
→ higher drawdown
→ higher return
→ higher Return/MDD
```

This period was previously included in an earlier validation experiment.

For that reason, it is treated as a **post-walk-forward tail analysis**, not as a fully untouched independent holdout.

---

# Research Pipeline

```text
SPY Historical Data
        |
        v
Data Cleaning / Validation
        |
        v
EMA Feature Generation
        |
        v
Signal Generation
        |
        v
Risk-Based Position Sizing
        |
        v
Backtesting
        |
        +----------------------+
        |                      |
        v                      v
Long + Short            Long + Cash
                               |
                               v
                       Parameter Sweep
                               |
                               v
                     Chronological Split
                               |
                               v
                   Out-of-Sample Validation
                               |
                               v
                    Walk-Forward Evaluation
                               |
                               v
                   Adaptive vs Fixed Test
                               |
                               v
                Equal-Exposure SPY Benchmark
                               |
                               v
                      Tail-Period Analysis
```

---

# Project Structure

```text
liquidity-agent/
│
├── src/
│   ├── backtester.py
│   ├── data_loader.py
│   ├── features.py
│   ├── metrics.py
│   ├── parameter_sweep.py
│   ├── risk_manager.py
│   ├── strategy.py
│   └── walk_forward.py
│
├── scripts/
│   ├── download_stock_data.py
│   ├── run_stock_backtest.py
│   ├── run_stock_parameter_sweep.py
│   ├── run_stock_walk_forward.py
│   ├── generate_research_figures.py
│   └── archive/
│
├── tests/
│   └── ...
│
├── data/
│   ├── spy_daily.csv
│   └── results/
│       ├── spy_final_oos_comparison.csv
│       ├── spy_long_cash_parameter_sweep.csv
│       ├── spy_long_cash_walk_forward_folds.csv
│       ├── spy_long_cash_walk_forward_summary.csv
│       ├── spy_long_cash_walk_forward_equity.csv
│       ├── spy_fixed_20_75_2_equity.csv
│       ├── spy_10pct_buy_hold_equity.csv
│       └── spy_tail_test_comparison.csv
│
├── figures/
│   ├── oos_equity_curve.png
│   └── oos_fold_returns.png
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

# Main Modules

## `data_loader.py`

Responsible for:

- Loading OHLCV CSV files
- Normalizing column names
- Parsing UTC timestamps
- Converting price columns to numeric values
- Removing invalid rows
- Sorting data chronologically
- Removing duplicate timestamps

---

## `features.py`

Responsible for feature engineering.

Current features include:

```text
Fast EMA
Slow EMA
```

---

## `strategy.py`

Generates the core market signals:

```text
LONG
SHORT
HOLD
```

The research pipeline can transform bearish `SHORT` signals into `EXIT` signals for Long + Cash experiments.

---

## `risk_manager.py`

Controls trade sizing and safety limits.

The risk manager considers:

```text
Account equity
Risk per trade
Entry price
Stop price
Maximum position notional
Minimum allowed equity
```

---

## `backtester.py`

Executes historical strategy simulations.

Major responsibilities include:

- Next-candle execution
- Long and short trades
- EXIT handling
- Stop-loss handling
- Transaction fees
- Slippage
- Position sizing
- Trade PnL
- Equity curves
- Trade records

---

## `metrics.py`

Calculates strategy-performance statistics including:

```text
Total Return
Maximum Drawdown
Total Trades
Winning Trades
Losing Trades
Win Rate
Gross Profit
Gross Loss
Profit Factor
Average Trade PnL
```

---

## `parameter_sweep.py`

Evaluates multiple combinations of:

```text
Fast EMA
Slow EMA
Stop Loss
Strategy Mode
```

and ranks eligible parameter configurations.

It supports:

```text
LONG_SHORT
LONG_CASH
```

research modes.

---

## `walk_forward.py`

Implements rolling walk-forward optimization.

For each fold:

```text
Train
→ optimize parameters
→ freeze parameters
→ validate on future data
→ carry equity forward
→ repeat
```

The module also retains:

```text
Fold results
Combined OOS equity curve
All OOS trades
```

for final performance analysis.

---

# Installation

Clone the repository:

```bash
git clone <YOUR-REPOSITORY-URL>
cd liquidity-agent
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

---

# Download Market Data

SPY historical data can be downloaded using:

```bash
python -m scripts.download_stock_data
```

The generated file is:

```text
data/spy_daily.csv
```

The downloaded dataset is excluded from Git because it can be reproduced programmatically.

---

# Run Tests

Run the complete test suite:

```bash
python -m pytest -q
```

The tests cover major research components including:

- Data loading
- EMA calculation
- Signal generation
- Risk management
- Backtesting
- Trading costs
- Performance metrics
- Parameter sweep
- Walk-forward evaluation
- EXIT behavior

---

# Run the Baseline Backtest

```bash
python -m scripts.run_stock_backtest
```

This runs the primary SPY strategy backtest using the default research configuration.

---

# Run the Parameter Sweep

```bash
python -m scripts.run_stock_parameter_sweep
```

This performs parameter optimization using only the designated training period.

Results are written to:

```text
data/results/spy_long_cash_parameter_sweep.csv
```

---

# Run Walk-Forward Evaluation

```bash
python -m scripts.run_stock_walk_forward
```

This produces:

- Adaptive walk-forward results
- Fixed-strategy results
- Equal-exposure SPY benchmark
- Fold statistics
- Combined OOS equity curve
- Tail-period analysis
- Final comparison CSV files

---

# Generate Research Figures

```bash
python -m scripts.generate_research_figures
```

This generates:

```text
figures/oos_equity_curve.png
figures/oos_fold_returns.png
```

These figures are used directly in this README.

---

# Reproducible Research Workflow

A typical complete research run is:

```bash
python -m scripts.download_stock_data
python -m pytest -q
python -m scripts.run_stock_backtest
python -m scripts.run_stock_parameter_sweep
python -m scripts.run_stock_walk_forward
python -m scripts.generate_research_figures
```

This reproduces the primary research pipeline from raw market data through final visualization.

---

# Backtesting Assumptions

The simulation makes several important assumptions.

### Signal Timing

Signals are calculated from completed candles.

```text
Today's close
→ signal generation

Next trading day's open
→ trade execution
```

This is intended to prevent look-ahead bias.

### Market Exposure

The strategy uses a maximum position notional of 10% of portfolio equity.

### Costs

Trading simulations include:

```text
5 bps transaction fees
2 bps adverse slippage
```

### Cash

Uninvested cash is assumed to earn:

```text
0%
```

interest.

### Position Count

Only one strategy position can be active at a time.

### Parameter Selection

During walk-forward evaluation, parameters are selected only from historical data preceding the validation period.

---

# Important Limitations

This project is a research backtester, not a production trading system.

Important limitations include:

- Only SPY is evaluated in the current V1 study.
- The dataset uses daily OHLCV candles.
- Daily candles do not reveal the exact intraday price path.
- Stop-loss execution can differ from real-world fills during price gaps.
- Short borrow fees were not modeled in the early Long + Short experiment.
- Dividend and financing effects are simplified by the selected market-data representation.
- Cash earns no interest in the current model.
- Taxes are not included.
- The number of out-of-sample trades is relatively small.
- Parameter candidates are limited to a predefined search space.
- Optimization results may be sensitive to the chosen training-window size.
- Results from SPY may not generalize to other assets.
- Historical performance does not imply future profitability.

These limitations are intentionally documented rather than hidden.

---

# What I Learned

The most important lesson from this project was that improving a backtest is not necessarily the same as improving a trading strategy.

Several experiments demonstrated this.

## 1. Position Size Is Not Alpha

Increasing risk per trade from 0.25% to 0.50% approximately doubled return and drawdown without materially changing win rate or profit factor.

The strategy had not become better.

It was simply taking more risk.

---

## 2. Market Structure Matters

Short exposure significantly hurt the EMA strategy on SPY.

Replacing bearish short positions with cash improved both return and drawdown.

This highlighted the importance of considering the long-term characteristics of the underlying asset instead of assuming symmetrical long and short behavior.

---

## 3. In-Sample Optimization Can Look Very Strong

The training parameter sweep produced high profit factors and attractive returns.

Those values were substantially stronger than later out-of-sample performance.

This reinforced why training results should not be reported as evidence of future strategy quality.

---

## 4. Out-of-Sample Testing Changed the Conclusion

The selected strategy remained profitable on future data, but its advantage was much smaller than training performance suggested.

---

## 5. Adaptive Optimization Did Not Help

Repeatedly optimizing parameters with a rolling training window produced lower returns than simply keeping EMA 20/75 fixed.

More sophisticated optimization therefore did not automatically produce a better strategy.

---

## 6. Benchmarks Are Essential

Without an equal-exposure benchmark, the EMA strategy's lower drawdown could appear more impressive than it actually was.

After comparing against:

```text
10% SPY
90% Cash
```

the passive benchmark remained superior on both:

```text
Absolute Return
Return / Maximum Drawdown
```

The strategy reduced risk, but not efficiently enough to outperform the passive alternative.

---

# Research Conclusion

The V1 research produced three major conclusions.

### 1. Long + Cash was superior to Long + Short

For SPY, avoiding bearish short exposure materially improved the EMA strategy.

### 2. Fixed parameters were superior to adaptive re-optimization

EMA 20/75 + 2% stop loss outperformed the adaptive walk-forward strategy over the primary OOS period.

### 3. Passive SPY remained the strongest benchmark

The EMA strategy reduced drawdown, but the lost upside was large enough that the equal-exposure passive benchmark retained superior overall performance.

The final conclusion is therefore:

> **The EMA timing system showed value as a drawdown-control mechanism, but V1 did not demonstrate sufficient predictive advantage to outperform a simple equal-exposure SPY buy-and-hold strategy on a return-to-drawdown basis.**

---

# Future Work

V1 is intentionally frozen at this point to avoid repeatedly tuning the same historical data.

Future research should introduce new hypotheses rather than simply expanding the EMA parameter grid.

Potential Strategy V2 experiments include:

### Market Regime Filters

- 200-day trend filter
- Long-term moving-average regime detection
- Market breadth filters

### Volatility

- ATR-based stop losses
- Volatility regime detection
- Volatility-scaled position sizing

### Portfolio Construction

- Multiple ETFs
- Multiple asset classes
- Diversified trend-following portfolio
- Risk-parity allocation

### Cash Modeling

- Treasury-bill or short-term interest yield
- Opportunity cost of cash positions

### Research Metrics

- Sharpe ratio
- Sortino ratio
- Calmar ratio
- Exposure-adjusted return
- Time-in-market
- Average holding period
- Turnover

### Robustness Testing

- Bootstrap analysis
- Monte Carlo trade sequencing
- Alternative walk-forward window sizes
- Parameter stability analysis
- Multiple-market validation

### Execution

- Paper-trading adapter
- Broker/exchange abstraction
- Real-time market-data ingestion
- Position-state persistence
- Duplicate-order protection
- Live risk checks

Any Strategy V2 experiment should be evaluated using the same disciplined research process rather than modifying the evaluation criteria after observing results.

---

# V1 Status

**V1 Research: Complete**

The current version includes:

```text
✓ Market-data pipeline
✓ Feature generation
✓ Signal generation
✓ Risk management
✓ Backtester
✓ Trading costs
✓ LONG / SHORT support
✓ LONG / CASH support
✓ Parameter sweep
✓ Chronological validation
✓ Walk-forward optimization
✓ Fixed-vs-adaptive comparison
✓ Equal-exposure benchmark
✓ Combined OOS equity analysis
✓ Research visualizations
✓ Automated tests
```

The next development phase will focus on new strategy hypotheses and eventual paper-trading infrastructure rather than further tuning the V1 EMA parameters.

---

# Disclaimer

This repository is intended for:

- Software engineering practice
- Quantitative research
- Education
- Portfolio demonstration

It is **not financial advice**.

All results shown in this repository are historical simulations.

Backtested performance does not represent live trading performance and does not guarantee future results.