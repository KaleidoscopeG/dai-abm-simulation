"""
dai_market.py

Simplified DAI market price dynamics for the DAI stability simulation.

This module models DAI price as responding to excess demand/supply pressure.

The aim is not to reproduce the full real-world DAI market. Instead, this
module provides a transparent mechanism for stress testing:

- if DAI trades below $1 and confidence is high, stabilising arbitrage demand
  pushes the price upward;
- if DAI trades above $1, selling/minting pressure pushes the price downward;
- if confidence collapses, panic selling can dominate stabilising arbitrage.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DAIMarketConfig:
    """
    Configuration for simplified DAI market dynamics.

    Attributes
    ----------
    peg_price:
        Target DAI price, normally 1 USD.
    price_adjustment_speed:
        Controls how strongly DAI price reacts to net demand pressure.
    arbitrage_strength:
        Strength of stabilising arbitrage around the peg.
    above_peg_supply_strength:
        Strength of selling/minting pressure when DAI is above peg.
    panic_strength:
        Strength of additional selling pressure in panic.
    noise_std:
        Standard deviation of random market noise.
    min_price:
        Lower bound for simulated DAI price.
    max_price:
        Upper bound for simulated DAI price.
    """

    peg_price: float = 1.0
    price_adjustment_speed: float = 0.02
    arbitrage_strength: float = 1.0
    above_peg_supply_strength: float = 1.0
    panic_strength: float = 1.0
    noise_std: float = 0.0005
    min_price: float = 0.50
    max_price: float = 1.50

    def validate(self) -> None:
        """Validate DAI market configuration."""
        if self.peg_price <= 0:
            raise ValueError("peg_price must be positive.")
        if self.price_adjustment_speed < 0:
            raise ValueError("price_adjustment_speed cannot be negative.")
        if self.arbitrage_strength < 0:
            raise ValueError("arbitrage_strength cannot be negative.")
        if self.above_peg_supply_strength < 0:
            raise ValueError("above_peg_supply_strength cannot be negative.")
        if self.panic_strength < 0:
            raise ValueError("panic_strength cannot be negative.")
        if self.noise_std < 0:
            raise ValueError("noise_std cannot be negative.")
        if self.min_price <= 0:
            raise ValueError("min_price must be positive.")
        if self.max_price <= self.min_price:
            raise ValueError("max_price must be greater than min_price.")


def calculate_dai_market_pressures(
    dai_price: float,
    confidence: float,
    panic_selling_pressure: float,
    market_config: DAIMarketConfig,
) -> dict:
    """
    Calculate simplified DAI demand and supply pressures.

    Parameters
    ----------
    dai_price:
        Current DAI price.
    confidence:
        Current confidence level in the peg.
    panic_selling_pressure:
        Additional panic selling pressure from confidence.py.
    market_config:
        DAIMarketConfig object.

    Returns
    -------
    dict
        Dictionary containing demand pressure, supply pressure, panic pressure,
        and net pressure.
    """
    market_config.validate()

    if dai_price <= 0:
        raise ValueError("dai_price must be positive.")
    if confidence < 0:
        raise ValueError("confidence cannot be negative.")
    if panic_selling_pressure < 0:
        raise ValueError("panic_selling_pressure cannot be negative.")

    peg_gap = market_config.peg_price - dai_price

    # Stabilising arbitrage:
    # If DAI < 1, buying pressure should be positive.
    # If DAI >= 1, this term becomes zero.
    demand_pressure = (
        market_config.arbitrage_strength
        * confidence
        * max(peg_gap, 0.0)
    )

    # Above-peg supply/minting:
    # If DAI > 1, supply pressure pushes price downward.
    # If DAI <= 1, this term becomes zero.
    above_peg_supply_pressure = (
        market_config.above_peg_supply_strength
        * max(-peg_gap, 0.0)
    )

    # Panic selling:
    # This is extra sell pressure when confidence breaks down.
    panic_pressure = market_config.panic_strength * panic_selling_pressure

    total_supply_pressure = above_peg_supply_pressure + panic_pressure

    net_pressure = demand_pressure - total_supply_pressure

    return {
        "demand_pressure": demand_pressure,
        "above_peg_supply_pressure": above_peg_supply_pressure,
        "panic_pressure": panic_pressure,
        "total_supply_pressure": total_supply_pressure,
        "net_pressure": net_pressure,
    }


def update_dai_price(
    dai_price: float,
    confidence: float,
    panic_selling_pressure: float,
    market_config: DAIMarketConfig,
    rng: np.random.Generator | None = None,
) -> tuple[float, dict]:
    """
    Update DAI price by one step.

    Price update rule:

        P_{t+1} = P_t + eta * net_pressure + noise

    where net_pressure = demand pressure - supply pressure.

    Parameters
    ----------
    dai_price:
        Current DAI price.
    confidence:
        Current confidence level.
    panic_selling_pressure:
        Additional panic selling pressure.
    market_config:
        DAIMarketConfig object.
    rng:
        Optional NumPy random generator.

    Returns
    -------
    tuple[float, dict]
        New DAI price and pressure details.
    """
    market_config.validate()

    if rng is None:
        rng = np.random.default_rng()

    pressures = calculate_dai_market_pressures(
        dai_price=dai_price,
        confidence=confidence,
        panic_selling_pressure=panic_selling_pressure,
        market_config=market_config,
    )

    noise = rng.normal(0.0, market_config.noise_std)

    new_price = (
        dai_price
        + market_config.price_adjustment_speed * pressures["net_pressure"]
        + noise
    )

    new_price = float(
        np.clip(new_price, market_config.min_price, market_config.max_price)
    )

    pressures["price_noise"] = noise
    pressures["new_dai_price"] = new_price

    return new_price, pressures


if __name__ == "__main__":
    # Quick smoke test. Run:
    # python src/dai_market.py

    market_config = DAIMarketConfig()
    rng = np.random.default_rng(42)

    test_cases = [
        {
            "name": "below peg, high confidence",
            "dai_price": 0.98,
            "confidence": 1.0,
            "panic_selling_pressure": 0.0,
        },
        {
            "name": "below peg, low confidence",
            "dai_price": 0.98,
            "confidence": 0.1,
            "panic_selling_pressure": 0.0,
        },
        {
            "name": "above peg",
            "dai_price": 1.02,
            "confidence": 1.0,
            "panic_selling_pressure": 0.0,
        },
        {
            "name": "panic below peg",
            "dai_price": 0.94,
            "confidence": 0.1,
            "panic_selling_pressure": 0.12,
        },
    ]

    for case in test_cases:
        new_price, pressures = update_dai_price(
            dai_price=case["dai_price"],
            confidence=case["confidence"],
            panic_selling_pressure=case["panic_selling_pressure"],
            market_config=market_config,
            rng=rng,
        )

        print(f"\n{case['name']}")
        print(f"old price: {case['dai_price']}")
        print(f"new price: {new_price}")
        print(pressures)