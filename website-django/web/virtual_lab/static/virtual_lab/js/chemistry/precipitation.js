// static/virtual_lab/js/chemistry/precipitation.js

// Canvases
const beakerCanvas = document.getElementById('beaker-canvas');
const bctx         = beakerCanvas.getContext('2d');
const swirlCanvas  = document.getElementById('swirl-canvas');
const sctx         = swirlCanvas.getContext('2d');
const precipCanvas = document.getElementById('precip-canvas');
const pctx         = precipCanvas.getContext('2d');

// Controls & status
const addBtn   = document.getElementById('add-reagent');
const stirBtn  = document.getElementById('stir-btn');
const resetBtn = document.getElementById('reset-btn');
const hintEl   = document.getElementById('hint');
const propEl   = document.getElementById('property');

let swirlAngle = 0,
    swirlRAF,
    precipParticles = [],
    stage = 0;  // 0=init,1=reagent,2=stirring,3=precipitating,4=done

// Draw beaker outline
function drawBeaker() {
  bctx.clearRect(0,0,600,400);
  bctx.strokeStyle = '#333';
  bctx.lineWidth = 3;
  bctx.strokeRect(200,100,200,250);
}

// Swirl animation
function drawSwirl() {
  sctx.clearRect(0,0,600,400);
  const cx=300, cy=300, r=100;
  sctx.strokeStyle = 'rgba(128,0,128,0.5)';
  sctx.lineWidth = 4;
  sctx.beginPath();
  sctx.arc(cx,cy,r, swirlAngle, swirlAngle + Math.PI*1.5);
  sctx.stroke();
  swirlAngle += 0.05;
  swirlRAF = requestAnimationFrame(drawSwirl);
}

// Start stirring
function startStir() {
  stage = 2;
  updateHint('🌀 Stirring to initiate precipitation...');
  drawBeaker();
  drawSwirl();
  stirBtn.disabled = true;
  stirBtn.classList.add('opacity-50');
  setTimeout(stopStir, 2000);
}

// Stop swirling and spawn precipitate
function stopStir() {
  cancelAnimationFrame(swirlRAF);
  sctx.clearRect(0,0,600,400);
  stage = 3;
  updateHint('🌧️ Precipitate forming...');
  spawnParticles();
}

// Spawn and animate precipitate
function spawnParticles() {
  precipParticles = [];
  for (let i=0; i<150; i++) {
    precipParticles.push({
      x: 220 + Math.random()*160,
      y: 110,
      vy: 1 + Math.random()*1.5
    });
  }
  animateParticles();
}

// Animate particles falling
function animateParticles() {
  pctx.clearRect(0,0,600,400);
  precipParticles.forEach(p => {
    pctx.fillStyle = '#666';
    pctx.beginPath();
    pctx.arc(p.x, p.y, 4, 0,2*Math.PI);
    pctx.fill();
    p.y += p.vy;
  });
  precipParticles = precipParticles.filter(p => p.y < 350);
  if (precipParticles.length) {
    requestAnimationFrame(animateParticles);
  } else {
    stage = 4;
    updateHint('✅ Precipitation complete!');
    propEl.innerText = 'Precipitate Present';
  }
}

// Update hint text
function updateHint(txt) {
  hintEl.innerText = txt;
}

// Reset everything
function resetAll() {
  cancelAnimationFrame(swirlRAF);
  precipParticles = [];
  sctx.clearRect(0,0,600,400);
  pctx.clearRect(0,0,600,400);
  propEl.innerText = '';
  stage = 0;
  updateHint('Click Add Reagent to begin.');
  addBtn.disabled = false;
  stirBtn.disabled = true;
  stirBtn.classList.add('opacity-50');
  drawBeaker();
}

// Event handlers
addBtn.addEventListener('click', () => {
  stage = 1;
  updateHint('➕ Reagent added! Now stir the solution.');
  addBtn.disabled = true;
  stirBtn.disabled = false;
  stirBtn.classList.remove('opacity-50');
});
stirBtn.addEventListener('click', startStir);
resetBtn.addEventListener('click', resetAll);

// Initial setup
window.addEventListener('load', () => {
  drawBeaker();
  updateHint('Click Add Reagent to begin.');
  stirBtn.disabled = true;
  stirBtn.classList.add('opacity-50');
});
