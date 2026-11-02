"""
Dashboard HTML served inline by the Cloudflare Python Worker.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EarthMind — Environmental Monitoring</title>
  <link rel="stylesheet" href="https://design.alphaonelabs.com/brand.css">
  <script src="https://design.alphaonelabs.com/chrome.js" defer></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    /* Site tokens mapped onto the Alpha One Labs brand (design.alphaonelabs.com) */
    :root {
      --bg: var(--a1-bg, #000);
      --surface: var(--a1-surface, #0d0d0d);
      --surface2: var(--a1-surface-raised, #1a1a1a);
      --border: var(--a1-border, #2e2e2e);
      --text: var(--a1-text, #fff);
      --muted: var(--a1-text-muted, #a3a3a3);
      --accent: var(--a1-accent, #c7ab4f);
      --accent-hover: var(--a1-accent-hover, #e2c66a);
      --focus: var(--a1-focus, #e2c66a);
      /* status colours: tuned per theme for AA contrast */
      --warning: #ffb347;
      --danger: #ff7a7a;
      --info: #9ecbff;
      --map-filter: invert(1) hue-rotate(180deg) brightness(0.95) contrast(0.9);
      --hover-tint: rgba(255,255,255,0.04);
    }
    @media (prefers-color-scheme: light) {
      :root:not([data-a1-theme="dark"]) { --warning: #9a5800; --danger: #c0262d; --info: #1f5fa8; --map-filter: none; --hover-tint: rgba(0,0,0,0.03); }
    }
    :root[data-a1-theme="light"] { --warning: #9a5800; --danger: #c0262d; --info: #1f5fa8; --map-filter: none; --hover-tint: rgba(0,0,0,0.03); }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: var(--a1-font-body, system-ui, sans-serif); min-height: 100vh; line-height: 1.5; }
    a1-header { display: block; min-height: 65px; background: var(--bg); }
    :focus-visible { outline: 2px solid var(--focus); outline-offset: 3px; }
    .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }

    /* Page intro */
    .page-intro { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
    .page-intro h1 { font-family: var(--a1-font-display, sans-serif); font-size: var(--a1-text-3xl, 2.25rem); font-weight: 700; letter-spacing: -0.03em; line-height: 1.05; }
    .page-intro h1 span { color: var(--accent); }
    .eyebrow { font-family: var(--a1-font-mono, monospace); font-size: 0.75rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent); margin-bottom: 6px; }
    .header-info { font-size: 0.95rem; color: var(--muted); }
    .maker-art { width: 88px; height: 88px; flex: none; background: var(--accent); -webkit-mask: url("https://design.alphaonelabs.com/assets/illustrations/iss.svg") center / contain no-repeat; mask: url("https://design.alphaonelabs.com/assets/illustrations/iss.svg") center / contain no-repeat; }
    .a1-trace { margin: 0 0 24px; }
    @media (max-width: 480px) { .maker-art { width: 56px; height: 56px; } }
    .live { margin-left: auto; display: inline-flex; align-items: center; gap: 8px; font-family: var(--a1-font-mono, monospace); font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
    .status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    @media (prefers-reduced-motion: reduce) { .status-dot, .loading { animation: none !important; } }

    /* Layout */
    .container { max-width: 1400px; margin: 0 auto; padding: 32px 24px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
    .grid-2 > * { min-width: 0; }
    .grid-full { margin-bottom: 20px; }
    @media (max-width: 900px) { .grid-3, .grid-2 { grid-template-columns: 1fr; } }
    @media (max-width: 480px) { .container { padding: 20px 16px; } .card { padding: 16px; } }

    /* Cards */
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--a1-radius, 12px); padding: 20px; }
    .card-title { font-family: var(--a1-font-mono, monospace); font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.14em; color: var(--accent); margin-bottom: 12px; }
    .metric-value { font-family: var(--a1-font-display, sans-serif); font-size: 2.2rem; font-weight: 700; color: var(--text); line-height: 1; }
    .metric-label { font-size: 0.8rem; color: var(--muted); margin-top: 6px; }
    .metric-change { font-size: 0.85rem; margin-top: 8px; }
    .metric-change.up { color: var(--warning); }
    .metric-change.down { color: var(--info); }

    /* Map: OpenStreetMap tiles, darkened to sit on the black theme */
    #map { height: 400px; border-radius: 8px; background: var(--surface2); isolation: isolate; z-index: 0; }
    #map .leaflet-tile-pane { filter: var(--map-filter); }
    #map .leaflet-control-attribution { background: var(--surface); color: var(--muted); opacity: 0.92; }
    #map .leaflet-control-attribution a { color: var(--accent); }
    #map .leaflet-popup-content-wrapper, #map .leaflet-popup-tip { background: var(--surface2); color: var(--text); }
    #map .leaflet-bar a { background: var(--surface2); color: var(--text); border-color: var(--border); }
    @media (max-width: 480px) { #map { height: 300px; } }

    /* Charts */
    .chart-container { position: relative; height: 260px; }

    /* Parameter selector */
    .controls { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
    select, button {
      background: var(--surface2); border: 1px solid var(--border); color: var(--text);
      padding: 8px 14px; border-radius: var(--a1-radius-full, 999px); font: 500 0.875rem/1.2 var(--a1-font-body, sans-serif); cursor: pointer; min-height: 40px;
    }
    select { border-radius: 8px; }
    button:hover { border-color: var(--accent); color: var(--accent); }
    button.active { border-color: var(--accent); color: var(--accent); background: rgba(199,171,79,0.1); }
    button:disabled { opacity: 0.6; cursor: wait; }

    /* Alerts */
    .alert-list { max-height: 300px; overflow-y: auto; }
    .alert-item { display: flex; gap: 12px; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid var(--border); }
    .alert-item:last-child { border-bottom: none; }
    .severity-badge {
      font: 700 0.7rem/1.2 var(--a1-font-mono, monospace); text-transform: uppercase; padding: 3px 8px;
      border-radius: 20px; white-space: nowrap; letter-spacing: 0.06em; display: inline-block;
    }
    .sev-critical { background: rgba(255,122,122,0.15); color: var(--danger); border: 1px solid var(--danger); }
    .sev-high { background: rgba(255,179,71,0.15); color: var(--warning); border: 1px solid var(--warning); }
    .sev-medium { background: rgba(158,203,255,0.12); color: var(--info); border: 1px solid var(--info); }
    .sev-low { background: rgba(199,171,79,0.1); color: var(--accent); border: 1px solid var(--accent); }
    .alert-msg { font-size: 0.875rem; }
    .alert-time { font-size: 0.75rem; color: var(--muted); margin-top: 4px; }
    .resolve-btn { margin-left: auto; font-size: 0.75rem; padding: 4px 10px; min-height: 32px; }

    /* AI Insights */
    .insight-text { font-size: 0.9rem; line-height: 1.7; color: var(--text); overflow-wrap: anywhere; }
    .insight-text p { margin-bottom: 10px; }
    .loading { color: var(--muted); font-size: 0.875rem; animation: pulse 1.5s infinite; }

    /* Anomaly table */
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th { text-align: left; color: var(--muted); font-weight: 600; padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 0.78rem; text-transform: uppercase; }
    td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: var(--hover-tint); }

    /* Risk indicator */
    .risk-indicator { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
    .risk-bar { flex: 1; height: 8px; border-radius: 4px; background: var(--border); overflow: hidden; }
    .risk-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
    .risk-low .risk-fill { background: var(--accent); width: 20%; }
    .risk-medium .risk-fill { background: var(--warning); width: 55%; }
    .risk-high .risk-fill { background: var(--danger); width: 90%; }

    /* Credits */
    .credits { text-align: center; padding: 8px 0 24px; color: var(--muted); font-size: 0.8rem; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { color: var(--accent-hover); text-decoration: underline; }
  </style>
</head>
<body>
  <a1-header site="EarthMind" site-href="/" sticky></a1-header>

  <main class="container" id="main">

    <div class="page-intro">
      <div class="maker-art" aria-hidden="true"></div>
      <div>
        <p class="eyebrow">Alpha One Labs</p>
        <h1>Earth<span>Mind</span></h1>
        <p class="header-info">AI-powered environmental monitoring</p>
      </div>
      <div class="live"><span class="status-dot" aria-hidden="true"></span>Live</div>
    </div>
    <hr class="a1-trace">

    <!-- Summary metrics -->
    <div class="grid-3">
      <div class="card">
        <h2 class="card-title">Active Sensors</h2>
        <div class="metric-value" id="metric-sensors">—</div>
        <div class="metric-label">reporting sources</div>
      </div>
      <div class="card">
        <h2 class="card-title">Active Alerts</h2>
        <div class="metric-value" id="metric-alerts" style="color:var(--warning)">—</div>
        <div class="metric-label">require attention</div>
      </div>
      <div class="card">
        <h2 class="card-title">Anomalies (24 h)</h2>
        <div class="metric-value" id="metric-anomalies" style="color:var(--danger)">—</div>
        <div class="metric-label">detected deviations</div>
      </div>
    </div>

    <!-- AI Dashboard Summary -->
    <div class="grid-full card">
      <h2 class="card-title"><span aria-hidden="true">🤖</span> AI Insights — Executive Summary</h2>
      <div id="ai-summary" aria-live="polite" class="insight-text loading">Loading AI analysis…</div>
    </div>

    <!-- Map + Alerts -->
    <div class="grid-2">
      <div class="card">
        <h2 class="card-title"><span aria-hidden="true">📍</span> Geospatial Overview</h2>
        <div class="controls">
          <label class="sr-only" for="map-param-filter">Map parameter</label>
          <select id="map-param-filter" onchange="refreshMap()">
            <option value="">All Parameters</option>
            <option value="pm2_5">PM2.5</option>
            <option value="co2">CO₂</option>
            <option value="temperature">Temperature</option>
            <option value="ph">pH</option>
            <option value="no2">NO₂</option>
            <option value="humidity">Humidity</option>
            <option value="noise_db">Noise</option>
          </select>
          <button onclick="refreshMap()">Refresh Map</button>
        </div>
        <div id="map" role="region" aria-label="Map of sensor readings"></div>
      </div>
      <div class="card">
        <h2 class="card-title"><span aria-hidden="true">🚨</span> Active Alerts</h2>
        <div class="controls">
          <label class="sr-only" for="alert-severity-filter">Alert severity</label>
          <select id="alert-severity-filter" onchange="loadAlerts()">
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <button onclick="loadAlerts()">Refresh</button>
        </div>
        <div id="alert-list" class="alert-list"><span class="loading">Loading alerts…</span></div>
      </div>
    </div>

    <!-- Trend Chart -->
    <div class="card grid-full">
      <h2 class="card-title"><span aria-hidden="true">📈</span> Trend Analysis</h2>
      <div class="controls">
        <label class="sr-only" for="trend-param">Trend parameter</label>
        <select id="trend-param" onchange="loadTrendChart()">
          <option value="pm2_5">PM2.5 (µg/m³)</option>
          <option value="co2">CO₂ (ppm)</option>
          <option value="temperature">Temperature (°C)</option>
          <option value="ph">pH</option>
          <option value="no2">NO₂ (µg/m³)</option>
          <option value="humidity">Humidity (%)</option>
          <option value="noise_db">Noise (dB)</option>
        </select>
        <button onclick="loadTrendChart()">Update Chart</button>
        <span id="trend-summary" aria-live="polite" style="font-size:0.85rem; color:var(--muted); margin-left:8px;"></span>
      </div>
      <div class="chart-container">
        <canvas id="trend-chart" role="img" aria-label="Line chart of recent readings for the selected parameter with a 5-point moving average"></canvas>
      </div>
    </div>

    <!-- AI Trend Analysis + Risk Assessment -->
    <div class="grid-2">
      <div class="card">
        <h2 class="card-title"><span aria-hidden="true">🧠</span> AI Trend Narrative</h2>
        <div id="ai-trend" class="insight-text loading">Select a parameter above to analyse.</div>
      </div>
      <div class="card">
        <h2 class="card-title"><span aria-hidden="true">⚠️</span> Ecological Risk Assessment</h2>
        <div id="ai-risk" class="insight-text loading">Loading risk assessment…</div>
      </div>
    </div>

    <!-- Anomalies Table -->
    <div class="card grid-full">
      <h2 class="card-title"><span aria-hidden="true">🔍</span> Detected Anomalies</h2>
      <div class="controls">
        <label class="sr-only" for="anomaly-param">Anomaly parameter</label>
        <select id="anomaly-param" onchange="loadAnomalies()">
          <option value="pm2_5">PM2.5</option>
          <option value="co2">CO₂</option>
          <option value="temperature">Temperature</option>
          <option value="ph">pH</option>
          <option value="no2">NO₂</option>
        </select>
        <button onclick="loadAnomalies()">Detect Anomalies</button>
        <button onclick="explainTopAnomaly()"><span aria-hidden="true">🤖</span> Explain with AI</button>
      </div>
      <div id="anomaly-table">
        <span class="loading">Select a parameter to run anomaly detection.</span>
      </div>
      <div id="anomaly-explanation" aria-live="polite" style="margin-top:14px; font-size:0.875rem; color:var(--info); display:none;"></div>
    </div>

    <p class="credits">
      EarthMind &mdash; open-source environmental intelligence &bull;
      Powered by <a href="https://workers.cloudflare.com">Cloudflare Workers</a> &amp;
      <a href="https://developers.cloudflare.com/workers-ai/">Workers AI</a> &bull;
      Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors
    </p>

  </main>

  <a1-footer source="earthmind"></a1-footer>

  <script>
  // ──────────────────────────────────────────────
  // State
  let map = null;
  let trendChart = null;
  let markers = [];

  // Read brand/site colour tokens so canvas + map colours follow the light/dark theme
  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  document.addEventListener('a1-themechange', () => {
    // let the new token values apply before re-reading them
    requestAnimationFrame(() => { loadTrendChart(); refreshMap(); });
  });

  // ──────────────────────────────────────────────
  // Initialise
  document.addEventListener('DOMContentLoaded', async () => {
    initMap();
    await Promise.all([
      loadMetrics(),
      loadAlerts(),
      loadTrendChart(),
      loadAiSummary(),
      loadRiskAssessment(),
    ]);
    refreshMap();
  });

  // ──────────────────────────────────────────────
  // Map
  function initMap() {
    map = L.map('map').setView([40.7128, -74.0060], 11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);
  }

  async function refreshMap() {
    const param = document.getElementById('map-param-filter').value;
    const url = '/api/geo' + (param ? `?parameter=${param}` : '');
    try {
      const res = await fetch(url);
      const geojson = await res.json();
      markers.forEach(m => map.removeLayer(m));
      markers = [];
      const colourForValue = (parameter, value) => {
        const thresholds = { pm2_5: 35, co2: 1000, temperature: 35, no2: 40, ph: 8.5 };
        const t = thresholds[parameter];
        if (!t) return cssVar('--accent');
        if (value > t * 1.5) return cssVar('--danger');
        if (value > t) return cssVar('--warning');
        return cssVar('--accent');
      };
      (geojson.features || []).forEach(f => {
        const [lng, lat] = f.geometry.coordinates;
        const p = f.properties;
        const colour = colourForValue(p.parameter, p.value);
        const circle = L.circleMarker([lat, lng], {
          radius: 9, fillColor: colour, color: cssVar('--bg'), weight: 2,
          opacity: 1, fillOpacity: 0.85,
        }).addTo(map);
        circle.bindPopup(
          `<b>${p.location || p.source}</b><br/>` +
          `${p.parameter}: <b>${p.value} ${p.unit || ''}</b><br/>` +
          `<small>${p.timestamp}</small>`
        );
        markers.push(circle);
      });
    } catch (e) {
      console.error('Map load error', e);
    }
  }

  // ──────────────────────────────────────────────
  // Metrics
  async function loadMetrics() {
    try {
      const [readingsRes, alertsRes] = await Promise.all([
        fetch('/api/data?limit=500'),
        fetch('/api/alerts?active=true'),
      ]);
      const readingsData = await readingsRes.json();
      const alertsData = await alertsRes.json();

      const sources = new Set((readingsData.data || []).map(r => r.source));
      document.getElementById('metric-sensors').textContent = sources.size;
      document.getElementById('metric-alerts').textContent = alertsData.count || 0;
    } catch (e) { console.error('Metrics error', e); }
  }

  // ──────────────────────────────────────────────
  // Alerts
  async function loadAlerts() {
    const severity = document.getElementById('alert-severity-filter').value;
    const url = '/api/alerts?active=true' + (severity ? `&severity=${severity}` : '');
    const container = document.getElementById('alert-list');
    container.innerHTML = '<span class="loading">Loading…</span>';
    try {
      const res = await fetch(url);
      const data = await res.json();
      const alerts = data.alerts || [];
      if (!alerts.length) {
        container.innerHTML = '<p style="color:var(--muted); font-size:0.875rem;">No active alerts.</p>';
        return;
      }
      container.innerHTML = alerts.map(a => `
        <div class="alert-item">
          <div>
            <span class="severity-badge sev-${a.severity}">${a.severity}</span>
          </div>
          <div style="flex:1">
            <div class="alert-msg">${a.message}</div>
            <div class="alert-time">${a.created_at} · ${a.type}</div>
          </div>
          <button class="resolve-btn" onclick="resolveAlert(${a.id}, this)" aria-label="Resolve alert ${a.id}">Resolve</button>
        </div>
      `).join('');
    } catch (e) {
      container.innerHTML = '<p style="color:var(--danger)">Failed to load alerts.</p>';
    }
  }

  async function resolveAlert(id, btn) {
    btn.disabled = true;
    btn.textContent = '…';
    try {
      await fetch(`/api/alerts/${id}/resolve`, { method: 'PUT' });
      loadAlerts();
      loadMetrics();
    } catch (e) { btn.textContent = 'Resolve'; btn.disabled = false; }
  }

  // ──────────────────────────────────────────────
  // Trend Chart
  async function loadTrendChart() {
    const param = document.getElementById('trend-param').value;
    const summaryEl = document.getElementById('trend-summary');
    summaryEl.textContent = 'Loading…';
    try {
      const res = await fetch(`/api/trends?parameter=${param}&limit=100`);
      const data = await res.json();
      const trend = data.trend || {};
      const readRes = await fetch(`/api/data?parameter=${param}&limit=100`);
      const readData = await readRes.json();
      const readings = (readData.data || []).reverse();
      const labels = readings.map(r => r.timestamp ? r.timestamp.slice(11, 16) : '');
      const values = readings.map(r => r.value);
      const sma = computeSMA(values, 5);

      if (trendChart) trendChart.destroy();
      const cAccent = cssVar('--accent'), cText = cssVar('--text'), cMuted = cssVar('--muted'), cGrid = cssVar('--border');
      const ctx = document.getElementById('trend-chart').getContext('2d');
      trendChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: param,
              data: values,
              borderColor: cAccent,
              backgroundColor: cAccent + '1f',
              borderWidth: 2,
              pointRadius: 3,
              tension: 0.3,
              fill: true,
            },
            {
              label: 'SMA(5)',
              data: sma,
              borderColor: cText,
              borderWidth: 1.5,
              pointRadius: 0,
              borderDash: [4, 4],
              tension: 0.3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: cMuted, font: { size: 12 } } },
            tooltip: { mode: 'index', intersect: false },
          },
          scales: {
            x: { ticks: { color: cMuted, maxTicksLimit: 12 }, grid: { color: cGrid } },
            y: { ticks: { color: cMuted }, grid: { color: cGrid } },
          },
        },
      });

      const dir = (trend.linear || {}).direction || 'stable';
      const risk = trend.risk_level || 'low';
      summaryEl.textContent = `Direction: ${dir} | Risk: ${risk.toUpperCase()}`;

      // Load AI trend narrative
      loadAiTrendNarrative(param);
    } catch (e) {
      summaryEl.textContent = 'Failed to load';
      console.error(e);
    }
  }

  function computeSMA(values, window) {
    return values.map((_, i) => {
      if (i < window - 1) return null;
      const slice = values.slice(i - window + 1, i + 1);
      return slice.reduce((a, b) => a + b, 0) / window;
    });
  }

  // ──────────────────────────────────────────────
  // Anomaly Detection
  async function loadAnomalies() {
    const param = document.getElementById('anomaly-param').value;
    const container = document.getElementById('anomaly-table');
    container.innerHTML = '<span class="loading">Running anomaly detection…</span>';
    document.getElementById('anomaly-explanation').style.display = 'none';
    try {
      const res = await fetch(`/api/anomalies?parameter=${param}`);
      const data = await res.json();
      const report = (data.anomalies || {});
      const summary = report.summary || [];
      document.getElementById('metric-anomalies').textContent = report.total_anomalies || 0;
      if (!summary.length) {
        container.innerHTML = '<p style="color:var(--accent);font-size:0.875rem;">No anomalies detected.</p>';
        return;
      }
      container.innerHTML = `
        <div class="table-wrap"><table>
          <thead><tr>
            <th scope="col">Index</th><th scope="col">Actual</th><th scope="col">Expected</th>
            <th scope="col">Deviation</th><th scope="col">Method</th><th scope="col">Severity</th><th scope="col">Timestamp</th>
          </tr></thead>
          <tbody>
            ${summary.map(a => `
              <tr>
                <td>${a.index}</td>
                <td>${a.actual_value}</td>
                <td>${a.expected_value}</td>
                <td>${a.deviation}</td>
                <td>${a.method}</td>
                <td><span class="severity-badge sev-${a.severity}">${a.severity}</span></td>
                <td>${a.timestamp || '—'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table></div>
      `;
    } catch (e) {
      container.innerHTML = '<p style="color:var(--danger)">Failed to detect anomalies.</p>';
    }
  }

  async function explainTopAnomaly() {
    const param = document.getElementById('anomaly-param').value;
    const el = document.getElementById('anomaly-explanation');
    el.style.display = 'block';
    el.textContent = '🤖 Asking AI to explain the top anomaly…';
    try {
      const res = await fetch(`/api/analytics/anomaly-explain?parameter=${param}`);
      const data = await res.json();
      el.textContent = data.explanation || 'No explanation available.';
    } catch (e) { el.textContent = 'AI explanation unavailable.'; }
  }

  // ──────────────────────────────────────────────
  // AI Sections
  async function loadAiSummary() {
    const el = document.getElementById('ai-summary');
    try {
      const res = await fetch('/api/analytics/summary');
      const data = await res.json();
      el.className = 'insight-text';
      el.innerHTML = (data.summary || 'No summary available.').replace(/\\n/g, '<br>');
    } catch (e) {
      el.className = 'insight-text';
      el.textContent = 'AI summary unavailable.';
    }
  }

  async function loadAiTrendNarrative(param) {
    const el = document.getElementById('ai-trend');
    el.className = 'insight-text loading';
    el.textContent = 'Generating AI analysis…';
    try {
      const res = await fetch(`/api/analytics/trends?parameter=${param}`);
      const data = await res.json();
      el.className = 'insight-text';
      el.innerHTML = (data.analysis || 'No analysis.').replace(/\\n/g, '<br>');
    } catch (e) {
      el.className = 'insight-text';
      el.textContent = 'AI analysis unavailable.';
    }
  }

  async function loadRiskAssessment() {
    const el = document.getElementById('ai-risk');
    try {
      const res = await fetch('/api/analytics/risk');
      const data = await res.json();
      el.className = 'insight-text';
      el.innerHTML = (data.risk_assessment || 'No assessment.').replace(/\\n/g, '<br>');
    } catch (e) {
      el.className = 'insight-text';
      el.textContent = 'Risk assessment unavailable.';
    }
  }
  </script>
</body>
</html>"""
