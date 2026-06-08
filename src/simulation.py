"""
simulation.py

Base simulation engine for the simplified ETH-backed DAI model.

Version 2 connects:
- ETH price paths;
- synthetic vault population;
- vault collateral ratios;
- liquidation eligibility;
- keeper liquidation decisions;
- gas-cost frictions;
- bad debt measurement.

Later versions will add:
- DAI market price dynamics;
- confidence/panic regimes;
- DAI trader behaviour.
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

from liquidation import (
    LiquidationConfig,
    liquidate_vaults,
    summarise_liquidations,
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


def summarise_vault_system(
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

    active_df = vault_df[vault_df["is_active"]].copy()

    total_debt = active_df["debt_dai"].sum()
    total_collateral_value = active_df["collateral_value"].sum()
    total_bad_debt = active_df["bad_debt"].sum()

    n_active_vaults = len(active_df)
    n_liquidated_vaults = int(vault_df["is_liquidated"].sum())

    if n_active_vaults > 0:
        n_liquidatable = int(active_df["is_liquidatable"].sum())
        share_liquidatable = n_liquidatable / n_active_vaults
    else:
        n_liquidatable = 0
        share_liquidatable = 0.0

    if total_debt > 0:
        system_collateral_ratio = total_collateral_value / total_debt
    else:
        system_collateral_ratio = float("inf")

    return {
        "step": step,
        "eth_price": eth_price,
        "n_vaults_total": len(vault_df),
        "n_vaults_active": n_active_vaults,
        "n_vaults_liquidated_cumulative": n_liquidated_vaults,
        "total_debt_active": total_debt,
        "total_collateral_value_active": total_collateral_value,
        "system_collateral_ratio": system_collateral_ratio,
        "n_liquidatable": n_liquidatable,
        "share_liquidatable": share_liquidatable,
        "total_bad_debt_active": total_bad_debt,
    }


def run_simulation_with_price_path(
    config: SimulationConfig,
    price_path: pd.DataFrame,
    liquidation_config: LiquidationConfig,
    execute_liquidations: bool = True,
) -> pd.DataFrame:
    """
    Run the simulation using a provided ETH price path.

    Parameters
    ----------
    config:
        SimulationConfig object.
    price_path:
        DataFrame containing columns 'step' and 'eth_price'.
    liquidation_config:
        LiquidationConfig object.
    execute_liquidations:
        Whether keepers should actually execute profitable liquidations.

    Returns
    -------
    pd.DataFrame
        System-level simulation results by time step.
    """
    config.validate()
    liquidation_config.validate()

    required_cols = {"step", "eth_price"}
    missing_cols = required_cols - set(price_path.columns)
    if missing_cols:
        raise ValueError(f"price_path is missing columns: {missing_cols}")

    vaults = create_initial_vaults(config)

    records = []

    cumulative_keeper_profit = 0.0
    cumulative_debt_repaid = 0.0
    cumulative_collateral_liquidated = 0.0
    cumulative_bad_debt_realised = 0.0
    cumulative_unprofitable_attempts = 0

    for _, row in price_path.iterrows():
        step = int(row["step"])
        eth_price = float(row["eth_price"])

        # State before keeper action
        pre_summary = summarise_vault_system(
            vaults=vaults,
            eth_price=eth_price,
            step=step,
        )

        liquidation_summary = {
            "n_attempted": 0,
            "n_liquidated": 0,
            "n_unprofitable": 0,
            "keeper_profit": 0.0,
            "bad_debt_realised": 0.0,
            "debt_repaid": 0.0,
            "collateral_liquidated": 0.0,
        }

        if execute_liquidations and pre_summary["n_liquidatable"] > 0:
            liquidation_df = liquidate_vaults(
                vaults=vaults,
                eth_price=eth_price,
                config=liquidation_config,
            )
            liquidation_summary = summarise_liquidations(liquidation_df)

            cumulative_keeper_profit += float(liquidation_summary["keeper_profit"])
            cumulative_debt_repaid += float(liquidation_summary["debt_repaid"])
            cumulative_collateral_liquidated += float(
                liquidation_summary["collateral_liquidated"]
            )
            cumulative_bad_debt_realised += float(
                liquidation_summary["bad_debt_realised"]
            )
            cumulative_unprofitable_attempts += int(
                liquidation_summary["n_unprofitable"]
            )

        # State after keeper action
        post_summary = summarise_vault_system(
            vaults=vaults,
            eth_price=eth_price,
            step=step,
        )

        record = {
            **post_summary,
            "n_liquidatable_before_liquidation": pre_summary["n_liquidatable"],
            "n_attempted_liquidations": int(liquidation_summary["n_attempted"]),
            "n_successful_liquidations": int(liquidation_summary["n_liquidated"]),
            "n_unprofitable_liquidations": int(liquidation_summary["n_unprofitable"]),
            "keeper_profit_step": float(liquidation_summary["keeper_profit"]),
            "debt_repaid_step": float(liquidation_summary["debt_repaid"]),
            "collateral_liquidated_step": float(
                liquidation_summary["collateral_liquidated"]
            ),
            "bad_debt_realised_step": float(liquidation_summary["bad_debt_realised"]),
            "keeper_profit_cumulative": cumulative_keeper_profit,
            "debt_repaid_cumulative": cumulative_debt_repaid,
            "collateral_liquidated_cumulative": cumulative_collateral_liquidated,
            "bad_debt_realised_cumulative": cumulative_bad_debt_realised,
            "unprofitable_liquidations_cumulative": cumulative_unprofitable_attempts,
        }

        records.append(record)

    return pd.DataFrame(records)


def run_constant_price_simulation(
    config: SimulationConfig,
    liquidation_config: LiquidationConfig,
    execute_liquidations: bool = True,
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

    return run_simulation_with_price_path(
        config=config,
        price_path=price_path,
        liquidation_config=liquidation_config,
        execute_liquidations=execute_liquidations,
    )


def run_shock_simulation(
    config: SimulationConfig,
    liquidation_config: LiquidationConfig,
    shock_time: int = 50,
    shock_size: float = -0.43,
    execute_liquidations: bool = True,
) -> pd.DataFrame:
    """
    Run simulation with a deterministic ETH price shock.

    Parameters
    ----------
    config:
        SimulationConfig object.
    liquidation_config:
        LiquidationConfig object.
    shock_time:
        Time step at which the ETH shock occurs.
    shock_size:
        Percentage ETH price shock.
        Example: -0.43 means ETH falls by 43%.
    execute_liquidations:
        Whether to execute profitable liquidations.

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

    return run_simulation_with_price_path(
        config=config,
        price_path=price_path,
        liquidation_config=liquidation_config,
        execute_liquidations=execute_liquidations,
    )


def run_gbm_simulation(
    config: SimulationConfig,
    liquidation_config: LiquidationConfig,
    mu: float = 0.0,
    sigma: float = 0.80,
    dt: float = 1 / 365,
    execute_liquidations: bool = True,
) -> pd.DataFrame:
    """
    Run simulation with GBM ETH price path.

    Parameters
    ----------
    config:
        SimulationConfig object.
    liquidation_config:
        LiquidationConfig object.
    mu:
        Annualised drift.
    sigma:
        Annualised volatility.
    dt:
        Time step size.
    execute_liquidations:
        Whether to execute profitable liquidations.

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

    return run_simulation_with_price_path(
        config=config,
        price_path=price_path,
        liquidation_config=liquidation_config,
        execute_liquidations=execute_liquidations,
    )


if __name__ == "__main__":
    # Quick smoke test. Run:
    # python src/simulation.py

    sim_config = SimulationConfig(
        n_steps=100,
        n_vaults=100,
        initial_eth_price=2_000.0,
        liquidation_ratio=1.5,
        random_seed=42,
    )

    low_gas_config = LiquidationConfig(
        liquidation_penalty=0.13,
        gas_cost=100.0,
        risk_cost_rate=0.00,
        max_close_factor=1.0,
    )

    high_gas_config = LiquidationConfig(
        liquidation_penalty=0.13,
        gas_cost=700.0,
        risk_cost_rate=0.00,
        max_close_factor=1.0,
    )

    low_gas_results = run_shock_simulation(
        config=sim_config,
        liquidation_config=low_gas_config,
        shock_time=30,
        shock_size=-0.43,
        execute_liquidations=True,
    )

    high_gas_results = run_shock_simulation(
        config=sim_config,
        liquidation_config=high_gas_config,
        shock_time=30,
        shock_size=-0.43,
        execute_liquidations=True,
    )

    columns_to_show = [
        "step",
        "eth_price",
        "n_vaults_active",
        "n_liquidatable_before_liquidation",
        "n_successful_liquidations",
        "n_unprofitable_liquidations",
        "n_liquidatable",
        "total_bad_debt_active",
        "keeper_profit_cumulative",
        "bad_debt_realised_cumulative",
    ]

    print("Low gas results around shock:")
    print(low_gas_results.loc[27:34, columns_to_show])

    print("\nHigh gas results around shock:")
    print(high_gas_results.loc[27:34, columns_to_show])

    print("\nLow gas final row:")
    print(low_gas_results.tail(1)[columns_to_show].T)

    print("\nHigh gas final row:")
    print(high_gas_results.tail(1)[columns_to_show].T)