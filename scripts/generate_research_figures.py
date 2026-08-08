from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RESULTS_DIR = Path("data/results")
FIGURES_DIR = Path("figures")

ADAPTIVE_PATH = (
    RESULTS_DIR
    / "spy_long_cash_walk_forward_equity.csv"
)

FIXED_PATH = (
    RESULTS_DIR
    / "spy_fixed_20_75_2_equity.csv"
)

BENCHMARK_PATH = (
    RESULTS_DIR
    / "spy_10pct_buy_hold_equity.csv"
)

FOLDS_PATH = (
    RESULTS_DIR
    / "spy_long_cash_walk_forward_folds.csv"
)

EQUITY_OUTPUT_PATH = (
    FIGURES_DIR
    / "oos_equity_curve.png"
)

FOLD_RETURNS_OUTPUT_PATH = (
    FIGURES_DIR
    / "oos_fold_returns.png"
)


def load_equity_curve(
    path: Path,
) -> pd.DataFrame:
    data = pd.read_csv(path)

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        utc=True,
    )

    return (
        data
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


def load_folds(
    path: Path,
) -> pd.DataFrame:
    data = pd.read_csv(path)

    return (
        data
        .sort_values("fold")
        .reset_index(drop=True)
    )


def create_equity_curve_figure() -> None:
    adaptive = load_equity_curve(
        ADAPTIVE_PATH
    )

    fixed = load_equity_curve(
        FIXED_PATH
    )

    benchmark = load_equity_curve(
        BENCHMARK_PATH
    )

    plt.figure(
        figsize=(11, 6)
    )

    plt.plot(
        adaptive["timestamp"],
        adaptive["equity"],
        label="Adaptive Walk-Forward",
        linewidth=2,
    )

    plt.plot(
        fixed["timestamp"],
        fixed["equity"],
        label="Fixed EMA 20/75 + 2% Stop",
        linewidth=2,
    )

    plt.plot(
        benchmark["timestamp"],
        benchmark["equity"],
        label="10% SPY Buy & Hold",
        linewidth=2,
    )

    plt.axhline(
        y=1000,
        linestyle="--",
        linewidth=1,
        alpha=0.6,
        label="Initial Equity",
    )

    plt.title(
        "Out-of-Sample Equity Curve Comparison"
    )

    plt.xlabel("Date")
    plt.ylabel("Portfolio Equity ($)")
    plt.legend()
    plt.grid(alpha=0.25)
    plt.tight_layout()

    plt.savefig(
        EQUITY_OUTPUT_PATH,
        dpi=200,
        bbox_inches="tight",
    )

    print(
        f"Saved figure to: {EQUITY_OUTPUT_PATH}"
    )

    plt.show()


def create_fold_returns_figure() -> None:
    folds = load_folds(
        FOLDS_PATH
    )

    fold_labels = [
        f"Fold {int(fold)}"
        for fold in folds["fold"]
    ]

    returns = folds["return_pct"]

    plt.figure(
        figsize=(10, 6)
    )

    bars = plt.bar(
        fold_labels,
        returns,
    )

    plt.axhline(
        y=0,
        linestyle="--",
        linewidth=1,
        alpha=0.7,
    )

    plt.title(
        "Out-of-Sample Return by Walk-Forward Fold"
    )

    plt.xlabel("Fold")
    plt.ylabel("Return (%)")
    plt.grid(
        axis="y",
        alpha=0.25,
    )

    for bar, value in zip(
        bars,
        returns,
    ):
        x = (
            bar.get_x()
            + bar.get_width() / 2
        )

        y = bar.get_height()

        if y >= 0:
            va = "bottom"
            offset = 0.05
        else:
            va = "top"
            offset = -0.05

        plt.text(
            x,
            y + offset,
            f"{value:.2f}%",
            ha="center",
            va=va,
        )

    plt.tight_layout()

    plt.savefig(
        FOLD_RETURNS_OUTPUT_PATH,
        dpi=200,
        bbox_inches="tight",
    )

    print(
        f"Saved figure to: {FOLD_RETURNS_OUTPUT_PATH}"
    )

    plt.show()


def main() -> None:
    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    create_equity_curve_figure()
    create_fold_returns_figure()


if __name__ == "__main__":
    main()