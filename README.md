# Carbon Risk Dashboard

An interactive geospatial dashboard for visualizing facility-level carbon risk using Python (Flask), Leaflet, and Chart.js.

## Features

* Upload CSV of facility addresses
* Automatic geocoding (mock for now)
* Carbon risk classification (low, medium, high)
* Interactive map visualization
* Risk distribution chart
* Sidebar for regional emission factor checks

## CSV Format

Your file must include:

address

Example:

Lekki Phase 1, Lagos
Ikeja, Lagos

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000

## Tech Stack

* Flask (Backend)
* Leaflet (Mapping)
* Chart.js (Visualization)
* Tailwind CSS (UI)

## Notes

* Geocoding is currently mocked
* Carbon risk is estimated using placeholder logic
* Designed for future integration with real emissions data and satellite inputs
