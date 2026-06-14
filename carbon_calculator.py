"""
carbon_calculator.py
---------------------
Core logic for calculating a user's daily carbon footprint from
simple, real-world inputs: transport, electricity usage, diet, and waste.

All emission factors are loaded from data/factors.json so they can be
updated without touching code (e.g., when regional grid data changes).
"""

import json
import os

FACTORS_PATH = os.path.join(os.path.dirname(__file__), "data", "factors.json")


def load_factors():
    """Load emission factors from the JSON data file."""
    with open(FACTORS_PATH, "r") as f:
        return json.load(f)


def calculate_footprint(entry, factors=None):
    """
    Calculate the total daily carbon footprint (kg CO2e) and a
    breakdown by category, given a user's daily activity entry.

    Parameters
    ----------
    entry : dict
        {
            "transport_mode": str,      # e.g. "car_petrol"
            "transport_km": float,
            "electricity_kwh": float,
            "diet": str,                # e.g. "medium_meat"
            "waste_kg": float
        }
    factors : dict, optional
        Pre-loaded emission factors (loaded from file if not given).

    Returns
    -------
    dict
        {
            "transport": float,
            "electricity": float,
            "diet": float,
            "waste": float,
            "total": float
        }
    """
    if factors is None:
        factors = load_factors()

    transport_mode = entry.get("transport_mode", "car_petrol")
    transport_km = float(entry.get("transport_km", 0))
    electricity_kwh = float(entry.get("electricity_kwh", 0))
    diet = entry.get("diet", "medium_meat")
    waste_kg = float(entry.get("waste_kg", 0))

    transport_factor = factors["transport"].get(transport_mode, 0)
    diet_factor = factors["diet"].get(diet, 0)
    electricity_factor = factors["electricity_kg_per_kwh"]
    waste_factor = factors["waste_kg_per_kg"]

    transport_emission = round(transport_km * transport_factor, 3)
    electricity_emission = round(electricity_kwh * electricity_factor, 3)
    diet_emission = round(diet_factor, 3)
    waste_emission = round(waste_kg * waste_factor, 3)

    total = round(
        transport_emission + electricity_emission + diet_emission + waste_emission, 3
    )

    return {
        "transport": transport_emission,
        "electricity": electricity_emission,
        "diet": diet_emission,
        "waste": waste_emission,
        "total": total,
    }


def yearly_projection(daily_total):
    """Project the yearly footprint (kg CO2e) from a single day's total."""
    return round(daily_total * 365, 2)
