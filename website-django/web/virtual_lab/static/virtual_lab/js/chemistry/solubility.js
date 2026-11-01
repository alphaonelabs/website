// static/virtual_lab/js/chemistry/solubility.js

const canvas = document.getElementById('solubility-canvas');
const ctx    = canvas.getContext('2d');

let dissolved = 0;
const limit   = 10; // grams

// Draws beaker and liquid fill based on dissolved amount
function drawBeaker() {
  ctx.clearRect(0, 0, 600, 400);
  // Beaker outline
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 2;
  ctx.strokeRect(200, 100, 200, 250);
  // Liquid fill
  const height = Math.min((dissolved / limit) * 240, 240);
  ctx.fillStyle = '#f3e6b8';
  ctx.fillRect(202, 350 - height, 196, height);
  // Label
  ctx.fillStyle = '#000';
  ctx.font = '16px Arial';
  ctx.fillText(`${dissolved.toFixed(1)}g / ${limit}g`, 250, 380);
}

// Updates hint text based on current dissolved amount
function updateHint() {
  const hintEl = document.getElementById('hint');
  if (dissolved < limit) {
    hintEl.innerText = '🔽 Solution is unsaturated. Keep adding solute.';
  } else if (dissolved === limit) {
    hintEl.innerText = '✅ Saturation point reached!';
  } else {
    hintEl.innerText = '⚠️ Supersaturated! Excess solute will precipitate.';
  }
}

// Displays final property once user is done
function displayProperty() {
  const propEl = document.getElementById('property');
  if (dissolved < limit) {
    propEl.innerText = 'Solution is Unsaturated';
  } else if (dissolved === limit) {
    propEl.innerText = 'Solution is Saturated';
  } else {
    propEl.innerText = 'Solution is Supersaturated';
  }
}

// Called when user clicks “Add Solute”
function addSolute() {
  const amtInput = parseFloat(document.getElementById('solute-amt').value) || 0;
  dissolved += amtInput;
  document.getElementById('dissolved-amt').innerText = dissolved.toFixed(1);
  drawBeaker();
  updateHint();
  displayProperty();
}

// Called when user clicks “Reset”
function resetSolubility() {
  dissolved = 0;
  document.getElementById('dissolved-amt').innerText = '0';
  document.getElementById('property').innerText = '';
  drawBeaker();
  updateHint();
}

// Initial render on page load
window.addEventListener('load', () => {
  drawBeaker();
  updateHint();
});
