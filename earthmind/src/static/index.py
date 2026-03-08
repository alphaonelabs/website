"""
Dashboard HTML served inline by the Cloudflare Python Worker.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EarthMind — Environmental Monitoring</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    :root {
      --bg: #0f1117;
      --surface: #1a1e2e;
      --surface2: #232840;
      --border: #2e3455;
      --text: #e2e8f0;
      --muted: #8892b0;
      --accent: #64ffda;
      --warning: #ffb347;
      --danger: #ff6b6b;
      --info: #74b9ff;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }

    /* Header */
    header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 24px; display: flex; align-items: center; gap: 16px; }
    .logo { font-size: 1.4rem; font-weight: 700; color: var(--accent); letter-spacing: -0.5px; }
    .logo span { color: var(--text); }
    .status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); animation: pulse 2s infinite; margin-left: auto; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .header-info { font-size: 0.85rem; color: var(--muted); }

    /* Layout */
    .container { max-width: 1400px; margin: 0 auto; padding: 20px 24px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
    .grid-full { margin-bottom: 20px; }
    @media (max-width: 900px) { .grid-3, .grid-2 { grid-template-columns: 1fr; } }

    /* Cards */
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
    .card-title { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 12px; }
    .metric-value { font-size: 2.2rem; font-weight: 700; color: var(--accent); line-height: 1; }
    .metric-label { font-size: 0.8rem; color: var(--muted); margin-top: 6px; }
    .metric-change { font-size: 0.85rem; margin-top: 8px; }
    .metric-change.up { color: var(--warning); }
    .metric-change.down { color: var(--info); }

    /* Map */
    #map { height: 400px; border-radius: 8px; }

    /* Charts */
    .chart-container { position: relative; height: 260px; }

    /* Parameter selector */
    .controls { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
    select, button {
      background: var(--surface2); border: 1px solid var(--border); color: var(--text);
      padding: 8px 14px; border-radius: 8px; font-size: 0.875rem; cursor: pointer;
    }
    button:hover { border-color: var(--accent); color: var(--accent); }
    button.active { border-color: var(--accent); color: var(--accent); background: rgba(100,255,218,0.08); }

    /* Alerts */
    .alert-list { max-height: 300px; overflow-y: auto; }
    .alert-item { display: flex; gap: 12px; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid var(--border); }
    .alert-item:last-child { border-bottom: none; }
    .severity-badge {
      font-size: 0.7rem; font-weight: 700; text-transform: uppercase; padding: 3px 8px;
      border-radius: 20px; white-space: nowrap; letter-spacing: 0.06em;
    }
    .sev-critical { background: rgba(255,107,107,0.2); color: var(--danger); border: 1px solid var(--danger); }
    .sev-high { background: rgba(255,179,71,0.2); color: var(--warning); border: 1px solid var(--warning); }
    .sev-medium { background: rgba(116,185,255,0.2); color: var(--info); border: 1px solid var(--info); }
    .sev-low { background: rgba(100,255,218,0.1); color: var(--accent); border: 1px solid var(--accent); }
    .alert-msg { font-size: 0.875rem; }
    .alert-time { font-size: 0.75rem; color: var(--muted); margin-top: 4px; }
    .resolve-btn { margin-left: auto; font-size: 0.75rem; padding: 4px 10px; }

    /* AI Insights */
    .insight-text { font-size: 0.9rem; line-height: 1.7; color: var(--text); }
    .insight-text p { margin-bottom: 10px; }
    .loading { color: var(--muted); font-size: 0.875rem; animation: pulse 1.5s infinite; }

    /* Anomaly table */
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th { text-align: left; color: var(--muted); font-weight: 600; padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 0.78rem; text-transform: uppercase; }
    td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255,255,255,0.02); }

    /* Risk indicator */
    .risk-indicator { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
    .risk-bar { flex: 1; height: 8px; border-radius: 4px; background: var(--border); overflow: hidden; }
    .risk-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
    .risk-low .risk-fill { background: var(--accent); width: 20%; }
    .risk-medium .risk-fill { background: var(--warning); width: 55%; }
    .risk-high .risk-fill { background: var(--danger); width: 90%; }

    /* Footer */
    footer { text-align: center; padding: 24px; color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 40px; }
    a { color: var(--accent); text-decoration: none; }
  </style>
</head>
<body>
  <header>
    <div class="logo">Earth<span>Mind</span></div>
    <div class="header-info">AI-Powered Environmental Monitoring</div>
    <div class="status-dot" title="Live"></div>
  </header>

  <div class="container">

    <!-- Summary metrics -->
    <div class="grid-3">
      <div class="card">
        <div class="card-title">Active Sensors</div>
        <div class="metric-value" id="metric-sensors">—</div>
        <div class="metric-label">reporting sources</div>
      </div>
      <div class="card">
        <div class="card-title">Active Alerts</div>
        <div class="metric-value" id="metric-alerts" style="color:var(--warning)">—</div>
        <div class="metric-label">require attention</div>
      </div>
      <div class="card">
        <div class="card-title">Anomalies (24 h)</div>
        <div class="metric-value" id="metric-anomalies" style="color:var(--danger)">—</div>
        <div class="metric-label">detected deviations</div>
      </div>
    </div>

    <!-- AI Dashboard Summary -->
    <div class="grid-full card">
      <div class="card-title">🤖 AI Insights — Executive Summary</div>
      <div id="ai-summary" class="insight-text loading">Loading AI analysis…</div>
    </div>

    <!-- Map + Alerts -->
    <div class="grid-2">
      <div class="card">
        <div class="card-title">📍 Geospatial Overview</div>
        <div class="controls">
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
        <div id="map"></div>
      </div>
      <div class="card">
        <div class="card-title">🚨 Active Alerts</div>
        <div class="controls">
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
      <div class="card-title">📈 Trend Analysis</div>
      <div class="controls">
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
        <span id="trend-summary" style="font-size:0.85rem; color:var(--muted); margin-left:8px;"></span>
      </div>
      <div class="chart-container">
        <canvas id="trend-chart"></canvas>
      </div>
    </div>

    <!-- AI Trend Analysis + Risk Assessment -->
    <div class="grid-2">
      <div class="card">
        <div class="card-title">🧠 AI Trend Narrative</div>
        <div id="ai-trend" class="insight-text loading">Select a parameter above to analyse.</div>
      </div>
      <div class="card">
        <div class="card-title">⚠️ Ecological Risk Assessment</div>
        <div id="ai-risk" class="insight-text loading">Loading risk assessment…</div>
      </div>
    </div>

    <!-- Anomalies Table -->
    <div class="card grid-full">
      <div class="card-title">🔍 Detected Anomalies</div>
      <div class="controls">
        <select id="anomaly-param" onchange="loadAnomalies()">
          <option value="pm2_5">PM2.5</option>
          <option value="co2">CO₂</option>
          <option value="temperature">Temperature</option>
          <option value="ph">pH</option>
          <option value="no2">NO₂</option>
        </select>
        <button onclick="loadAnomalies()">Detect Anomalies</button>
        <button onclick="explainTopAnomaly()">🤖 Explain with AI</button>
      </div>
      <div id="anomaly-table">
        <span class="loading">Select a parameter to run anomaly detection.</span>
      </div>
      <div id="anomaly-explanation" style="margin-top:14px; font-size:0.875rem; color:var(--info); display:none;"></div>
    </div>

  </div>

  <footer>
    EarthMind &mdash; Open-source environmental intelligence &bull;
    <a href="https://github.com/alphaonelabs/earthmind" target="_blank">GitHub</a> &bull;
    Powered by <a href="https://workers.cloudflare.com" target="_blank">Cloudflare Workers</a> &amp;
    <a href="https://developers.cloudflare.com/workers-ai/" target="_blank">Workers AI</a>
  </footer>

  <script>
  // ──────────────────────────────────────────────
  // State
  let map = null;
  let trendChart = null;
  let markers = [];

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
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap, © CARTO',
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
        if (!t) return '#64ffda';
        if (value > t * 1.5) return '#ff6b6b';
        if (value > t) return '#ffb347';
        return '#64ffda';
      };
      (geojson.features || []).forEach(f => {
        const [lng, lat] = f.geometry.coordinates;
        const p = f.properties;
        const colour = colourForValue(p.parameter, p.value);
        const circle = L.circleMarker([lat, lng], {
          radius: 9, fillColor: colour, color: '#0f1117', weight: 2,
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
          <button class="resolve-btn" onclick="resolveAlert(${a.id}, this)">Resolve</button>
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
      const ctx = document.getElementById('trend-chart').getContext('2d');
      trendChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: param,
              data: values,
              borderColor: '#64ffda',
              backgroundColor: 'rgba(100,255,218,0.07)',
              borderWidth: 2,
              pointRadius: 3,
              tension: 0.3,
              fill: true,
            },
            {
              label: 'SMA(5)',
              data: sma,
              borderColor: '#ffb347',
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
            legend: { labels: { color: '#8892b0', font: { size: 12 } } },
            tooltip: { mode: 'index', intersect: false },
          },
          scales: {
            x: { ticks: { color: '#8892b0', maxTicksLimit: 12 }, grid: { color: '#2e3455' } },
            y: { ticks: { color: '#8892b0' }, grid: { color: '#2e3455' } },
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
        <table>
          <thead><tr>
            <th>Index</th><th>Actual</th><th>Expected</th>
            <th>Deviation</th><th>Method</th><th>Severity</th><th>Timestamp</th>
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
        </table>
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
