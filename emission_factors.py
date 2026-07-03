"""
emission_factors.py

Provides a reference table of regional grid emission factors (kgCO2e/kWh)
and a concurrent lookup routine that simulates the latency of querying
multiple regional/utility data sources in parallel.

IMPORTANT — DATA PROVENANCE:
The GRID_EMISSION_FACTORS table below is an illustrative baseline, not a
live authoritative feed. Real deployments should replace `_lookup_one()`
with calls to a verified source such as:
  - National grid operator / regulator publications (e.g. NERC, TCN for Nigeria)
  - IGES/IPCC national grid emission factor databases
  - A commercial API (e.g. Climatiq, Watershed, Electricity Maps)
Values here are order-of-magnitude approximations for Nigeria's largely
gas-thermal grid, with light regional variance to model DisCo-zone
differences. They are clearly surfaced as "baseline / unverified" in the
API response so the frontend can label them honestly.
"""

import time
import random
import concurrent.futures
from datetime import datetime, timezone

# kgCO2e per kWh — illustrative baseline figures (see module docstring)
GRID_EMISSION_FACTORS = {
    # Nigeria — approximate national grid average is thermal(gas)-heavy;
    # regional variance modeled loosely on DisCo zone generation mix.
    "lagos":        0.52,
    "abuja":        0.49,
    "port harcourt":0.55,
    "kano":         0.47,
    "ibadan":       0.50,
    "kaduna":       0.46,
    "enugu":        0.48,
    "benin city":   0.51,
    "jos":          0.44,
    "warri":        0.56,
    "nigeria":      0.50,  # national fallback
    # A handful of non-Nigeria fallbacks for generic use
    "united states": 0.37,
    "united kingdom":0.19,
    "south africa":  0.85,
    "germany":       0.34,
    "global average":0.48,
}

DEFAULT_FACTOR = GRID_EMISSION_FACTORS["global average"]


def _normalize(region: str) -> str:
    return (region or "").strip().lower()


def _lookup_one(region: str) -> dict:
    """
    Simulates a single network round-trip to a regional data source.
    Replace this body with a real HTTP call in production.
    """
    started = time.monotonic()
    # Simulate variable network/API latency so parallelism is visible in the UI
    time.sleep(random.uniform(0.35, 1.2))

    key = _normalize(region)
    factor = GRID_EMISSION_FACTORS.get(key)
    matched = factor is not None
    if factor is None:
        factor = DEFAULT_FACTOR

    elapsed_ms = round((time.monotonic() - started) * 1000)
    return {
        "region": region,
        "emission_factor_kgco2_per_kwh": factor,
        "matched_known_region": matched,
        "source": "baseline_reference_table" if matched else "global_average_fallback",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "latency_ms": elapsed_ms,
    }


def run_parallel_checks(regions: list[str], max_workers: int = 8) -> list[dict]:
    """
    Runs grid-emission-factor lookups for all given regions concurrently
    and returns results in the original region order.
    """
    unique_regions = list(dict.fromkeys(r for r in regions if r))
    if not unique_regions:
        return []

    results_by_region = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_region = {
            pool.submit(_lookup_one, region): region for region in unique_regions
        }
        for future in concurrent.futures.as_completed(future_to_region):
            region = future_to_region[future]
            try:
                results_by_region[region] = future.result()
            except Exception as exc:  # keep one failure from sinking the batch
                results_by_region[region] = {
                    "region": region,
                    "error": str(exc),
                    "emission_factor_kgco2_per_kwh": DEFAULT_FACTOR,
                    "matched_known_region": False,
                    "source": "error_fallback",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": None,
                }

    return [results_by_region[r] for r in unique_regions]
