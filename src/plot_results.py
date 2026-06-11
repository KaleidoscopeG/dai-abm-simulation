"""
plot_results.py

Plotting utilities for the DAI stability simulation.

This module creates dissertation-ready figures from saved experiment outputs.

Figures:
- DAI price by scenario;
- active bad debt by scenario;
- liquidatable vaults by scenario;
- cumulative keeper profit by scenario.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "outputs" / "results"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"


def load_combined_results(
    path: Path | None = None,
) -> pd.DataFrame:
    """
    Load combined simulation results.

    Parameters
    ----------
    path:
        Optional path to combined_results.csv.

    Returns
    -------
    pd.DataFrame
        Combined results DataFrame.
    """
    if path is None:
        path = RESULTS_DIR / "combined_results.csv"

    if not path.exists():
        raise FileNotFoundError(f"Could not find results file: {path}")

    return pd.read_csv(path)


def plot_dai_price(
    results: pd.DataFrame,
    shock_time: int = 30,
    save_path: Path | None = None,
) -> Path:
    """
    Plot DAI price by scenario.

    Parameters
    ----------
    results:
        Combined scenario results.
    shock_time:
        ETH shock time.
    save_path:
        Optional save path.

    Returns
    -------
    Path
        Saved figure path.
    """
    if save_path is None:
        save_path = FIGURES_DIR / "dai_price_by_scenario.png"

    fig, ax = plt.subplots(figsize=(10, 6))

    for scenario_name, scenario_df in results.groupby("scenario"):
        scenario_df = scenario_df.sort_values("step")
        ax.plot(
            scenario_df["step"],
            scenario_df["dai_price"],
            label=scenario_name,
        )

    ax.axhline(1.0, linestyle="--", linewidth=1, label="DAI peg")
    ax.axvline(shock_time, linestyle=":", linewidth=1, label="ETH shock")

    ax.set_title("DAI Price under ETH Collateral Shock")
    ax.set_xlabel("Simulation step")
    ax.set_ylabel("DAI price")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_path, dpi=300)
    plt.close(fig)

    return save_path


def plot_active_bad_debt(
    results: pd.DataFrame,
    shock_time: int = 30,
    save_path: Path | None = None,
) -> Path:
    """
    Plot active bad debt by scenario.

    Parameters
    ----------
    results:
        Combined scenario results.
    shock_time:
        ETH shock time.
    save_path:
        Optional save path.

    Returns
    -------
    Path
        Saved figure path.
    """
    if save_path is None:
        save_path = FIGURES_DIR / "active_bad_debt_by_scenario.png"

    fig, ax = plt.subplots(figsize=(10, 6))

    for scenario_name, scenario_df in results.groupby("scenario"):
        scenario_df = scenario_df.sort_values("step")
        ax.plot(
            scenario_df["step"],
            scenario_df["total_bad_debt_active"],
            label=scenario_name,
        )

    ax.axvline(shock_time, linestyle=":", linewidth=1, label="ETH shock")

    ax.set_title("Active Bad Debt under ETH Collateral Shock")
    ax.set_xlabel("Simulation step")
    ax.set_ylabel("Active bad debt")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_path, dpi=300)
    plt.close(fig)

    return save_path


def plot_liquidatable_vaults(
    results: pd.DataFrame,
    shock_time: int = 30,
    save_path: Path | None = None,
) -> Path:
    """
    Plot number of liquidatable vaults by scenario.

    Parameters
    ----------
    results:
        Combined scenario results.
    shock_time:
        ETH shock time.
    save_path:
        Optional save path.

    Returns
    -------
    Path
        Saved figure path.
    """
    if save_path is None:
        save_path = FIGURES_DIR / "liquidatable_vaults_by_scenario.png"

    fig, ax = plt.subplots(figsize=(10, 6))

    for scenario_name, scenario_df in results.groupby("scenario"):
        scenario_df = scenario_df.sort_values("step")
        ax.plot(
            scenario_df["step"],
            scenario_df["n_liquidatable"],
            label=scenario_name,
        )

    ax.axvline(shock_time, linestyle=":", linewidth=1, label="ETH shock")

    ax.set_title("Liquidatable Vaults under ETH Collateral Shock")
    ax.set_xlabel("Simulation step")
    ax.set_ylabel("Number of liquidatable vaults")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_path, dpi=300)
    plt.close(fig)

    return save_path


def plot_keeper_profit(
    results: pd.DataFrame,
    shock_time: int = 30,
    save_path: Path | None = None,
) -> Path:
    """
    Plot cumulative keeper profit by scenario.

    Parameters
    ----------
    results:
        Combined scenario results.
    shock_time:
        ETH shock time.
    save_path:
        Optional save path.

    Returns
    -------
    Path
        Saved figure path.
    """
    if save_path is None:
        save_path = FIGURES_DIR / "keeper_profit_by_scenario.png"

    fig, ax = plt.subplots(figsize=(10, 6))

    for scenario_name, scenario_df in results.groupby("scenario"):
        scenario_df = scenario_df.sort_values("step")
        ax.plot(
            scenario_df["step"],
            scenario_df["keeper_profit_cumulative"],
            label=scenario_name,
        )

    ax.axvline(shock_time, linestyle=":", linewidth=1, label="ETH shock")

    ax.set_title("Cumulative Keeper Profit under ETH Collateral Shock")
    ax.set_xlabel("Simulation step")
    ax.set_ylabel("Cumulative keeper profit")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_path, dpi=300)
    plt.close(fig)

    return save_path


def create_all_figures(
    results: pd.DataFrame,
    shock_time: int = 30,
) -> list[Path]:
    """
    Create all standard result figures.

    Parameters
    ----------
    results:
        Combined scenario results.
    shock_time:
        ETH shock time.

    Returns
    -------
    list[Path]
        Saved figure paths.
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    figure_paths = [
        plot_dai_price(results, shock_time=shock_time),
        plot_active_bad_debt(results, shock_time=shock_time),
        plot_liquidatable_vaults(results, shock_time=shock_time),
        plot_keeper_profit(results, shock_time=shock_time),
    ]

    return figure_paths


if __name__ == "__main__":
    # Run:
    # python src/plot_results.py

    combined_results = load_combined_results()
    paths = create_all_figures(combined_results, shock_time=30)

    print("Saved figures:")
    for path in paths:
        print(path)