const RISK_COLORS = {
  low: '#3DDC84',
  medium: '#FFD23D',
  high: '#FF9F40',
  critical: '#FF4D4D',
};

let map, markerLayer, riskChart, regionChart;
let currentData = null;
let selectedFile = null;

// ---------- Map setup ----------
function initMap() {
  map = L.map('map', { zoomControl: true, attributionControl: true }).setView([9.0820, 8.6753], 6); // Nigeria default
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);
  markerLayer = L.layerGroup().addTo(map);
}

function riskMarker(facility) {
  const color = RISK_COLORS[facility.risk_category] || '#7A8088';
  return L.circleMarker([facility.latitude, facility.longitude], {
    radius: 7,
    color: color,
    weight: 1.5,
    fillColor: color,
    fillOpacity: 0.55,
  }).bindPopup(`
    <div class="risk-popup">
      <span class="rp-badge" style="background:${color}22;color:${color};border:1px solid ${color}66">${facility.risk_category}</span>
      <div class="rp-title">${escapeHtml(facility.facility_name)}</div>
      <div class="rp-row"><span>Risk score</span><span>${facility.risk_score}/100</span></div>
      <div class="rp-row"><span>Region</span><span>${escapeHtml(facility.region)}</span></div>
      <div class="rp-row"><span>Sector</span><span>${escapeHtml(facility.sector || 'other')}</span></div>
      <div class="rp-row"><span>Grid factor</span><span>${facility.grid_emission_factor_kgco2_per_kwh} kg/kWh</span></div>
      <div class="rp-row"><span>Est. emissions</span><span>${Number(facility.estimated_annual_emissions_tco2e).toLocaleString()} tCO2e (${facility.emissions_basis})</span></div>
    </div>
  `);
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s ?? '';
  return d.innerHTML;
}

function plotFacilities(facilities) {
  markerLayer.clearLayers();
  const bounds = [];
  facilities.forEach(f => {
    if (typeof f.latitude !== 'number' || typeof f.longitude !== 'number') return;
    riskMarker(f).addTo(markerLayer);
    bounds.push([f.latitude, f.longitude]);
  });
  if (bounds.length) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
  document.getElementById('emptyState').classList.toggle('hidden', bounds.length > 0);
  document.getElementById('legend').classList.toggle('hidden', bounds.length === 0);
}

// ---------- Metrics & charts ----------
function updateMetrics(summary) {
  document.getElementById('mFacilities').textContent = summary.facility_count;
  document.getElementById('mRegions').textContent = summary.region_count;
  document.getElementById('mAvgRisk').textContent = summary.avg_risk_score;
  document.getElementById('mEmissions').textContent = Math.round(summary.total_estimated_emissions_tco2e).toLocaleString();
}

function renderRiskChart(categoryCounts) {
  const ctx = document.getElementById('riskChart');
  const labels = ['low', 'medium', 'high', 'critical'];
  const data = labels.map(l => categoryCounts[l] || 0);
  const colors = labels.map(l => RISK_COLORS[l]);

  if (riskChart) riskChart.destroy();
  riskChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels.map(l => l[0].toUpperCase() + l.slice(1)),
      datasets: [{ data, backgroundColor: colors, borderColor: '#1B1E23', borderWidth: 2 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#7A8088', font: { family: 'JetBrains Mono', size: 10 }, boxWidth: 10 },
        },
      },
      cutout: '65%',
    },
  });
}

function renderRegionChart(facilities) {
  const totals = {};
  facilities.forEach(f => {
    totals[f.region] = (totals[f.region] || 0) + (f.estimated_annual_emissions_tco2e || 0);
  });
  const labels = Object.keys(totals).sort((a, b) => totals[b] - totals[a]);
  const data = labels.map(l => Math.round(totals[l]));

  const ctx = document.getElementById('regionChart');
  if (regionChart) regionChart.destroy();
  regionChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data, backgroundColor: '#D4FF3D', borderRadius: 3, barThickness: 14 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#7A8088', font: { family: 'JetBrains Mono', size: 9 } }, grid: { color: '#23262B' } },
        y: { ticks: { color: '#7A8088', font: { family: 'JetBrains Mono', size: 9 } }, grid: { display: false } },
      },
    },
  });
}

// ---------- Grid emission factor parallel-check console ----------
async function runParallelGridChecks(regions) {
  const console_ = document.getElementById('checkConsole');
  const liveDot = document.getElementById('liveDot');
  console_.innerHTML = '';
  liveDot.classList.remove('hidden');
  document.getElementById('runChecksBtn').disabled = true;

  const rowEls = {};
  regions.forEach(region => {
    const row = document.createElement('div');
    row.className = 'check-row pending';
    row.innerHTML = `
      <span class="flex items-center gap-2"><span class="status-dot pending"></span>${escapeHtml(region)}</span>
      <span class="text-muted">checking…</span>
    `;
    console_.appendChild(row);
    rowEls[region] = row;
  });

  // Fire one request per region concurrently so the UI reflects true parallelism.
  const checks = regions.map(region =>
    fetch('/api/grid-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ regions: [region] }),
    })
      .then(r => r.json())
      .then(data => {
        const result = data.results && data.results[0];
        const row = rowEls[region];
        if (!result) {
          row.className = 'check-row';
          row.innerHTML = `<span class="flex items-center gap-2"><span class="status-dot error"></span>${escapeHtml(region)}</span><span class="text-risk-critical">no data</span>`;
          return;
        }
        const dotClass = result.error ? 'error' : (result.matched_known_region ? 'done' : 'fallback');
        row.className = 'check-row';
        row.innerHTML = `
          <span class="flex items-center gap-2"><span class="status-dot ${dotClass}"></span>${escapeHtml(region)}</span>
          <span class="text-gray-300">${result.emission_factor_kgco2_per_kwh} kg/kWh <span class="text-muted">· ${result.latency_ms}ms</span></span>
        `;
      })
      .catch(() => {
        const row = rowEls[region];
        row.className = 'check-row';
        row.innerHTML = `<span class="flex items-center gap-2"><span class="status-dot error"></span>${escapeHtml(region)}</span><span class="text-risk-critical">failed</span>`;
      })
  );

  await Promise.all(checks);
  liveDot.classList.add('hidden');
  document.getElementById('runChecksBtn').disabled = false;
}

// ---------- Upload flow ----------
function showError(msg) {
  const banner = document.getElementById('errorBanner');
  if (!msg) { banner.classList.add('hidden'); banner.textContent = ''; return; }
  banner.textContent = msg;
  banner.classList.remove('hidden');
}

async function uploadCsv(file) {
  showError(null);
  const form = new FormData();
  form.append('file', file);
  document.getElementById('analyzeBtn').textContent = 'Analyzing…';

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || 'Upload failed.');
      return;
    }
    currentData = data;
    plotFacilities(data.facilities);
    updateMetrics(data.summary);
    renderRiskChart(data.summary.category_counts);
    renderRegionChart(data.facilities);
    document.getElementById('runChecksBtn').disabled = false;
    if (data.row_errors && data.row_errors.length) {
      showError(`Loaded with ${data.row_errors.length} row warning(s): ${data.row_errors.slice(0, 3).join(' ')}`);
    }
  } catch (e) {
    showError('Could not reach the server. Is the Flask app running?');
  } finally {
    document.getElementById('analyzeBtn').textContent = 'Analyze facilities';
  }
}

// ---------- Wire up UI ----------
document.getElementById('csvInput').addEventListener('change', (e) => {
  selectedFile = e.target.files[0] || null;
  document.getElementById('fileLabel').textContent = selectedFile ? selectedFile.name : 'Choose facility CSV…';
  document.getElementById('analyzeBtn').disabled = !selectedFile;
});

document.getElementById('analyzeBtn').addEventListener('click', () => {
  if (selectedFile) uploadCsv(selectedFile);
});

document.getElementById('loadSampleBtn').addEventListener('click', async () => {
  showError(null);
  const res = await fetch('/api/sample-csv');
  const text = await res.text();
  const file = new File([text], 'sample_facilities.csv', { type: 'text/csv' });
  selectedFile = file;
  document.getElementById('fileLabel').textContent = file.name;
  document.getElementById('analyzeBtn').disabled = false;
  uploadCsv(file);
});

document.getElementById('runChecksBtn').addEventListener('click', () => {
  if (currentData && currentData.regions && currentData.regions.length) {
    runParallelGridChecks(currentData.regions);
  }
});

initMap();
