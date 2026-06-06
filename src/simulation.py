"""
simulation.py

Base simulation engine for the simplified ETH-backed DAI model.

Version 1 connects:
- ETH price paths;
- synthetic vault population;
- vault collateral ratios;
- liquidation eligibility;
- bad debt measurement.

Later versions will add:
- DAI market price dynamics;
- confidence/panic regimes;
- keeper profitability;
- gas costs;
- liquidation execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from price_process import (
    PriceProcessConfig,
    generate_constant_price_path,
    generate_shock_price_path,
    generate_gbm_price_path,
)

from vault import (
    Vault,
    generate_random_vaults,
    vaults_to_dataframe,
)


@dataclass(frozen=True)
class SimulationConfig:
    """
    Configuration for the base simulation.

    Attributes
    ----------
    n_steps:
        Number of simulation time steps.
    n_vaults:
        Number of synthetic vaults.
    initial_eth_price:
        Initial ETH price in USD.
    liquidation_ratio:
        Liquidation ratio for vaults. Example: 1.5 means 150%.
    debt_mean:
        Mean initial DAI debt per vault.
    debt_std:
        Standard deviation of initial DAI debt.
    collateral_ratio_mean:
        Mean initial collateral ratio.
    collateral_ratio_std:
        Standard deviation of initial collateral ratio.
    random_seed:
        Random seed for reproducibility.
    """

    n_steps: int = 200
    n_vaults: int = 100
    initial_eth_price: float = 2_000.0
    liquidation_ratio: float = 1.5

    debt_mean: float = 5_000.0
    debt_std: float = 1_000.0
    collateral_ratio_mean: float = 2.0
    collateral_ratio_std: float = 0.25

    random_seed: Optional[int] = 42

    def validate(self) -> None:
        """Validate basic simulation inputs."""
        if self.n_steps <= 0:
            raise ValueError("n_steps must be positive.")
        if self.n_vaults <= 0:
            raise ValueError("n_vaults must be positive.")
        if self.initial_eth_price <= 0:
            raise ValueError("initial_eth_price must be positive.")
        if self.liquidation_ratio <= 1:
            raise ValueError("liquidation_ratio must be greater than 1.")
        if self.debt_mean <= 0:
            raise ValueError("debt_mean must be positive.")
        if self.debt_std < 0:
            raise ValueError("debt_std cannot be negative.")
        if self.collateral_ratio_mean <= self.liquidation_ratio:
            raise ValueError(
                "collateral_ratio_mean should be greater than liquidation_ratio."
            )
        if self.collateral_ratio_std < 0:
            raise ValueError("collateral_ratio_std cannot be negative.")


def create_initial_vaults(config: SimulationConfig) -> list[Vault]:
    """
    Create the initial synthetic vault population.

    Parameters
    ----------
    config:
        SimulationConfig object.

    Returns
    -------
    list[Vault]
        Initial vault population.
    """
    config.validate()

    return generate_random_vaults(
        n_vaults=config.n_vaults,
        eth_price=config.initial_eth_price,
        liquidation_ratio=config.liquidation_ratio,
        debt_mean=config.debt_mean,
        debt_std=config.debt_std,
        collateral_ratio_mean=config.collateral_ratio_mean,
        collateral_ratio_std=config.collateral_ratio_std,
        random_seed=config.random_seed,
    )


def summarize_vault_system(
    vaults: list[Vault],
    eth_price: float,
    step: int,
) -> dict:
    """
    Summarise vault system state at one time step.

    Parameters
    ----------
    vaults:
        List of Vault objects.
    eth_price:
        Current ETH price.
    step:
        Current simulation step.

    Returns
    -------
    dict
        System-level summary.
    """
    vault_df = vaults_to_dataframe(vaults, eth_price=eth_price)

    total_debt = vault_df["debt_dai"].sum()
    total_collateral_value = vault_df["collateral_value"].sum()
    total_bad_debt = vault_df["bad_debt"].sum()

    n_liquidatable = int(vault_df["is_liquidatable"].sum())
    share_liquidatable = n_liquidatable / len(vault_df)

    if total_debt > 0:
        system_collateral_ratio = total_collateral_value / total_debt
    else:
        system_collateral_ratio = float("inf")

    return {
        "step": step,
        "eth_price": eth_price,
        "n_vaults": len(vault_df),
        "total_debt": total_debt,
        "total_collateral_value": total_collateral_value,
        "system_collateral_ratio": system_collateral_ratio,
        "n_liquidatable": n_liquidatable,
        "share_liquidatable": share_liquidatable,
        "total_bad_debt": total_bad_debt,
    }


def run_simulation_with_price_path(
    config: SimulationConfig,
    price_path: pd.DataFrame,
) -> pd.DataFrame:
    """
    Run the base vault simulation using a provided ETH price path.

    Parameters
    ----------
    config:
        SimulationConfig object.
    price_path:
        DataFrame containing columns 'step' and 'eth_price'.

    Returns
    -------
    pd.DataFrame
        System-level simulation results by time step.
    """
    config.validate()

    required_cols = {"step", "eth_price"}
    missing_cols = required_cols - set(price_path.columns)
    if missing_cols:
        raise ValueError(f"price_path is missing columns: {missing_cols}")

    vaults = create_initial_vaults(config)

    records = []

    for _, row in price_path.iterrows():
        step = int(row["step"])
        eth_price = float(row["eth_price"])

        summary = summarize_vault_system(
            vaults=vaults,
            eth_price=eth_price,
            step=step,
        )
        records.append(summary)

    return pd.DataFrame(records)


def run_constant_price_simulation(
    config: SimulationConfig,
) -> pd.DataFrame:
    """
    Run simulation with constant ETH price.

    Useful for debugging.
    """
    price_config = PriceProcessConfig(
        n_steps=config.n_steps,
        initial_price=config.initial_eth_price,
        random_seed=config.random_seed,
    )
    price_path = generate_constant_price_path(price_config)

    return run_simulation_with_price_path(config, price_path)


def run_shock_simulation(
    config: SimulationConfig,
    shock_time: int = 50,
    shock_size: float = -0.43,
) -> pd.DataFrame:
    """
    Run simulation with a deterministic ETH price shock.

    Parameters
    ----------
    config:
        SimulationConfig object.
    shock_time:
        Time step at which the ETH shock occurs.
    shock_size:
        Percentage ETH price shock.
        Example: -0.43 means ETH falls by 43%.

    Returns
    -------
    pd.DataFrame
        System-level simulation results.
    """
    price_config = PriceProcessConfig(
        n_steps=config.n_steps,
        initial_price=config.initial_eth_price,
        random_seed=config.random_seed,
    )
    price_path = generate_shock_price_path(
        config=price_config,
        shock_time=shock_time,
        shock_size=shock_size,
    )

    return run_simulation_with_price_path(config, price_path)


def run_gbm_simulation(
    config: SimulationConfig,
    mu: float = 0.0,
    sigma: float = 0.80,
    dt: float = 1 / 365,
) -> pd.DataFrame:
    """
    Run simulation with GBM ETH price path.

    Parameters
    ----------
    config:
        SimulationConfig object.
    mu:
        Annualised drift.
    sigma:
        Annualised volatility.
    dt:
        Time step size.

    Returns
    -------
    pd.DataFrame
        System-level simulation results.
    """
    price_config = PriceProcessConfig(
        n_steps=config.n_steps,
        initial_price=config.initial_eth_price,
        random_seed=config.random_seed,
    )
    price_path = generate_gbm_price_path(
        config=price_config,
        mu=mu,
        sigma=sigma,
        dt=dt,
    )

    return run_simulation_with_price_path(config, price_path)


if __name__ == "__main__":
    # Quick smoke test. Run:
    # python src/simulation.py

    config = SimulationConfig(
        n_steps=100,
        n_vaults=100,
        initial_eth_price=2_000.0,
        liquidation_ratio=1.5,
        random_seed=42,
    )

    results = run_shock_simulation(
        config=config,
        shock_time=30,
        shock_size=-0.43,
    )

    print("Simulation results head:")
    print(results.head())

    print("\nSimulation results around shock:")
    print(
        results.loc[
            27:34,
            [
                "step",
                "eth_price",
                "system_collateral_ratio",
                "n_liquidatable",
                "share_liquidatable",
                "total_bad_debt",
            ],
        ]
    )

    print("\nFinal row:")
    print(results.tail(1).T)