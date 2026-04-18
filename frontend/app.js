const API_BASE = '';

let map;
let txMarker = null;
let rxMarker = null;
let txCoords = null;
let rxCoords = null;
let clickMode = 'p2p';
let currentLegend = null;
let covTxCoords = null;
let computedCoverageRadius = null;

// Multi-site coverage
let sitesCoverage = [];
const SITE_COLORS = ['#ff4444', '#44ff44', '#4444ff', '#ffff44', '#ff44ff', '#44ffff'];

class CoverageSite {
    constructor(name, tx, coverage_data, color) {
        this.id = Date.now();
        this.name = name;
        this.tx = tx;
        this.coverage_data = coverage_data;
        this.color = color;
        this.visible = true;
        this.opacity = 0.6;
    }
}

const MODE_LABELS = {
    0: 'Line-of-Sight',
    1: 'Single Horizon Diffraction',
    2: 'Double Horizon Diffraction',
    3: 'Troposcatter',
    4: 'Diffraction LOS Backward',
    5: 'Mixed Path',
};

function initMap() {
    map = new maplibregl.Map({
        container: 'map',
        style: {
            version: 8,
            sources: {
                'hillshade': {
                    type: 'raster',
                    tiles: [
                        'https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}',
                    ],
                    tileSize: 256,
                    attribution: '© Esri World Hillshade',
                },
                'osm': {
                    type: 'raster',
                    tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                    tileSize: 256,
                    attribution: '© OpenStreetMap contributors',
                },
            },
            layers: [
                { id: 'hillshade', type: 'raster', source: 'hillshade' },
                { id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-opacity': 0.55 } },
            ],
        },
        center: [121.0, 12.0],
        zoom: 6,
    });

    map.on('load', () => setupLayers());
    map.on('click', handleMapClick);
}

function setupLayers() {
    map.addSource('path-line', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
        id: 'path-line-layer',
        type: 'line',
        source: 'path-line',
        paint: { 'line-color': '#22d3ee', 'line-width': 3 },
    });

    map.addSource('horizons', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
        id: 'horizons-layer',
        type: 'circle',
        source: 'horizons',
        paint: {
            'circle-radius': 6,
            'circle-color': '#f59e0b',
            'circle-stroke-color': '#0b0b0b',
            'circle-stroke-width': 2,
        },
    });
}

function handleMapClick(e) {
    const { lng, lat } = e.lngLat;

    if (clickMode === 'p2p') {
        if (!txCoords) {
            txCoords = { lng, lat };
            if (txMarker) txMarker.remove();
            txMarker = new maplibregl.Marker({ color: '#22c55e' }).setLngLat([lng, lat]).addTo(map);
            document.getElementById('tx-coords').textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        } else if (!rxCoords) {
            rxCoords = { lng, lat };
            if (rxMarker) rxMarker.remove();
            rxMarker = new maplibregl.Marker({ color: '#ef4444' }).setLngLat([lng, lat]).addTo(map);
            document.getElementById('rx-coords').textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        } else {
            txCoords = { lng, lat };
            rxCoords = null;
            if (txMarker) txMarker.remove();
            if (rxMarker) rxMarker.remove();
            txMarker = new maplibregl.Marker({ color: '#22c55e' }).setLngLat([lng, lat]).addTo(map);
            document.getElementById('tx-coords').textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
            document.getElementById('rx-coords').textContent = 'Not selected';
        }
    } else if (clickMode === 'coverage') {
        covTxCoords = { lat, lon: lng };
        if (txMarker) txMarker.remove();
        txMarker = new maplibregl.Marker({ color: '#22c55e' }).setLngLat([lng, lat]).addTo(map);
        document.getElementById('cov-tx-coords').textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        computedCoverageRadius = null;
        document.getElementById('computed-radius').classList.add('hidden');
        document.getElementById('coverage-btn').disabled = true;
    }
}

function drawPathOnMap(tx, rx) {
    map.getSource('path-line').setData({
        type: 'FeatureCollection',
        features: [{
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: [[tx.lng, tx.lat], [rx.lng, rx.lat]] },
        }],
    });
}

function drawHorizons(horizons, tx, rx, totalDistM) {
    const features = horizons.map(h => {
        const t = h.d_m / totalDistM;
        const lng = tx.lng + t * (rx.lng - tx.lng);
        const lat = tx.lat + t * (rx.lat - tx.lat);
        return {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [lng, lat] },
            properties: { role: h.role },
        };
    });
    map.getSource('horizons').setData({ type: 'FeatureCollection', features });
}

function renderProfileChart(result) {
    const chartDiv = document.getElementById('profile-chart');
    const profile = result.profile;
    if (!profile || profile.length === 0) return;

    const distances = profile.map(p => p.d / 1000);
    const terrainB = profile.map(p => p.terrain_bulge);
    const los = profile.map(p => p.los);
    const fu = profile.map(p => p.fresnel_upper);
    const fl = profile.map(p => p.fresnel_lower);
    const f60 = profile.map(p => p.fresnel_60);

    // Base-ground fill (earth-curve corrected terrain)
    const terrainTrace = {
        x: distances,
        y: terrainB,
        name: 'Terrain (earth-curved)',
        type: 'scatter',
        fill: 'tozeroy',
        fillcolor: 'rgba(92, 64, 42, 0.55)',
        line: { color: '#8B5A2B', width: 2 },
        hovertemplate: '%{x:.2f} km<br>%{y:.0f} m<extra></extra>',
    };

    // Fresnel zone outline
    const fresnelZone = {
        x: [...distances, ...distances.slice().reverse()],
        y: [...fu, ...fl.slice().reverse()],
        name: 'Fresnel F1',
        type: 'scatter',
        fill: 'toself',
        fillcolor: 'rgba(255, 200, 0, 0.12)',
        line: { color: 'rgba(255, 200, 0, 0.5)', width: 1 },
        hoverinfo: 'skip',
    };

    // 60% Fresnel (engineering threshold)
    const f60Trace = {
        x: distances,
        y: f60,
        name: '0.6 F1',
        type: 'scatter',
        line: { color: 'rgba(255, 200, 0, 0.8)', width: 1, dash: 'dot' },
        hoverinfo: 'skip',
    };

    // LOS straight line
    const losTrace = {
        x: distances,
        y: los,
        name: 'LOS',
        type: 'scatter',
        line: { color: '#3b82f6', width: 2, dash: 'dash' },
        hoverinfo: 'skip',
    };

    // Fresnel obstruction shading (red where terrain > fresnel_lower)
    const obstructX = [];
    const obstructYtop = [];
    const obstructYbottom = [];
    profile.forEach(p => {
        if (p.violates_f1) {
            obstructX.push(p.d / 1000);
            obstructYtop.push(Math.min(p.terrain_bulge, p.fresnel_upper));
            obstructYbottom.push(p.fresnel_lower);
        }
    });

    const traces = [fresnelZone, f60Trace, losTrace, terrainTrace];

    if (obstructX.length > 1) {
        traces.push({
            x: [...obstructX, ...obstructX.slice().reverse()],
            y: [...obstructYtop, ...obstructYbottom.slice().reverse()],
            name: 'Fresnel violation',
            type: 'scatter',
            fill: 'toself',
            fillcolor: 'rgba(239, 68, 68, 0.45)',
            line: { color: 'rgba(239, 68, 68, 0.85)', width: 1 },
            hoverinfo: 'skip',
        });
    }

    // Horizon markers as vertical lines via shapes
    const shapes = (result.horizons || []).map(h => ({
        type: 'line',
        x0: h.d_m / 1000,
        x1: h.d_m / 1000,
        yref: 'paper',
        y0: 0,
        y1: 1,
        line: { color: '#f59e0b', width: 1.5, dash: 'dot' },
    }));

    const annotations = (result.horizons || []).map((h, i) => ({
        x: h.d_m / 1000,
        y: 1,
        yref: 'paper',
        text: h.role === 'tx_horizon' ? 'TX horizon' : 'RX horizon',
        showarrow: false,
        font: { size: 10, color: '#f59e0b' },
        yshift: -4,
        xshift: (i % 2 === 0 ? 30 : -30),
    }));

    Plotly.newPlot(chartDiv, traces, {
        margin: { t: 20, r: 20, b: 36, l: 52 },
        xaxis: { title: 'Distance (km)', gridcolor: '#333' },
        yaxis: { title: 'Elevation (m)', gridcolor: '#333' },
        legend: { orientation: 'h', y: -0.22, font: { size: 10 } },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#ddd', size: 11 },
        shapes,
        annotations,
    }, { displayModeBar: false, responsive: true });

    const flagsEl = document.getElementById('chart-flags');
    const flags = result.flags || {};
    const parts = [];
    if (flags.los_blocked) parts.push('<span class="flag bad">LOS blocked</span>');
    else if (flags.fresnel_60_violated) parts.push('<span class="flag warn">0.6 F1 violated</span>');
    else if (flags.fresnel_f1_violated) parts.push('<span class="flag warn">F1 grazed</span>');
    else parts.push('<span class="flag ok">F1 clear</span>');
    flagsEl.innerHTML = parts.join(' ');

    const chartPanel = document.getElementById('chart-panel');
    chartPanel.classList.remove('hidden');
    setTimeout(() => map.resize(), 100);
}

function displayP2PResult(result) {
    const resultBox = document.getElementById('p2p-result');
    const content = document.getElementById('result-content');
    const lb = result.link_budget || {};
    const modeName = MODE_LABELS[result.mode] || 'Unknown';

    const prx = lb.prx_dbm;
    const margin = lb.margin_db;
    const prxClass = margin >= 10 ? 'good' : margin >= 0 ? 'warn' : 'bad';

    content.innerHTML = `
        <div class="stat-grid">
            <div class="stat">
                <span class="stat-label">Distance</span>
                <span class="stat-value">${(result.distance_m / 1000).toFixed(2)} km</span>
            </div>
            <div class="stat">
                <span class="stat-label">ITM Loss</span>
                <span class="stat-value loss">${result.loss_db} dB</span>
            </div>
            <div class="stat">
                <span class="stat-label">Prx</span>
                <span class="stat-value ${prxClass}">${prx} dBm</span>
            </div>
            <div class="stat">
                <span class="stat-label">Margin</span>
                <span class="stat-value ${prxClass}">${margin} dB</span>
            </div>
            <div class="stat full">
                <span class="stat-label">Mode</span>
                <span class="stat-value mode">${modeName}</span>
            </div>
        </div>
        <div class="lb-table">
            <div><span>EIRP</span><span>${lb.eirp_dbm} dBm</span></div>
            <div><span>FSPL</span><span>${lb.fspl_db} dB</span></div>
            <div><span>Excess loss</span><span>${lb.excess_loss_db} dB</span></div>
            <div><span>RX sensitivity</span><span>${lb.rx_sensitivity_dbm} dBm</span></div>
        </div>
    `;
    resultBox.classList.remove('hidden');
}

function renderLegend(legend, rxSens) {
    const container = document.getElementById('cov-legend-items');
    container.innerHTML = '';

    const sorted = [...legend].sort((a, b) => b.threshold_dbm - a.threshold_dbm);

    sorted.forEach(entry => {
        const [r, g, b, a] = entry.rgba;
        const row = document.createElement('div');
        row.className = 'legend-row';
        row.innerHTML = `
            <span class="swatch" style="background: rgba(${r},${g},${b},${a / 255})"></span>
            <span class="legend-label">&ge; ${entry.threshold_dbm} dBm</span>
            <span class="legend-tier">${entry.label}</span>
        `;
        container.appendChild(row);
    });

    if (rxSens !== undefined && rxSens !== null) {
        const note = document.createElement('div');
        note.className = 'legend-note';
        note.textContent = `RX sensitivity: ${rxSens} dBm`;
        container.appendChild(note);
    }

    document.getElementById('cov-legend').classList.remove('hidden');
}

function addCoverageOverlay(pngBase64, bounds, legend, rxSens) {
    const minLat = bounds[0][0], minLon = bounds[0][1];
    const maxLat = bounds[1][0], maxLon = bounds[1][1];
    const coordinates = [
        [minLon, maxLat],
        [maxLon, maxLat],
        [maxLon, minLat],
        [minLon, minLat],
    ];

    const img = new Image();
    img.onload = () => {
        if (map.getSource('coverage-overlay')) {
            map.removeLayer('coverage-overlay-layer');
            map.removeSource('coverage-overlay');
        }
        map.addSource('coverage-overlay', {
            type: 'image',
            url: 'data:image/png;base64,' + pngBase64,
            coordinates,
        });
        map.addLayer({
            id: 'coverage-overlay-layer',
            type: 'raster',
            source: 'coverage-overlay',
            paint: { 'raster-opacity': 0.75 },
        }, 'path-line-layer');

        renderLegend(legend, rxSens);
    };
    img.src = 'data:image/png;base64,' + pngBase64;
}

function fnum(id, dflt) {
    const v = parseFloat(document.getElementById(id).value);
    return Number.isFinite(v) ? v : dflt;
}
function fint(id, dflt) {
    const v = parseInt(document.getElementById(id).value);
    return Number.isFinite(v) ? v : dflt;
}

async function runP2PAnalysis() {
    if (!txCoords || !rxCoords) {
        alert('Please select both TX and RX locations on the map.');
        return;
    }

    const btn = document.getElementById('analyze-btn');
    btn.textContent = 'Analyzing...';
    btn.disabled = true;

    try {
        const body = {
            tx: { lat: txCoords.lat, lon: txCoords.lng, h_m: fnum('tx-h', 30) },
            rx: { lat: rxCoords.lat, lon: rxCoords.lng, h_m: fnum('rx-h', 10) },
            freq_mhz: fnum('freq', 450),
            polarization: fint('polarization', 0),
            climate: fint('climate', 1),
            time_pct: fnum('time-pct', 50),
            location_pct: fnum('loc-pct', 50),
            situation_pct: fnum('sit-pct', 50),
            k_factor: fnum('k-factor', 4 / 3),
            tx_power_dbm: fnum('tx-power', 43),
            tx_gain_dbi: fnum('tx-gain', 8),
            rx_gain_dbi: fnum('rx-gain', 2),
            cable_loss_db: fnum('cable-loss', 2),
            rx_sensitivity_dbm: fnum('rx-sens', -100),
        };

        const response = await fetch(`${API_BASE}/api/p2p`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const text = await response.text();
            alert('Server error ' + response.status + ': ' + text.substring(0, 200));
            return;
        }

        const result = await response.json();
        if (result.error) { alert('Error: ' + result.error); return; }

        drawPathOnMap(txCoords, rxCoords);
        displayP2PResult(result);
        renderProfileChart(result);
        drawHorizons(result.horizons || [], txCoords, rxCoords, result.distance_m);
    clearInterval(progressInterval);
    } catch (err) {
        alert('Analysis failed: ' + err.message);
    } finally {
        btn.textContent = 'Analyze Path';
        btn.disabled = false;
    }
}

async function runCoverage() {
    if (!covTxCoords) {
        alert('Please select a TX location on the map.');
        return;
    }

    const btn = document.getElementById('coverage-btn');
    btn.textContent = 'Generating';
        let dotCount = 0;
        const progressInterval = setInterval(() => {
            dotCount = (dotCount + 1) % 4;
            btn.textContent = 'Generating' + '.'.repeat(dotCount);
        }, 500);
    btn.disabled = true;

    try {
        const pattern = document.getElementById('cov-ant-pattern').value;
        const body = {
            tx: { lat: covTxCoords.lat, lon: covTxCoords.lon, h_m: fnum('cov-tx-h', 30) },
            rx_h_m: fnum('cov-rx-h', 10),
            freq_mhz: fnum('cov-freq', 450),
            radius_km: computedCoverageRadius,
            grid_size: fint('cov-grid', 192),
            terrain_spacing_m: fnum('cov-terrain', 300),
            polarization: fint('cov-polarization', 0),
            climate: fint('cov-climate', 1),
            time_pct: fnum('cov-time-pct', 50),
            location_pct: fnum('cov-loc-pct', 50),
            situation_pct: fnum('cov-sit-pct', 50),
            tx_power_dbm: fnum('cov-tx-power', 43),
            tx_gain_dbi: fnum('cov-tx-gain', 8),
            rx_gain_dbi: fnum('cov-rx-gain', 2),
            cable_loss_db: fnum('cov-cable-loss', 2),
            rx_sensitivity_dbm: fnum('cov-rx-sens', -100),
            antenna_az_deg: pattern === 'dir' ? fnum('cov-ant-az', 0) : null,
            antenna_beamwidth_deg: pattern === 'dir' ? fnum('cov-ant-bw', 90) : 360,
        };

        const response = await fetch(`${API_BASE}/api/coverage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const text = await response.text();
            alert('Server error ' + response.status + ': ' + text.substring(0, 200));
            return;
        }

        const result = await response.json();
        if (!result.png_base64) {
            alert('No coverage data returned.');
            return;
        }

        currentCoverageResult = result;  // Store for multi-site saving
        addCoverageOverlay(result.png_base64, result.bounds, result.legend, result.rx_sensitivity_dbm);

        const s = result.stats || {};
        const covBox = document.getElementById('coverage-result');
        covBox.classList.remove('hidden');
        document.getElementById('coverage-status').innerHTML = `
            <div class="lb-table">
                <div><span>EIRP</span><span>${result.eirp_dbm} dBm</span></div>
                <div><span>Prx range</span><span>${s.prx_min_dbm?.toFixed(1)} to ${s.prx_max_dbm?.toFixed(1)} dBm</span></div>
                <div><span>ITM loss</span><span>${s.loss_min_db?.toFixed(1)} to ${s.loss_max_db?.toFixed(1)} dB</span></div>
                <div><span>Served area</span><span>${s.pct_above_sensitivity?.toFixed(1)}%</span></div>
                <div><span>Terrain grid</span><span>${s.terrain_grid_n}² @ ${s.terrain_spacing_m} m</span></div>
                <div><span>Terrain relief</span><span>${s.terrain_elev_min_m?.toFixed(0)} to ${s.terrain_elev_max_m?.toFixed(0)} m (σ ${s.terrain_elev_std_m} m)</span></div>
                <div><span>Cache</span><span>${result.from_cache ? 'hit' : 'miss'}</span></div>
            </div>
        `;
    clearInterval(progressInterval);
    } catch (err) {
        alert('Coverage generation failed: ' + err.message);
    } finally {
        clearInterval(progressInterval);
        btn.textContent = 'Generate Coverage';
        btn.disabled = false;
    }
}

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
            clickMode = tabId;
            if (tabId === 'p2p') {
                if (txMarker) txMarker.remove();
                if (rxMarker) rxMarker.remove();
                txMarker = null; rxMarker = null;
                txCoords = null; rxCoords = null;
            }
        });
    });
}

async function computeRadius() {
    if (!covTxCoords) {
        alert('Select TX location first');
        return;
    }

    const btn = document.getElementById('compute-radius-btn');
    const origText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Computing (1–2 min)...';

    try {
        const req = {
            tx: { lat: covTxCoords.lat, lon: covTxCoords.lon, h_m: fnum('cov-tx-h') },
            rx_h_m: fnum('cov-rx-h'),
            freq_mhz: fnum('cov-freq'),
            radius_km: 100,  // Dummy, not used for radius computation
            grid_size: 192,
            profile_step_m: 250,
            terrain_spacing_m: fnum('cov-terrain'),
            tx_power_dbm: fnum('cov-tx-power'),
            cable_loss_db: fnum('cov-cable-loss'),
            tx_gain_dbi: fnum('cov-tx-gain'),
            rx_gain_dbi: fnum('cov-rx-gain'),
            rx_sensitivity_dbm: fnum('cov-rx-sens'),
            antenna_az_deg: document.getElementById('cov-ant-pattern').value === 'dir' ? fnum('cov-ant-az') : null,
            antenna_beamwidth_deg: document.getElementById('cov-ant-pattern').value === 'dir' ? fnum('cov-ant-bw') : 360,
            polarization: fint('cov-polarization'),
            climate: fint('cov-climate'),
        };

        const res = await fetch('/api/coverage-radius', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req),
        });

        const data = await res.json();

        document.getElementById('radius-avg').textContent = data.avg_radius_km;
        document.getElementById('radius-min').textContent = data.min_radius_km;
        document.getElementById('radius-max').textContent = data.max_radius_km;
        document.getElementById('computed-radius').classList.remove('hidden');

        // Store computed radius and enable coverage button
        computedCoverageRadius = data.avg_radius_km;
        document.getElementById('coverage-btn').disabled = false;
    } catch (e) {
        console.error('Radius compute error:', e);
        alert('Error computing radius: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = origText;
    }
}

async function saveSiteToComparison() {
    if (!covTxCoords || !currentCoverageResult) {
        alert('Generate coverage first');
        return;
    }

    const name = prompt('Site name (e.g., "TX-A", "Transmitter 1"):', `Site ${sitesCoverage.length + 1}`);
    if (!name) return;

    const color = SITE_COLORS[sitesCoverage.length % SITE_COLORS.length];
    const site = new CoverageSite(name, covTxCoords, currentCoverageResult, color);
    sitesCoverage.push(site);

    addSiteLayer(site);
    updateSitesPanel();

    document.getElementById('sites-panel').classList.remove('hidden');
}

function addSiteLayer(site) {
    const layerId = `site-coverage-${site.id}`;
    const sourceId = `site-source-${site.id}`;

    map.addSource(sourceId, {
        type: 'image',
        url: `data:image/png;base64,${site.coverage_data.png_base64}`,
        coordinates: [
            [site.coverage_data.bounds[0][1], site.coverage_data.bounds[0][0]],
            [site.coverage_data.bounds[1][1], site.coverage_data.bounds[0][0]],
            [site.coverage_data.bounds[1][1], site.coverage_data.bounds[1][0]],
            [site.coverage_data.bounds[0][1], site.coverage_data.bounds[1][0]],
        ],
    });

    map.addLayer({
        id: layerId,
        type: 'raster',
        source: sourceId,
        paint: {
            'raster-opacity': site.opacity,
        },
    }, 'path-line');  // Insert before path-line so it's behind other elements
}

function updateSiteLayerVisibility(site) {
    const layerId = `site-coverage-${site.id}`;
    if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', site.visible ? 'visible' : 'none');
    }
}

function updateSiteLayerOpacity(site) {
    const layerId = `site-coverage-${site.id}`;
    if (map.getLayer(layerId)) {
        map.setPaintProperty(layerId, 'raster-opacity', site.opacity);
    }
}

function removeSiteLayer(site) {
    const layerId = `site-coverage-${site.id}`;
    const sourceId = `site-source-${site.id}`;
    if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
    }
    if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
    }
}

function computeSitesStatistics() {
    if (sitesCoverage.length === 0) return null;

    // Compute aggregate stats from all visible sites
    let totalPixels = 0;
    let totalServed = 0;
    let coverageAreas = [];

    for (const site of sitesCoverage) {
        if (!site.visible) continue;
        const stats = site.coverage_data.stats;
        totalPixels += stats.pixels_total;
        totalServed += stats.pixels_valid * (stats.pct_above_sensitivity / 100);
        coverageAreas.push(stats.pct_above_sensitivity);
    }

    const avgCoverage = coverageAreas.length > 0 ? (coverageAreas.reduce((a,b) => a+b) / coverageAreas.length).toFixed(1) : 0;

    return {
        numSites: sitesCoverage.filter(s => s.visible).length,
        avgCoveragePct: avgCoverage,
        totalPixels,
        totalServed: totalServed.toFixed(0),
    };
}

function updateSitesPanel() {
    const listDiv = document.getElementById('sites-list');
    const statsDiv = document.getElementById('sites-stats');

    // Update site list
    listDiv.innerHTML = sitesCoverage.map(site => `
        <div style="display:flex; align-items:center; margin-bottom:8px; padding:8px; background:rgba(255,255,255,0.05); border-radius:4px;">
            <input type="checkbox" id="site-toggle-${site.id}" ${site.visible ? 'checked' : ''} style="margin-right:8px;">
            <div style="flex:1; min-width:0;">
                <div style="color:${site.color}; font-weight:bold; margin-bottom:2px;">${site.name}</div>
                <div style="font-size:10px; color:#999;">${site.tx.lat.toFixed(3)}°, ${site.tx.lon.toFixed(3)}°</div>
            </div>
            <div style="display:flex; flex-direction:column; gap:2px;">
                <input type="range" id="site-opacity-${site.id}" min="0" max="1" step="0.1" value="${site.opacity}" style="width:60px; height:4px;">
                <button class="btn" id="site-delete-${site.id}" style="padding:2px 6px; font-size:10px;">✕</button>
            </div>
        </div>
    `).join('');

    // Attach event listeners
    sitesCoverage.forEach(site => {
        const toggle = document.getElementById(`site-toggle-${site.id}`);
        const opacity = document.getElementById(`site-opacity-${site.id}`);
        const delBtn = document.getElementById(`site-delete-${site.id}`);

        if (toggle) toggle.addEventListener('change', e => {
            site.visible = e.target.checked;
            updateSiteLayerVisibility(site);
            updateSitesPanel();  // Refresh stats
        });

        if (opacity) opacity.addEventListener('input', e => {
            site.opacity = parseFloat(e.target.value);
            updateSiteLayerOpacity(site);
        });

        if (delBtn) delBtn.addEventListener('click', () => {
            removeSiteLayer(site);
            sitesCoverage = sitesCoverage.filter(s => s.id !== site.id);
            updateSitesPanel();
            if (sitesCoverage.length === 0) {
                document.getElementById('sites-panel').classList.add('hidden');
            }
        });
    });

    // Update statistics
    const stats = computeSitesStatistics();
    if (stats) {
        statsDiv.innerHTML = `
            <div><strong>Active Sites:</strong> ${stats.numSites}</div>
            <div><strong>Avg Coverage:</strong> ${stats.avgCoveragePct}%</div>
            <div style="margin-top:4px; font-size:10px; color:#ccc;">Blended view shows all sites</div>
        `;
    }
}

let currentCoverageResult = null;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    setupTabs();

    document.getElementById('analyze-btn').addEventListener('click', runP2PAnalysis);
    document.getElementById('coverage-btn').addEventListener('click', runCoverage);
    document.getElementById('compute-radius-btn').addEventListener('click', computeRadius);
    document.getElementById('save-site-btn').addEventListener('click', saveSiteToComparison);
    document.getElementById('coverage-opacity').addEventListener('input', e => {
        const opacity = parseFloat(e.target.value);
        document.getElementById('coverage-opacity-label').textContent = Math.round(opacity * 100) + '%';
        if (map.getLayer('coverage-overlay-layer')) {
            map.setPaintProperty('coverage-overlay-layer', 'raster-opacity', opacity);
        }
    });
    document.getElementById('sites-close').addEventListener('click', () => {
        document.getElementById('sites-panel').classList.add('hidden');
    });
    document.getElementById('clear-sites-btn').addEventListener('click', () => {
        if (confirm('Clear all saved sites?')) {
            sitesCoverage.forEach(site => removeSiteLayer(site));
            sitesCoverage = [];
            document.getElementById('sites-panel').classList.add('hidden');
        }
    });
    document.getElementById('chart-close').addEventListener('click', () => {
        document.getElementById('chart-panel').classList.add('hidden');
        setTimeout(() => map.resize(), 100);
    });
    document.getElementById('cov-ant-pattern').addEventListener('change', e => {
        document.getElementById('cov-ant-dir-row').style.display =
            e.target.value === 'dir' ? 'grid' : 'none';
    });
});
