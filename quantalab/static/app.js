/**
 * QuantaLab — Simulation Engine & Chat Client
 * Handles experiment loading, canvas simulations, and AI mentor chat.
 */

'use strict';

// ── State ─────────────────────────────────────────────────────────────────

const state = {
  domain: 'physics',
  experiment: null,        // current experiment object
  params: {},              // current parameter values
  animFrame: null,         // requestAnimationFrame handle
  chatHistory: [],         // [{role, content}, ...]
  mentorVisible: window.matchMedia('(min-width: 901px)').matches,
};

// ── DOM References ────────────────────────────────────────────────────────

const $ = (sel) => document.querySelector(sel);
const canvas = $('#simCanvas');
const ctx = canvas.getContext('2d');

// ── Theme palette ─────────────────────────────────────────────────────────
// Canvas colours come from CSS custom properties (style.css), which follow the
// Alpha One Labs light/dark theme. Simulations redraw every frame, so they pick
// up a theme change on the next frame.
const C = {};
function hexToRgb(hex) {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
}
function refreshPalette() {
  const cs = getComputedStyle(document.documentElement);
  const v = (name, fallback) => cs.getPropertyValue(name).trim() || fallback;
  Object.assign(C, {
    bg: v('--sim-bg', '#000000'),
    raised: v('--bg-raised', '#1a1a1a'),
    line: v('--border', '#2e2e2e'),
    muted: v('--text-secondary', '#a3a3a3'),
    text: v('--text-primary', '#ffffff'),
    accent: v('--accent', '#c7ab4f'),
    accentDeep: v('--accent-dark', '#9a8236'),
    accentHi: v('--accent-bright', '#e2c66a'),
    green: v('--sim-green', '#3fb950'),
    amber: v('--sim-amber', '#d29922'),
    red: v('--sim-red', '#f85149'),
    purple: v('--sim-purple', '#bc8cff'),
    orange: v('--sim-orange', '#f0883e'),
  });
  C.accentRgb = C.accent.startsWith('#') ? hexToRgb(C.accent) : '199,171,79';
  C.grid = C.line.startsWith('#') ? `rgba(${hexToRgb(C.line)},0.5)` : C.line;
}
const accentA = (a) => `rgba(${C.accentRgb},${a})`;
refreshPalette();
document.addEventListener('a1-themechange', () => requestAnimationFrame(refreshPalette));
// chrome.js (deferred) may apply a saved theme after this script runs, so also
// watch the attribute directly.
new MutationObserver(() => requestAnimationFrame(refreshPalette))
  .observe(document.documentElement, { attributes: true, attributeFilter: ['data-a1-theme'] });
matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => requestAnimationFrame(refreshPalette));
const domainBtns = document.querySelectorAll('.domain-btn');
const expList = $('#experimentList');
const welcomeScreen = $('#welcomeScreen');
const experimentPanel = $('#experimentPanel');
const expTitle = $('#expTitle');
const expDesc = $('#expDescription');
const controlsPanel = $('#controlsPanel');
const measurements = $('#measurements');
const objectivesList = $('#objectivesList');
const simOverlay = $('#simOverlay');
const chatMessages = $('#chatMessages');
const chatInput = $('#chatInput');
const sendBtn = $('#sendBtn');
const mentorPanel = $('#mentorPanel');
const toggleMentorBtn = $('#toggleMentorBtn');
const closeMentorBtn = $('#closeMentorBtn');
const resetBtn = $('#resetBtn');

// ── API ───────────────────────────────────────────────────────────────────

async function fetchExperiments(domain) {
  const res = await fetch(`/api/experiments/${domain}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function askMentor(message) {
  const res = await fetch('/api/mentor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history: state.chatHistory.slice(-10),
      domain: state.domain,
      experiment: state.experiment?.id || '',
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Domain & Experiment Loading ───────────────────────────────────────────

async function loadDomain(domain) {
  state.domain = domain;
  state.experiment = null;
  cancelAnimation();

  domainBtns.forEach((b) => {
    b.classList.toggle('active', b.dataset.domain === domain);
    b.setAttribute('aria-pressed', String(b.dataset.domain === domain));
  });
  expList.innerHTML = '<li class="skeleton-item"></li><li class="skeleton-item"></li><li class="skeleton-item"></li>';
  showWelcome();

  try {
    const data = await fetchExperiments(domain);
    renderExperimentList(data.experiments);
  } catch (e) {
    expList.innerHTML = `<li style="padding:16px;color:var(--danger);font-size:.85rem">Failed to load experiments.</li>`;
  }
}

function renderExperimentList(experiments) {
  expList.innerHTML = '';
  experiments.forEach((exp) => {
    const li = document.createElement('li');
    li.className = 'exp-item';
    li.dataset.id = exp.id;
    li.innerHTML = `<strong>${exp.title}</strong><small>${exp.description.slice(0, 72)}…</small>`;
    // Keyboard accessible: focusable and activates with Enter / Space
    li.tabIndex = 0;
    li.setAttribute('role', 'button');
    li.addEventListener('click', () => selectExperiment(exp));
    li.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectExperiment(exp); }
    });
    expList.appendChild(li);
  });
}

function selectExperiment(exp) {
  state.experiment = exp;
  state.params = {};
  (exp.parameters || []).forEach((p) => { state.params[p.id] = p.default; });

  document.querySelectorAll('.exp-item').forEach((li) => {
    li.classList.toggle('active', li.dataset.id === exp.id);
    li.setAttribute('aria-pressed', String(li.dataset.id === exp.id));
  });

  expTitle.textContent = exp.title;
  expDesc.textContent = exp.description;
  renderControls(exp.parameters || []);
  renderObjectives(exp.learning_objectives || []);
  showExperiment();
  cancelAnimation();
  startSimulation(exp.id);

  // Prompt the mentor with context
  const greeting = `I just started the "${exp.title}" experiment. Can you give me a quick overview of what I should look for?`;
  autoMentorGreet(greeting, exp.id);
}

// ── Controls ──────────────────────────────────────────────────────────────

function renderControls(params) {
  controlsPanel.innerHTML = '';
  params.forEach((p) => {
    const group = document.createElement('div');
    group.className = 'control-group';

    const labelRow = document.createElement('div');
    labelRow.style.display = 'flex';
    labelRow.style.justifyContent = 'space-between';

    const label = document.createElement('label');
    label.textContent = p.label;
    label.setAttribute('for', `param-${p.id}`);

    const valueSpan = document.createElement('span');
    valueSpan.className = 'control-value';
    valueSpan.id = `val-${p.id}`;
    valueSpan.textContent = state.params[p.id];

    labelRow.append(label, valueSpan);

    const slider = document.createElement('input');
    slider.type = 'range';
    slider.id = `param-${p.id}`;
    slider.min = p.min;
    slider.max = p.max;
    slider.step = p.step;
    slider.value = state.params[p.id];

    slider.addEventListener('input', () => {
      state.params[p.id] = parseFloat(slider.value);
      valueSpan.textContent = slider.value;
    });

    group.append(labelRow, slider);
    controlsPanel.appendChild(group);
  });
}

function renderObjectives(objectives) {
  objectivesList.innerHTML = objectives.map((o) => `<li>${o}</li>`).join('');
}

// ── UI helpers ────────────────────────────────────────────────────────────

function showWelcome() {
  welcomeScreen.hidden = false;
  experimentPanel.hidden = true;
}

function showExperiment() {
  welcomeScreen.hidden = true;
  experimentPanel.hidden = false;
}

function cancelAnimation() {
  if (state.animFrame) {
    cancelAnimationFrame(state.animFrame);
    state.animFrame = null;
  }
}

function setOverlayStats(stats) {
  simOverlay.innerHTML = stats
    .map((s) => `<div class="sim-stat">${s}</div>`)
    .join('');
}

function setMeasurements(items) {
  measurements.innerHTML = items
    .map(
      (m) =>
        `<div class="measurement"><div class="meas-label">${m.label}</div>` +
        `<div class="meas-value">${m.value}</div></div>`
    )
    .join('');
}

// ── Simulation Dispatcher ─────────────────────────────────────────────────

function startSimulation(id) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  simOverlay.innerHTML = '';
  measurements.innerHTML = '';

  const sims = {
    pendulum:         simPendulum,
    projectile:       simProjectile,
    ohms_law:         simOhmsLaw,
    acid_base:        simAcidBase,
    boyles_law:       simBoylesLaw,
    titration:        simTitration,
    mitosis:          simMitosis,
    natural_selection:simNaturalSelection,
    photosynthesis:   simPhotosynthesis,
  };

  const sim = sims[id];
  if (sim) sim();
  else drawPlaceholder(id);
}

function drawPlaceholder(id) {
  ctx.fillStyle = C.muted;
  ctx.font = '16px Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(`Simulation: ${id}`, canvas.width / 2, canvas.height / 2);
}

// ── PHYSICS: Pendulum ─────────────────────────────────────────────────────

function simPendulum() {
  const W = canvas.width, H = canvas.height;
  const pivotX = W / 2, pivotY = 60;
  let angle, angularVel = 0, t = 0;

  function loop() {
    const L = state.params.length || 1.0;
    const g = state.params.gravity || 9.81;
    const initAngle = ((state.params.angle || 15) * Math.PI) / 180;

    // Simple pendulum approximation (small angle)
    const omega = Math.sqrt(g / L);
    const period = (2 * Math.PI) / omega;
    angle = initAngle * Math.cos(omega * t);

    const bobX = pivotX + L * 130 * Math.sin(angle);
    const bobY = pivotY + L * 130 * Math.cos(angle);

    // Clear
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    // Pivot bracket
    ctx.fillStyle = C.line;
    ctx.fillRect(pivotX - 30, 40, 60, 20);

    // String
    ctx.strokeStyle = C.muted;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(pivotX, pivotY);
    ctx.lineTo(bobX, bobY);
    ctx.stroke();

    // Bob
    const bobR = 18;
    const grad = ctx.createRadialGradient(bobX - 4, bobY - 4, 2, bobX, bobY, bobR);
    grad.addColorStop(0, C.accentHi);
    grad.addColorStop(1, C.accentDeep);
    ctx.beginPath();
    ctx.arc(bobX, bobY, bobR, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();

    // Angle arc
    ctx.strokeStyle = accentA(0.3);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(pivotX, pivotY, 50, Math.PI / 2 - initAngle, Math.PI / 2 + initAngle);
    ctx.stroke();

    const currentAngleDeg = ((angle * 180) / Math.PI).toFixed(1);
    setOverlayStats([`θ = ${currentAngleDeg}°`, `T = ${period.toFixed(2)} s`]);
    setMeasurements([
      { label: 'Period (s)',  value: period.toFixed(3) },
      { label: 'Frequency (Hz)', value: (1 / period).toFixed(3) },
      { label: 'Angle (°)',  value: currentAngleDeg },
      { label: 'Length (m)', value: L.toFixed(2) },
    ]);

    t += 0.016;
    state.animFrame = requestAnimationFrame(loop);
  }
  loop();
}

// ── PHYSICS: Projectile ───────────────────────────────────────────────────

function simProjectile() {
  const W = canvas.width, H = canvas.height;
  const groundY = H - 40;
  const scale = 6; // pixels per meter
  let launched = false, px = 0, py = 0, vx = 0, vy = 0, t = 0;
  let trail = [];

  function computeMetrics() {
    const v0 = state.params.speed || 20;
    const a = ((state.params.angle || 45) * Math.PI) / 180;
    const g = state.params.gravity || 9.81;
    const range = (v0 * v0 * Math.sin(2 * a)) / g;
    const maxH = (v0 * v0 * Math.sin(a) * Math.sin(a)) / (2 * g);
    const flightT = (2 * v0 * Math.sin(a)) / g;
    return { range, maxH, flightT };
  }

  function launch() {
    const v0 = state.params.speed || 20;
    const a = ((state.params.angle || 45) * Math.PI) / 180;
    px = 40;
    py = groundY;
    vx = v0 * Math.cos(a) * scale;
    vy = -v0 * Math.sin(a) * scale;
    t = 0;
    trail = [];
    launched = true;
  }

  function loop() {
    const g = state.params.gravity || 9.81;
    const dt = 0.016;

    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    // Ground
    ctx.strokeStyle = C.line;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, groundY);
    ctx.lineTo(W, groundY);
    ctx.stroke();

    // Grid lines (faint)
    ctx.strokeStyle = C.grid;
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 60) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }

    // Launch arrow
    const a = ((state.params.angle || 45) * Math.PI) / 180;
    ctx.strokeStyle = C.accent;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(40, groundY);
    ctx.lineTo(40 + 40 * Math.cos(a), groundY - 40 * Math.sin(a));
    ctx.stroke();
    ctx.fillStyle = C.accent;
    ctx.font = '12px Inter';
    ctx.fillText(`${state.params.angle || 45}°`, 56, groundY - 20);

    // Trail
    if (trail.length > 1) {
      ctx.strokeStyle = accentA(0.4);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(trail[0].x, trail[0].y);
      trail.forEach((p) => ctx.lineTo(p.x, p.y));
      ctx.stroke();
    }

    // Physics update
    if (launched) {
      vy += g * scale * dt;
      px += vx * dt;
      py += vy * dt;
      t += dt;
      trail.push({ x: px, y: py });

      if (py >= groundY) {
        py = groundY;
        launched = false;
        trail.push({ x: px, y: py });
        setTimeout(launch, 800);
      }

      // Ball
      ctx.beginPath();
      ctx.arc(px, py, 8, 0, Math.PI * 2);
      ctx.fillStyle = C.orange;
      ctx.fill();
    }

    const m = computeMetrics();
    setOverlayStats([`Range: ${m.range.toFixed(1)} m`, `H_max: ${m.maxH.toFixed(1)} m`]);
    setMeasurements([
      { label: 'Range (m)',  value: m.range.toFixed(2) },
      { label: 'Max Height (m)', value: m.maxH.toFixed(2) },
      { label: 'Flight Time (s)', value: m.flightT.toFixed(2) },
    ]);

    state.animFrame = requestAnimationFrame(loop);
  }
  launch();
  loop();
}

// ── PHYSICS: Ohm's Law ────────────────────────────────────────────────────

function simOhmsLaw() {
  function draw() {
    const V = state.params.voltage || 9;
    const R = state.params.resistance || 100;
    const I = V / R;
    const P = V * I;

    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    // Draw circuit
    const cx = W / 2, cy = H / 2;
    const cw = 300, ch = 160;

    // Circuit outline (rectangle)
    ctx.strokeStyle = C.line;
    ctx.lineWidth = 3;
    ctx.strokeRect(cx - cw / 2, cy - ch / 2, cw, ch);

    // Battery (left side, centered)
    const bx = cx - cw / 2;
    drawBattery(bx, cy, V);

    // Resistor (top side)
    drawResistor(cx, cy - ch / 2, R);

    // Ammeter (right side)
    drawAmmeter(cx + cw / 2, cy, I);

    // Current flow dots
    drawCurrentFlow(cx, cy, cw, ch, I);

    // V=IR label
    ctx.fillStyle = C.text;
    ctx.font = 'bold 14px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText('V = I × R', cx, H - 20);

    setMeasurements([
      { label: 'Voltage (V)',   value: V.toFixed(1) },
      { label: 'Current (A)',   value: I.toFixed(4) },
      { label: 'Resistance (Ω)', value: R.toFixed(0) },
      { label: 'Power (W)',     value: P.toFixed(4) },
    ]);

    state.animFrame = requestAnimationFrame(draw);
  }
  draw();
}

function drawBattery(x, y, V) {
  ctx.strokeStyle = C.green;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x, y - 20);
  ctx.lineTo(x, y + 20);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x - 8, y - 12);
  ctx.lineTo(x + 8, y - 12);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x - 4, y + 12);
  ctx.lineTo(x + 4, y + 12);
  ctx.stroke();
  ctx.fillStyle = C.green;
  ctx.font = '11px Inter';
  ctx.textAlign = 'center';
  ctx.fillText(`${V}V`, x, y + 38);
}

function drawResistor(x, y, R) {
  ctx.strokeStyle = C.amber;
  ctx.lineWidth = 2;
  const w = 60, h = 18;
  ctx.strokeRect(x - w / 2, y - h / 2, w, h);
  ctx.fillStyle = C.amber;
  ctx.font = '11px Inter';
  ctx.textAlign = 'center';
  ctx.fillText(`${R}Ω`, x, y - h / 2 - 6);
}

function drawAmmeter(x, y, I) {
  ctx.strokeStyle = C.purple;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(x, y, 18, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = C.purple;
  ctx.font = 'bold 13px Inter';
  ctx.textAlign = 'center';
  ctx.fillText('A', x, y + 5);
  ctx.font = '10px JetBrains Mono';
  ctx.fillText(`${(I * 1000).toFixed(1)}mA`, x, y + 38);
}

let _dotOffset = 0;
function drawCurrentFlow(cx, cy, cw, ch, I) {
  _dotOffset = (_dotOffset + I * 800) % 60;
  ctx.fillStyle = accentA(0.7);
  const speed = Math.max(10, Math.min(60, I * 5000));
  const perimeter = 2 * (cw + ch);
  for (let d = _dotOffset; d < perimeter; d += 60) {
    const pos = d % perimeter;
    let px, py;
    if (pos < cw) { px = cx - cw / 2 + pos; py = cy - ch / 2; }
    else if (pos < cw + ch) { px = cx + cw / 2; py = cy - ch / 2 + (pos - cw); }
    else if (pos < 2 * cw + ch) { px = cx + cw / 2 - (pos - cw - ch); py = cy + ch / 2; }
    else { px = cx - cw / 2; py = cy + ch / 2 - (pos - 2 * cw - ch); }
    ctx.beginPath();
    ctx.arc(px, py, 3, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ── CHEMISTRY: Acid-Base ──────────────────────────────────────────────────

function simAcidBase() {
  function phColor(ph) {
    // Classic universal indicator colours
    if (ph <= 2)  return '#d73027';
    if (ph <= 4)  return '#f46d43';
    if (ph <= 6)  return '#fee08b';
    if (ph <= 7)  return '#ffffbf';
    if (ph <= 8)  return '#d9ef8b';
    if (ph <= 10) return '#66bd63';
    if (ph <= 12) return '#1a9850';
    return '#4575b4';
  }

  function draw() {
    const initPh = state.params.initial_ph || 7;
    const drops = state.params.drops || 5;
    const conc = state.params.concentration || 0.5;
    const ph = Math.max(1, Math.min(14, initPh + drops * conc * 0.4 - 4 * conc));

    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    // Beaker
    const bx = W / 2 - 60, bw = 120, bh = 140, by = H / 2 - 40;
    ctx.strokeStyle = C.muted;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(bx, by + bh);
    ctx.lineTo(bx + bw, by + bh);
    ctx.lineTo(bx + bw, by);
    ctx.stroke();

    // Liquid
    const liquidH = bh * 0.7;
    ctx.fillStyle = phColor(ph);
    ctx.globalAlpha = 0.8;
    ctx.fillRect(bx + 3, by + bh - liquidH, bw - 6, liquidH);
    ctx.globalAlpha = 1;

    // pH meter needle
    const phScale = (ph - 1) / 13;
    const meterX = W / 2, meterY = 60;
    drawPHMeter(meterX, meterY, ph, phScale);

    // Indicator scale bar
    drawPHScaleBar(W / 2, H - 30, 320);

    // Marker on bar
    const markerX = W / 2 - 160 + phScale * 320;
    ctx.fillStyle = C.text;
    ctx.beginPath();
    ctx.moveTo(markerX, H - 50);
    ctx.lineTo(markerX - 6, H - 30);
    ctx.lineTo(markerX + 6, H - 30);
    ctx.fill();

    setMeasurements([
      { label: 'pH',         value: ph.toFixed(2) },
      { label: 'Type',       value: ph < 7 ? 'Acid' : ph > 7 ? 'Base' : 'Neutral' },
      { label: 'H⁺ (mol/L)', value: Math.pow(10, -ph).toExponential(2) },
    ]);
    state.animFrame = requestAnimationFrame(draw);
  }
  draw();
}

function drawPHMeter(x, y, ph, scale) {
  ctx.font = 'bold 32px JetBrains Mono, monospace';
  ctx.fillStyle = C.text;
  ctx.textAlign = 'center';
  ctx.fillText(`pH ${ph.toFixed(1)}`, x, y + 10);
}

function drawPHScaleBar(cx, y, width) {
  const grad = ctx.createLinearGradient(cx - width / 2, y, cx + width / 2, y);
  grad.addColorStop(0,    '#d73027');
  grad.addColorStop(0.25, '#fee08b');
  grad.addColorStop(0.5,  '#ffffbf');
  grad.addColorStop(0.65, '#d9ef8b');
  grad.addColorStop(1,    '#4575b4');
  ctx.fillStyle = grad;
  ctx.fillRect(cx - width / 2, y - 8, width, 16);
  // Labels
  ctx.fillStyle = C.muted;
  ctx.font = '10px Inter';
  ctx.textAlign = 'center';
  for (let i = 1; i <= 14; i += 2) {
    const lx = cx - width / 2 + ((i - 1) / 13) * width;
    ctx.fillText(i, lx, y + 24);
  }
}

// ── CHEMISTRY: Boyle's Law ────────────────────────────────────────────────

function simBoylesLaw() {
  function draw() {
    const V = state.params.volume || 2.0;
    const P0 = state.params.initial_pressure || 1.0;
    const V0 = 2.0;
    const P = (P0 * V0) / V;

    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    // Syringe body
    const sy = H / 2, sx = 120, sw = 350 * (V / 5.0), sh = 80;
    ctx.strokeStyle = C.muted;
    ctx.lineWidth = 3;
    ctx.strokeRect(sx, sy - sh / 2, sw, sh);

    // Gas molecules (dots)
    const nMolecules = Math.round(20 * (V / 5.0));
    const seed = Math.sin(V * 100);
    ctx.fillStyle = `rgba(${C.accentRgb},${Math.min(1, 0.3 + P * 0.3)})`;
    for (let i = 0; i < nMolecules; i++) {
      const mx = sx + 10 + ((Math.sin(i * 2.7 + seed) * 0.5 + 0.5) * (sw - 20));
      const my = sy - sh / 2 + 10 + ((Math.cos(i * 3.1 + seed) * 0.5 + 0.5) * (sh - 20));
      ctx.beginPath();
      ctx.arc(mx, my, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    // Piston
    const pistonX = sx + sw;
    ctx.fillStyle = C.line;
    ctx.fillRect(pistonX, sy - sh / 2 - 4, 20, sh + 8);
    ctx.strokeStyle = C.muted;
    ctx.strokeRect(pistonX, sy - sh / 2 - 4, 20, sh + 8);

    // PV=const label
    ctx.fillStyle = C.text;
    ctx.font = 'bold 14px JetBrains Mono';
    ctx.textAlign = 'center';
    ctx.fillText('PV = constant', W / 2, H - 20);

    setMeasurements([
      { label: 'Volume (L)',    value: V.toFixed(2) },
      { label: 'Pressure (atm)', value: P.toFixed(3) },
      { label: 'P × V',         value: (P * V).toFixed(3) },
    ]);
    state.animFrame = requestAnimationFrame(draw);
  }
  draw();
}

// ── CHEMISTRY: Titration ──────────────────────────────────────────────────

function simTitration() {
  let titrantAdded = 0;
  let direction = 1;

  function phAtVolume(Vt) {
    const Va = state.params.acid_volume || 25;
    const Ca = state.params.acid_concentration || 0.1;
    const Cb = state.params.base_concentration || 0.1;
    const equivVol = (Va * Ca) / Cb;
    const totalVol = Va + Vt;

    if (Math.abs(Vt - equivVol) < 0.5) return 7;
    if (Vt < equivVol) {
      const molesAcid = Ca * Va - Cb * Vt;
      const concAcid = molesAcid / totalVol;
      return Math.max(1, -Math.log10(concAcid / 1000));
    }
    const molesBase = Cb * Vt - Ca * Va;
    const concBase = molesBase / totalVol;
    return Math.min(13, 14 + Math.log10(concBase / 1000));
  }

  function draw() {
    titrantAdded = (titrantAdded + 0.05 * direction + 60) % 60;
    if (titrantAdded > 55) direction = -1;
    if (titrantAdded < 2) direction = 1;

    const ph = phAtVolume(titrantAdded);
    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    // Burette (top)
    ctx.strokeStyle = C.muted;
    ctx.lineWidth = 2;
    ctx.strokeRect(W / 2 - 10, 20, 20, 120);
    ctx.fillStyle = '#4575b4';
    ctx.globalAlpha = 0.7;
    ctx.fillRect(W / 2 - 9, 21, 18, (1 - titrantAdded / 60) * 118);
    ctx.globalAlpha = 1;

    // Drop
    ctx.fillStyle = '#4575b4';
    ctx.beginPath();
    ctx.arc(W / 2, 150, 4, 0, Math.PI * 2);
    ctx.fill();

    // Conical flask
    const fx = W / 2, fy = 230;
    ctx.strokeStyle = C.muted;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(fx - 15, fy);
    ctx.lineTo(fx - 50, fy + 100);
    ctx.lineTo(fx + 50, fy + 100);
    ctx.lineTo(fx + 15, fy);
    ctx.closePath();
    ctx.stroke();

    // Liquid in flask
    const phColor = getPhColor(ph);
    ctx.fillStyle = phColor;
    ctx.globalAlpha = 0.7;
    ctx.beginPath();
    ctx.moveTo(fx - 50 + 5, fy + 100 - 5);
    ctx.lineTo(fx + 50 - 5, fy + 100 - 5);
    ctx.lineTo(fx + 50 - 5, fy + 40);
    ctx.lineTo(fx - 50 + 5, fy + 40);
    ctx.fill();
    ctx.globalAlpha = 1;

    // Titration curve (right side)
    drawTitrationCurve(W * 0.72, H / 2, 120, 140, titrantAdded);

    setMeasurements([
      { label: 'Titrant Added (mL)', value: titrantAdded.toFixed(1) },
      { label: 'pH', value: ph.toFixed(2) },
      { label: 'Equiv. Vol. (mL)', value: ((state.params.acid_volume || 25) * (state.params.acid_concentration || 0.1) / (state.params.base_concentration || 0.1)).toFixed(1) },
    ]);
    state.animFrame = requestAnimationFrame(draw);
  }
  draw();
}

function getPhColor(ph) {
  if (ph <= 3) return '#d73027';
  if (ph <= 6) return '#fee08b';
  if (ph <= 8) return '#ffffbf';
  if (ph <= 11) return '#66bd63';
  return '#4575b4';
}

function drawTitrationCurve(cx, cy, xScale, yScale, current) {
  ctx.strokeStyle = accentA(0.6);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let v = 0; v <= 60; v += 0.5) {
    const Va = 25, Ca = 0.1, Cb = 0.1;
    const equivVol = (Va * Ca) / Cb;
    let ph;
    if (Math.abs(v - equivVol) < 0.5) ph = 7;
    else if (v < equivVol) {
      const mA = Ca * Va - Cb * v;
      ph = Math.max(1, -Math.log10(mA / (Va + v) / 1000));
    } else {
      const mB = Cb * v - Ca * Va;
      ph = Math.min(13, 14 + Math.log10(mB / (Va + v) / 1000));
    }
    const px = cx - xScale / 2 + (v / 60) * xScale;
    const py = cy + yScale / 2 - ((ph - 1) / 13) * yScale;
    v === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
  }
  ctx.stroke();

  // Current position dot
  const Va = 25, Ca = 0.1, Cb = 0.1;
  const equivVol = (Va * Ca) / Cb;
  let cPh;
  if (Math.abs(current - equivVol) < 0.5) cPh = 7;
  else if (current < equivVol) {
    const mA = Ca * Va - Cb * current;
    cPh = Math.max(1, -Math.log10(mA / (Va + current) / 1000));
  } else {
    const mB = Cb * current - Ca * Va;
    cPh = Math.min(13, 14 + Math.log10(mB / (Va + current) / 1000));
  }
  const dotX = cx - xScale / 2 + (current / 60) * xScale;
  const dotY = cy + yScale / 2 - ((cPh - 1) / 13) * yScale;
  ctx.fillStyle = C.orange;
  ctx.beginPath();
  ctx.arc(dotX, dotY, 5, 0, Math.PI * 2);
  ctx.fill();

  // Axis labels
  ctx.fillStyle = C.muted;
  ctx.font = '10px Inter';
  ctx.textAlign = 'center';
  ctx.fillText('Volume added (mL)', cx, cy + yScale / 2 + 16);
  ctx.save();
  ctx.translate(cx - xScale / 2 - 14, cy);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('pH', 0, 0);
  ctx.restore();
}

// ── BIOLOGY: Mitosis ──────────────────────────────────────────────────────

const MITOSIS_PHASES = [
  { name: 'Interphase', duration: 120 },
  { name: 'Prophase',   duration: 80 },
  { name: 'Metaphase',  duration: 60 },
  { name: 'Anaphase',   duration: 60 },
  { name: 'Telophase',  duration: 80 },
  { name: 'Cytokinesis', duration: 60 },
];

function simMitosis() {
  let frame = 0;
  const totalFrames = MITOSIS_PHASES.reduce((s, p) => s + p.duration, 0);

  function getPhaseIndex(f) {
    let acc = 0;
    for (let i = 0; i < MITOSIS_PHASES.length; i++) {
      acc += MITOSIS_PHASES[i].duration;
      if (f < acc) return i;
    }
    return MITOSIS_PHASES.length - 1;
  }

  function draw() {
    const speed = state.params.speed || 1.0;
    frame = (frame + speed) % totalFrames;
    const phaseIdx = getPhaseIndex(frame);
    const phase = MITOSIS_PHASES[phaseIdx];

    let accBefore = 0;
    for (let i = 0; i < phaseIdx; i++) accBefore += MITOSIS_PHASES[i].duration;
    const phaseProgress = (frame - accBefore) / phase.duration;

    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    drawMitosisPhase(W / 2, H / 2 - 20, phaseIdx, phaseProgress);

    // Phase label
    ctx.fillStyle = C.text;
    ctx.font = 'bold 18px Inter';
    ctx.textAlign = 'center';
    ctx.fillText(phase.name, W / 2, 36);

    // Phase progress bar
    const barW = 400;
    ctx.fillStyle = C.raised;
    ctx.fillRect(W / 2 - barW / 2, 48, barW, 6);
    ctx.fillStyle = C.green;
    ctx.fillRect(W / 2 - barW / 2, 48, phaseProgress * barW, 6);

    // Phase timeline
    let bx = W / 2 - barW / 2;
    MITOSIS_PHASES.forEach((p, i) => {
      const pw = (p.duration / totalFrames) * barW;
      ctx.fillStyle = i === phaseIdx ? C.accent : C.line;
      ctx.fillRect(bx, H - 36, pw - 2, 8);
      ctx.fillStyle = C.muted;
      ctx.font = '9px Inter';
      ctx.textAlign = 'left';
      if (pw > 30) ctx.fillText(p.name, bx + 2, H - 20);
      bx += pw;
    });

    setMeasurements([{ label: 'Phase', value: phase.name }]);
    state.animFrame = requestAnimationFrame(draw);
  }
  draw();
}

function drawMitosisPhase(cx, cy, phaseIdx, progress) {
  const r = 70;

  if (phaseIdx === 0) {
    // Interphase: single round cell
    drawCell(cx, cy, r, 'rgba(63,185,80,0.2)', C.green);
    drawNucleus(cx, cy, r * 0.45, accentA(0.3), C.accent);
    ctx.fillStyle = C.muted;
    ctx.font = '12px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('DNA replication occurring…', cx, cy + r + 22);
  } else if (phaseIdx === 1) {
    // Prophase: chromosomes condense
    drawCell(cx, cy, r, 'rgba(63,185,80,0.2)', C.green);
    const n = 4;
    for (let i = 0; i < n; i++) {
      const angle = (i / n) * Math.PI * 2 + progress * 0.5;
      const dx = Math.cos(angle) * r * 0.35;
      const dy = Math.sin(angle) * r * 0.35;
      drawChromosome(cx + dx, cy + dy, 12 + 4 * progress, C.purple);
    }
  } else if (phaseIdx === 2) {
    // Metaphase: chromosomes align on plate
    drawCell(cx, cy, r, 'rgba(63,185,80,0.2)', C.green);
    drawSpindleFibres(cx, cy, r);
    const n = 4;
    for (let i = 0; i < n; i++) {
      const dx = ((i - 1.5) / 3) * r * 0.55;
      drawChromosome(cx + dx, cy, 14, C.purple);
    }
  } else if (phaseIdx === 3) {
    // Anaphase: chromosomes move to poles
    drawCell(cx, cy, r * (1 + 0.3 * progress), 'rgba(63,185,80,0.15)', C.green);
    drawSpindleFibres(cx, cy, r);
    const n = 4;
    for (let i = 0; i < n; i++) {
      const dx = ((i - 1.5) / 3) * r * 0.4;
      drawChromosome(cx + dx, cy - r * 0.35 * progress, 12, C.purple);
      drawChromosome(cx + dx, cy + r * 0.35 * progress, 12, C.orange);
    }
  } else if (phaseIdx === 4) {
    // Telophase: two nuclei forming
    const sep = r * 0.5 * progress;
    drawCell(cx, cy - sep, r * 0.7, 'rgba(63,185,80,0.2)', C.green);
    drawCell(cx, cy + sep, r * 0.7, 'rgba(63,185,80,0.2)', C.green);
    drawNucleus(cx, cy - sep, r * 0.28, accentA(0.25), C.accent);
    drawNucleus(cx, cy + sep, r * 0.28, accentA(0.25), C.accent);
  } else {
    // Cytokinesis: cell pinches
    const pinch = progress;
    drawPinchingCell(cx, cy, r, pinch);
  }
}

function drawCell(cx, cy, r, fill, stroke) {
  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
}

function drawNucleus(cx, cy, r, fill, stroke) {
  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 2]);
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawChromosome(cx, cy, size, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(cx, cy, size * 0.35, size, 0, 0, Math.PI * 2);
  ctx.fill();
}

function drawSpindleFibres(cx, cy, r) {
  ctx.strokeStyle = 'rgba(140,200,255,0.25)';
  ctx.lineWidth = 1;
  for (let i = -3; i <= 3; i++) {
    const dx = (i / 3) * r * 0.4;
    ctx.beginPath();
    ctx.moveTo(cx + dx, cy - r + 5);
    ctx.lineTo(cx + dx, cy + r - 5);
    ctx.stroke();
  }
}

function drawPinchingCell(cx, cy, r, pinch) {
  const squeeze = pinch * r * 0.6;
  ctx.fillStyle = 'rgba(63,185,80,0.2)';
  ctx.strokeStyle = C.green;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(cx, cy - squeeze / 2, r * (1 - pinch * 0.2), r * (1 - pinch * 0.1), 0, 0, Math.PI * 2);
  ctx.fill(); ctx.stroke();
  ctx.beginPath();
  ctx.ellipse(cx, cy + squeeze / 2, r * (1 - pinch * 0.2), r * (1 - pinch * 0.1), 0, 0, Math.PI * 2);
  ctx.fill(); ctx.stroke();
}

// ── BIOLOGY: Natural Selection ────────────────────────────────────────────

function simNaturalSelection() {
  let population = initPop(state.params.population || 40);
  let generation = 0;
  let frameCount = 0;
  const FRAMES_PER_GEN = 60;

  function initPop(n) {
    return Array.from({ length: n }, () => ({
      x: Math.random() * 640 + 30,
      y: Math.random() * 320 + 40,
      fitness: Math.random(),
      color: `hsl(${Math.random() * 360},70%,60%)`,
    }));
  }

  function evolve() {
    generation++;
    const mu = (state.params.mutation_rate || 5) / 100;
    // Sort by fitness
    population.sort((a, b) => b.fitness - a.fitness);
    // Keep top half, reproduce with mutation
    const survivors = population.slice(0, Math.ceil(population.length / 2));
    population = [];
    while (population.length < (state.params.population || 40)) {
      const parent = survivors[Math.floor(Math.random() * survivors.length)];
      const child = {
        x: Math.random() * 640 + 30,
        y: Math.random() * 320 + 40,
        fitness: Math.max(0, Math.min(1, parent.fitness + (Math.random() - 0.4) * mu * 2)),
        color: parent.color,
      };
      if (Math.random() < mu) {
        child.color = `hsl(${Math.random() * 360},70%,60%)`;
        child.fitness = Math.random();
      }
      population.push(child);
    }
  }

  function draw() {
    frameCount++;
    if (frameCount % FRAMES_PER_GEN === 0 && generation < (state.params.generations || 20)) {
      evolve();
    }

    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    // Background environment
    ctx.fillStyle = 'rgba(63,185,80,0.05)';
    ctx.fillRect(30, 40, 640, 320);

    population.forEach((org) => {
      const r = 4 + org.fitness * 8;
      ctx.fillStyle = org.color;
      ctx.globalAlpha = 0.6 + org.fitness * 0.4;
      ctx.beginPath();
      ctx.arc(org.x, org.y, r, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;

    const avgFit = population.reduce((s, o) => s + o.fitness, 0) / population.length;

    ctx.fillStyle = C.text;
    ctx.font = 'bold 13px Inter';
    ctx.textAlign = 'left';
    ctx.fillText(`Generation: ${generation}`, 36, 30);
    ctx.fillStyle = C.muted;
    ctx.font = '12px Inter';
    ctx.fillText(`Avg fitness: ${avgFit.toFixed(3)}`, 200, 30);

    setMeasurements([
      { label: 'Generation', value: generation },
      { label: 'Population', value: population.length },
      { label: 'Avg Fitness', value: avgFit.toFixed(3) },
    ]);
    state.animFrame = requestAnimationFrame(draw);
  }
  draw();
}

// ── BIOLOGY: Photosynthesis ───────────────────────────────────────────────

function simPhotosynthesis() {
  let bubbles = [];
  let lastBubble = 0;

  function rate() {
    const light = (state.params.light || 50) / 100;
    const co2 = (state.params.co2 || 0.04) / 1.0;
    const T = state.params.temperature || 25;
    const tempFactor = Math.exp(-0.05 * Math.pow(T - 30, 2));
    return light * Math.sqrt(co2 * 100) * tempFactor * 8;
  }

  function draw(timestamp) {
    const r = rate();

    if (timestamp - lastBubble > Math.max(60, 600 / (r + 0.1))) {
      lastBubble = timestamp;
      if (r > 0.5) {
        bubbles.push({
          x: 320 + (Math.random() - 0.5) * 30,
          y: 280,
          r: 3 + Math.random() * 3,
          speed: 0.5 + r * 0.2,
        });
      }
    }

    bubbles.forEach((b) => { b.y -= b.speed; });
    bubbles = bubbles.filter((b) => b.y > 60);

    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    // Water / beaker
    ctx.fillStyle = 'rgba(30,60,120,0.5)';
    ctx.fillRect(240, 120, 160, 220);

    // Plant (simple)
    ctx.strokeStyle = C.green;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(320, 330);
    ctx.lineTo(320, 200);
    ctx.stroke();
    // Leaves
    drawLeaf(320, 260, -0.5);
    drawLeaf(320, 230, 0.5);
    drawLeaf(320, 200, -0.3);

    // Light rays
    const lightAlpha = (state.params.light || 50) / 100;
    ctx.strokeStyle = `rgba(255,215,0,${lightAlpha * 0.4})`;
    ctx.lineWidth = 1.5;
    for (let i = -3; i <= 3; i++) {
      ctx.beginPath();
      ctx.moveTo(320 + i * 30, 0);
      ctx.lineTo(320 + i * 20, 120);
      ctx.stroke();
    }

    // Bubbles (O₂)
    bubbles.forEach((b) => {
      ctx.strokeStyle = accentA(0.7);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
      ctx.stroke();
    });

    // Rate gauge (right side)
    drawRateGauge(580, H / 2, r);

    // Equation
    ctx.fillStyle = C.muted;
    ctx.font = '11px JetBrains Mono';
    ctx.textAlign = 'center';
    ctx.fillText('6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂', W / 2, H - 12);

    setMeasurements([
      { label: 'Rate (AU)',     value: r.toFixed(2) },
      { label: 'O₂ Bubbles',   value: bubbles.length },
      { label: 'Light (%)',     value: state.params.light || 50 },
    ]);
    state.animFrame = requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
}

function drawLeaf(x, y, angle) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  ctx.fillStyle = C.green;
  ctx.globalAlpha = 0.8;
  ctx.beginPath();
  ctx.ellipse(25, 0, 25, 10, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.restore();
}

function drawRateGauge(cx, cy, rate) {
  const maxR = 10;
  const capped = Math.min(rate, maxR);
  const height = 120;

  ctx.fillStyle = C.raised;
  ctx.fillRect(cx - 20, cy - height / 2, 40, height);

  const fillH = (capped / maxR) * height;
  ctx.fillStyle = capped > 6 ? C.green : capped > 3 ? C.amber : C.red;
  ctx.fillRect(cx - 18, cy + height / 2 - fillH, 36, fillH);

  ctx.fillStyle = C.muted;
  ctx.font = '10px Inter';
  ctx.textAlign = 'center';
  ctx.fillText('Rate', cx, cy + height / 2 + 14);
}

// ── AI Mentor Chat ────────────────────────────────────────────────────────

async function sendMessage(text) {
  if (!text.trim()) return;
  chatInput.value = '';
  appendMessage('user', text);

  const typing = appendMessage('assistant', '', true);
  sendBtn.disabled = true;

  try {
    state.chatHistory.push({ role: 'user', content: text });
    const data = await askMentor(text);
    typing.remove();
    const reply = data.response || 'Sorry, I couldn\'t get a response. Please try again.';
    state.chatHistory.push({ role: 'assistant', content: reply });
    appendMessage('assistant', reply);
  } catch (e) {
    typing.remove();
    appendMessage('assistant', '⚠️ Connection error. Please check your network and try again.');
  } finally {
    sendBtn.disabled = false;
  }
}

function appendMessage(role, content, isTyping = false) {
  const div = document.createElement('div');
  div.className = `chat-message ${role}${isTyping ? ' typing-indicator' : ''}`;
  const inner = document.createElement('div');
  inner.className = 'message-content';
  if (content) inner.innerHTML = simpleMarkdown(content);
  div.appendChild(inner);
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function simpleMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code style="background:var(--bg-overlay);padding:1px 4px;border-radius:3px">$1</code>')
    .replace(/\n/g, '<br/>');
}

let _autoGreetPending = null;
function autoMentorGreet(message, expId) {
  // Debounce: don't spam if user switches experiments quickly
  if (_autoGreetPending) clearTimeout(_autoGreetPending);
  _autoGreetPending = setTimeout(async () => {
    if (state.experiment?.id !== expId) return;
    await sendMessage(message);
  }, 600);
}

// ── Event Listeners ───────────────────────────────────────────────────────

domainBtns.forEach((btn) => {
  btn.addEventListener('click', () => loadDomain(btn.dataset.domain));
});

sendBtn.addEventListener('click', () => sendMessage(chatInput.value));

chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(chatInput.value);
  }
});

toggleMentorBtn.addEventListener('click', () => {
  state.mentorVisible = !state.mentorVisible;
  mentorPanel.classList.toggle('hidden', !state.mentorVisible);
  // For mobile
  mentorPanel.classList.toggle('visible', state.mentorVisible);
  toggleMentorBtn.setAttribute('aria-expanded', String(state.mentorVisible));
});

closeMentorBtn.addEventListener('click', () => {
  state.mentorVisible = false;
  mentorPanel.classList.add('hidden');
  mentorPanel.classList.remove('visible');
  toggleMentorBtn.setAttribute('aria-expanded', 'false');
  toggleMentorBtn.focus();
});

resetBtn.addEventListener('click', () => {
  if (!state.experiment) return;
  (state.experiment.parameters || []).forEach((p) => {
    state.params[p.id] = p.default;
    const slider = document.getElementById(`param-${p.id}`);
    const valSpan = document.getElementById(`val-${p.id}`);
    if (slider) slider.value = p.default;
    if (valSpan) valSpan.textContent = p.default;
  });
});

// ── Init ──────────────────────────────────────────────────────────────────

toggleMentorBtn.setAttribute('aria-expanded', String(state.mentorVisible));
if (!state.mentorVisible) mentorPanel.classList.add('hidden');

loadDomain('physics');
