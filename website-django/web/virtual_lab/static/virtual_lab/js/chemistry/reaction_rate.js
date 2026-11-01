// static/virtual_lab/js/chemistry/reaction_rate.js

const canvas = document.getElementById('reaction-canvas');
const ctx    = canvas.getContext('2d');

let initialConc, conc, time = 0, loopID;

// Draws a test-tube shape and fills it proportional to conc
function drawTestTube(c) {
  ctx.clearRect(0,0,600,400);
  // Tube outline
  ctx.strokeStyle = '#555';
  ctx.lineWidth = 4;
  ctx.strokeRect(250,50,100,300);
  // Liquid fill
  const fillHeight = Math.max(0, Math.min(300, (c/initialConc)*300));
  ctx.fillStyle = '#a6f6a6';
  ctx.fillRect(254,350-fillHeight,92,fillHeight);
  // Label concentration
  ctx.fillStyle = '#000';
  ctx.font = '16px Arial';
  ctx.fillText(`[A]: ${c.toFixed(2)} M`, 20, 380);
}

// Provides textual hints based on current conc
function updateHint(c) {
  const hint = document.getElementById('hint');
  if (c <= 0)                  hint.innerText = '{% trans "Reaction has completed!" %}';
  else if (c <= initialConc/2) hint.innerText = '{% trans "Half-life reached." %}';
  else                         hint.innerText = '{% trans "Reaction proceeding..." %}';
}

// Displays final “Reaction Complete” message
function displayProperty() {
  document.getElementById('property').innerText = '{% trans "Reaction Complete" %}';
}

// Advances the reaction in small time steps
function startReaction() {
  initialConc = parseFloat(document.getElementById('reactant-conc').value) || 1.0;
  conc = initialConc;
  time = 0;
  clearInterval(loopID);
  document.getElementById('property').innerText = '';

  loopID = setInterval(() => {
    if (conc <= 0.01) {
      clearInterval(loopID);
      conc = 0;
      drawTestTube(0);
      document.getElementById('elapsed-time').innerText = time;
      updateHint(0);
      displayProperty();
      return;
    }
    // Simple first-order decay: dc/dt = -k * c
    const k = 0.1;               // rate constant
    conc -= k * conc * 0.5;      // ∆t = 0.5 s
    time += 0.5;
    drawTestTube(conc);
    document.getElementById('elapsed-time').innerText = time.toFixed(1);
    updateHint(conc);
  }, 500);
}

// Resets simulation
function resetReaction() {
  clearInterval(loopID);
  document.getElementById('elapsed-time').innerText = '0';
  document.getElementById('hint').innerText = '';
  document.getElementById('property').innerText = '';
  initialConc = parseFloat(document.getElementById('reactant-conc').value) || 1.0;
  conc = initialConc;
  drawTestTube(conc);
}

// Initialize on load
window.addEventListener('load', () => {
  initialConc = parseFloat(document.getElementById('reactant-conc').value) || 1.0;
  conc = initialConc;
  drawTestTube(conc);
});
