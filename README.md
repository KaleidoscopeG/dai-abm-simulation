# DAI ABM Simulation

This project develops a simplified agent-based simulation of DAI stability under stress. The aim is to investigate how the DAI peg may be affected by ETH collateral shocks when liquidation frictions, keeper incentives, and state-dependent market confidence are explicitly represented in a computational model.

The project does not attempt to reproduce the full MakerDAO protocol. Instead, it focuses on a simplified but interpretable simulation framework that captures the key mechanisms most relevant to DAI peg stability.

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

## Project Structure

dai-abm-simulation/
├── config/
│   └── baseline.yaml        # Baseline simulation parameters
├── src/
│   ├── agents.py            # Agent definitions and behaviour
│   ├── confidence.py        # Market confidence dynamics
│   ├── dai_market.py        # DAI price and market adjustment logic
│   ├── liquidation.py       # Liquidation and keeper mechanisms
│   ├── metrics.py           # Simulation output metrics
│   ├── price_process.py     # ETH price process and shock generation
│   ├── simulation.py        # Main simulation workflow
│   └── vault.py             # Vault-level collateral and debt mechanics
├── tests/                   # Unit tests
├── requirements.txt         # Python dependencies
├── environment.yml          # Conda environment specification
└── README.md

## Installation

Clone the repository:

    git clone git@github.com:KaleidoscopeG/dai-abm-simulation.git
    cd dai-abm-simulation

Create and activate a Python environment using Conda:

    conda env create -f environment.yml
    conda activate dai-sim

Alternatively, install the required packages with pip:

    pip install -r requirements.txt

## Usage

Run the baseline simulation from the project root:

    python src/simulation.py

Simulation parameters can be adjusted in:

    config/baseline.yaml

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