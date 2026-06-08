# DAI ABM Simulation

This project develops a simplified agent-based simulation of DAI stability under stress. The aim is to investigate how the DAI peg may be affected by ETH collateral shocks when liquidation frictions, keeper incentives, and state-dependent market confidence are explicitly represented in a computational model.

The project does not attempt to reproduce the full MakerDAO protocol. It focuses on a simplified but interpretable simulation framework that captures the key mechanisms most relevant to DAI peg stability.

## Project Motivation

DAI is designed to maintain a stable value close to 1 USD through over-collateralised vaults, liquidation mechanisms, and market incentives. However, under stressed market conditions, several frictions may weaken this stabilising mechanism. These include sharp ETH price declines, delayed or inefficient liquidations, high gas costs, limited keeper participation, and changes in market confidence.

This simulation explores how these factors may interact and whether liquidation efficiency and market confidence can stabilise or destabilise the DAI peg during stress scenarios.

## Key Mechanisms

The model currently focuses on the following mechanisms:

- collateralised minting of DAI;
- ETH price shocks;
- vault collateral ratios;
- liquidation thresholds;
- keeper and liquidator profitability;
- gas costs;
- belief-driven DAI demand;
- DAI price adjustment under supply-demand imbalance.

## Current Scope

This is an early-stage research simulation. The model is intentionally simplified and is designed for interpretability rather than full protocol replication. It should be understood as an experimental framework for analysing stabilisation and destabilisation channels in DAI-like collateralised stablecoin systems.

## Planned Extensions

Potential future extensions include:

- more heterogeneous vault owner behaviour;
- more detailed keeper competition;
- auction delay and partial liquidation mechanics;
- oracle lag and price update frictions;
- scenario-based stress testing;
- systematic sensitivity analysis;
- visualisation of peg deviation, liquidation volume, bad debt, and vault survival.

## Disclaimer

This project is for academic and research purposes only. It is not financial advice and should not be used for trading, investment, or risk-management decisions.