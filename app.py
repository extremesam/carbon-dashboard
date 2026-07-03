from flask import Flask, render_template, request, jsonify
import pandas as pd
from utils import geocode_address, estimate_carbon_risk

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_csv():
    file = request.files['file']
    df = pd.read_csv(file)

    results = []

    for _, row in df.iterrows():
        address = row['address']
        lat, lon = geocode_address(address)

        risk = estimate_carbon_risk(lat, lon)

        results.append({
            "address": address,
            "lat": lat,
            "lon": lon,
            "risk": risk
        })

    return jsonify(results)

@app.route('/grid-check', methods=['POST'])
def grid_check():
    region = request.json.get("region")

    # Mock emission factor lookup
    data = {
        "region": region,
        "emission_factor": round(0.4 + hash(region) % 30 / 100, 2)
    }

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
