# Carbon Risk Grid — Facility Intelligence Dashboard

A Flask + vanilla JS dashboard for plotting facility carbon risk on a map,
with Chart.js metrics and a sidebar console that runs parallel checks
against regional grid emission factors.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000**.

Click **"Load sample data"** to see it working immediately, or upload your
own CSV.

## CSV format

Required columns: `facility_name, latitude, longitude, region`
Optional columns: `address, sector, capacity_mw, annual_emissions_tco2e`

If `annual_emissions_tco2e` is omitted, emissions are estimated from
`capacity_mw` using an assumed capacity factor and the region's grid
emission factor. Rows with invalid coordinates or a missing name are
skipped and reported back in the response, not silently dropped.

A ready-to-use example lives at `sample_data/sample_facilities.csv`.

## How risk is scored

`risk_model.py` computes a 0–100 score per facility from three
transparent, weighted components — regional grid emission factor (40%),
normalized annual emissions (45%), and a sector multiplier (15%) — then
buckets the score into low / medium / high / critical. It's a heuristic,
not a trained model, by design: every score is traceable back to its
inputs, which matters when the output drives publication-facing content.

## About the grid emission factor data

`emission_factors.py` ships with an **illustrative baseline** reference
table (kgCO2e/kWh), weighted toward Nigeria's gas-thermal grid with rough
per-region variance. It is not a live, verified feed. Before using this
for anything client-facing, swap `_lookup_one()` for a real source —
e.g. Transmission Company of Nigeria / NERC data, an IGES/IPCC grid
factor database, or a commercial API like Climatiq or Electricity Maps.
The UI intentionally labels these as "baseline" for the same reason.

## Parallel grid checks

The sidebar's "Run parallel grid checks" button fires one request per
region concurrently from the browser; the backend also runs its own
lookups through a `ThreadPoolExecutor` so a single multi-region request
resolves in parallel too. Each row in the console updates independently
as its check completes, with latency shown per region.

## Project layout

```
app.py                  Flask routes: /, /api/upload, /api/grid-check, /api/sample-csv
risk_model.py            Facility risk scoring
emission_factors.py       Grid factor reference table + parallel lookup
templates/index.html      Dashboard markup (Tailwind via CDN)
static/js/app.js          Map (Leaflet), charts (Chart.js), upload + check console logic
static/css/style.css      Telemetry-console animation, marker/popup theming
sample_data/               Example CSV
```

## Notes for production

- Tailwind is loaded via the CDN Play build for zero-config prototyping;
  swap in a compiled Tailwind build before shipping.
- No authentication or rate limiting is included — add both before
  exposing this beyond a local/internal demo.
- `MAX_CONTENT_LENGTH` caps uploads at 5MB; adjust as needed.
