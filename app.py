import csv
import io
import os

from flask import Flask, request, jsonify, render_template

from risk_model import score_facility
from emission_factors import run_parallel_checks

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB CSV cap

REQUIRED_COLUMNS = {"facility_name", "latitude", "longitude", "region"}
OPTIONAL_COLUMNS = {"address", "sector", "capacity_mw", "annual_emissions_tco2e"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sample-csv")
def sample_csv():
    path = os.path.join(os.path.dirname(__file__), "sample_data", "sample_facilities.csv")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/csv"}


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Attach a CSV under the 'file' field."}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only .csv files are supported."}), 400

    try:
        raw = file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return jsonify({"error": "Could not decode file as UTF-8 text."}), 400

    reader = csv.DictReader(io.StringIO(raw))
    if reader.fieldnames is None:
        return jsonify({"error": "CSV appears to be empty."}), 400

    columns = {c.strip().lower() for c in reader.fieldnames}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        return jsonify({
            "error": f"CSV is missing required column(s): {', '.join(sorted(missing))}",
            "required_columns": sorted(REQUIRED_COLUMNS),
            "optional_columns": sorted(OPTIONAL_COLUMNS),
        }), 400

    rows = []
    errors = []
    for i, raw_row in enumerate(reader, start=2):  # header is line 1
        row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items()}
        try:
            row["latitude"] = float(row["latitude"])
            row["longitude"] = float(row["longitude"])
        except (TypeError, ValueError):
            errors.append(f"Row {i}: invalid or missing latitude/longitude — skipped.")
            continue
        if not row.get("facility_name"):
            errors.append(f"Row {i}: missing facility_name — skipped.")
            continue
        rows.append(row)

    if not rows:
        return jsonify({"error": "No valid facility rows found.", "row_errors": errors}), 400

    # First pass: rough emissions estimate to find fleet max for normalization
    from risk_model import estimate_emissions_tco2e, _grid_factor_for_region
    prelim = []
    for row in rows:
        gf = _grid_factor_for_region(row.get("region", ""))
        est, basis = estimate_emissions_tco2e(row, gf)
        prelim.append(est)
    fleet_max_emissions = max(prelim) if prelim else 1.0

    scored = [score_facility(row, fleet_max_emissions) for row in rows]

    regions = sorted({r["region"] for r in scored if r.get("region")})
    category_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    total_emissions = 0.0
    for f in scored:
        category_counts[f["risk_category"]] += 1
        total_emissions += f["estimated_annual_emissions_tco2e"] or 0

    return jsonify({
        "facilities": scored,
        "regions": regions,
        "summary": {
            "facility_count": len(scored),
            "region_count": len(regions),
            "category_counts": category_counts,
            "total_estimated_emissions_tco2e": round(total_emissions, 1),
            "avg_risk_score": round(sum(f["risk_score"] for f in scored) / len(scored), 1),
        },
        "row_errors": errors,
    })


@app.route("/api/grid-check", methods=["POST"])
def grid_check():
    """
    Runs parallel lookups of regional grid emission factors for the
    regions supplied in the request body: {"regions": ["Lagos", "Abuja", ...]}
    """
    payload = request.get_json(silent=True) or {}
    regions = payload.get("regions", [])
    if not isinstance(regions, list) or not regions:
        return jsonify({"error": "Provide a non-empty 'regions' list."}), 400
    if len(regions) > 50:
        return jsonify({"error": "Max 50 regions per check."}), 400

    results = run_parallel_checks(regions)
    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
