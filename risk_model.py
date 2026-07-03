"""
risk_model.py

A transparent, explainable heuristic for scoring facility-level carbon risk.
This is intentionally simple (not a trained model) so every score can be
traced back to its inputs — appropriate for a dashboard where the "why"
behind a color on the map matters as much as the color itself.

risk_score (0-100) is a weighted blend of:
  - normalized regional grid emission factor  (40%)
  - normalized annual emissions estimate      (45%)
  - sector risk multiplier                    (15%)

Facilities without a declared annual_emissions_tco2e get one estimated
from capacity_mw using a simple capacity-factor * grid-factor model —
clearly flagged as "estimated" vs "reported" in the output.
"""

from emission_factors import GRID_EMISSION_FACTORS, DEFAULT_FACTOR, _normalize

SECTOR_MULTIPLIERS = {
    "oil and gas": 1.30,
    "power generation": 1.25,
    "manufacturing": 1.10,
    "mining": 1.15,
    "agriculture": 0.85,
    "logistics": 1.00,
    "defence": 1.05,
    "commercial": 0.80,
    "other": 1.00,
}

# Assumed capacity factor for facilities that only report capacity_mw,
# used purely to derive an order-of-magnitude emissions estimate.
ASSUMED_CAPACITY_FACTOR = 0.55
HOURS_PER_YEAR = 8760

RISK_BANDS = [
    (0, 25, "low"),
    (25, 50, "medium"),
    (50, 75, "high"),
    (75, 101, "critical"),
]


def _sector_multiplier(sector: str) -> float:
    return SECTOR_MULTIPLIERS.get((sector or "other").strip().lower(), 1.0)


def _grid_factor_for_region(region: str) -> float:
    return GRID_EMISSION_FACTORS.get(_normalize(region), DEFAULT_FACTOR)


def estimate_emissions_tco2e(row: dict, grid_factor: float) -> tuple[float, str]:
    """Returns (emissions_tco2e, 'reported' | 'estimated')."""
    reported = row.get("annual_emissions_tco2e")
    if reported not in (None, "", "nan"):
        try:
            return float(reported), "reported"
        except (TypeError, ValueError):
            pass

    capacity_mw = row.get("capacity_mw")
    try:
        capacity_mw = float(capacity_mw)
    except (TypeError, ValueError):
        capacity_mw = None

    if capacity_mw:
        mwh = capacity_mw * HOURS_PER_YEAR * ASSUMED_CAPACITY_FACTOR
        tco2e = mwh * grid_factor  # kg/kWh == t/MWh
        return round(tco2e, 1), "estimated"

    # No capacity or reported emissions — fall back to a conservative
    # low estimate so the facility still plots, clearly marked.
    return 500.0, "estimated"


def score_facility(row: dict, fleet_max_emissions: float) -> dict:
    grid_factor = _grid_factor_for_region(row.get("region", ""))
    emissions_tco2e, emissions_basis = estimate_emissions_tco2e(row, grid_factor)

    grid_component = min(grid_factor / 0.9, 1.0) * 40  # 0.9 kg/kWh ~ worst-case anchor
    emissions_component = min(
        emissions_tco2e / max(fleet_max_emissions, 1), 1.0
    ) * 45
    sector_component = (_sector_multiplier(row.get("sector", "other")) / 1.30) * 15

    raw_score = grid_component + emissions_component + sector_component
    score = round(min(max(raw_score, 0), 100), 1)

    category = next(label for lo, hi, label in RISK_BANDS if lo <= score < hi)

    return {
        "facility_name": row.get("facility_name") or "Unnamed facility",
        "address": row.get("address", ""),
        "region": row.get("region", "Unknown"),
        "sector": row.get("sector", "other"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "grid_emission_factor_kgco2_per_kwh": grid_factor,
        "estimated_annual_emissions_tco2e": emissions_tco2e,
        "emissions_basis": emissions_basis,
        "risk_score": score,
        "risk_category": category,
    }
