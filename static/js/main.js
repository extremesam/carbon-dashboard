let map = L.map('map').setView([6.5244, 3.3792], 10);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

let markers = [];

document.getElementById('csvFile').addEventListener('change', async function() {
    let file = this.files[0];
    let formData = new FormData();
    formData.append("file", file);

    let res = await fetch('/upload', {
        method: 'POST',
        body: formData
    });

    let data = await res.json();

    renderMap(data);
    renderChart(data);
});

function getColor(risk) {
    return risk === 'high' ? 'red' :
           risk === 'medium' ? 'orange' : 'green';
}

function renderMap(data) {
    markers.forEach(m => map.removeLayer(m));

    data.forEach(d => {
        let marker = L.circleMarker([d.lat, d.lon], {
            color: getColor(d.risk),
            radius: 8
        }).addTo(map);

        marker.bindPopup(`${d.address} - ${d.risk}`);
        markers.push(marker);
    });
}

function renderChart(data) {
    let counts = {low: 0, medium: 0, high: 0};

    data.forEach(d => counts[d.risk]++);

    new Chart(document.getElementById('riskChart'), {
        type: 'bar',
        data: {
            labels: ['Low', 'Medium', 'High'],
            datasets: [{
                label: 'Facilities',
                data: [counts.low, counts.medium, counts.high]
            }]
        }
    });
}

async function runGridCheck() {
    let region = document.getElementById('regionInput').value;

    let res = await fetch('/grid-check', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({region})
    });

    let data = await res.json();

    document.getElementById('gridResult').innerText =
        `Emission Factor: ${data.emission_factor}`;
}
