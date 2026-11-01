// static/virtual_lab/js/chemistry/ph_indicator.js

const width = 600, height = 400;

// Canvases & contexts
const indCv   = document.getElementById('indicator-canvas'),
      indCtx  = indCv.getContext('2d');
const dropCv  = document.getElementById('drop-canvas'),
      dropCtx = dropCv.getContext('2d');
const confCv  = document.getElementById('confetti-canvas'),
      confCtx = confCv.getContext('2d');

const updateBtn = document.getElementById('update-btn'),
      resetBtn  = document.getElementById('reset-btn'),
      hintEl    = document.getElementById('hint'),
      propEl    = document.getElementById('property'),
      phInput   = document.getElementById('solution-ph');

let confettiParticles = [];

// 1. pH → color
function getColor(ph) {
  if (ph < 3)    return '#ff0000';
  if (ph < 6)    return '#ff9900';
  if (ph < 8)    return '#ffff00';
  if (ph < 11)   return '#66ff66';
                 return '#0000ff';
}

// 2. pH → property
function getProperty(ph) {
  if (ph < 7)   return '{% trans "Acidic" %}';
  if (ph === 7) return '{% trans "Neutral" %}';
                return '{% trans "Basic" %}';
}

// Draw the main indicator rectangle + pH label
function drawIndicator(ph) {
  indCtx.clearRect(0, 0, width, height);
  // Fill
  indCtx.fillStyle = getColor(ph);
  indCtx.fillRect(100, 75, 400, 250);
  // Border pulse
  indCtx.lineWidth = 8;
  indCtx.strokeStyle = '#333';
  indCtx.strokeRect(100, 75, 400, 250);
  // Label
  indCtx.fillStyle = '#000';
  indCtx.font = '24px Arial';
  indCtx.fillText(`pH: ${ph.toFixed(1)}`, 260, 360);
}

// Animate a single drop falling & splashing
function animateDrop(ph) {
  dropCtx.clearRect(0,0,width,height);
  const dropX = 300, startY = 0, groundY = 75;
  let y = startY;
  const id = setInterval(() => {
    dropCtx.clearRect(0,0,width,height);
    dropCtx.fillStyle = '#66b3ff';
    dropCtx.beginPath();
    dropCtx.arc(dropX, y, 6, 0, 2*Math.PI);
    dropCtx.fill();
    y += 8;
    if (y > groundY) {
      clearInterval(id);
      // Splash circle
      let r = 0;
      const sid = setInterval(()=>{
        dropCtx.clearRect(0,0,width,height);
        dropCtx.beginPath();
        dropCtx.arc(dropX, groundY, r, 0, 2*Math.PI);
        dropCtx.strokeStyle = '#66b3ff';
        dropCtx.lineWidth = 2;
        dropCtx.stroke();
        r += 2;
        if (r > 40) {
          clearInterval(sid);
          dropCtx.clearRect(0,0,width,height);
        }
      }, 30);
    }
  }, 30);
}

// Create confetti particles when neutral
function spawnConfetti() {
  confettiParticles = Array.from({length:100}, () => ({
    x: Math.random()*width,
    y: -10,
    vy: 2 + Math.random()*2,
    color: `hsl(${Math.random()*360},70%,60%)`
  }));
  requestAnimationFrame(updateConfetti);
}

function updateConfetti() {
  confCtx.clearRect(0,0,width,height);
  confettiParticles.forEach(p => {
    confCtx.fillStyle = p.color;
    confCtx.fillRect(p.x, p.y, 6, 6);
    p.y += p.vy;
  });
  confettiParticles = confettiParticles.filter(p => p.y < height);
  if (confettiParticles.length) requestAnimationFrame(updateConfetti);
}

// Update entire UI on pH change
function updateUI(ph) {
  drawIndicator(ph);
  animateDrop(ph);
  hintEl.innerText = `🎉 Indicator shows ${getProperty(ph)}!`;
  propEl.innerText = `{% trans "Solution is" %} ${getProperty(ph)}.`;
  if (ph === 7) spawnConfetti();
}

// Button handlers
updateBtn.addEventListener('click', ()=>{
  let ph = parseFloat(phInput.value);
  if (isNaN(ph) || ph < 0 || ph > 14) {
    hintEl.innerText = '{% trans "Please enter a valid pH between 0 and 14." %}';
    return;
  }
  updateUI(ph);
});

resetBtn.addEventListener('click', ()=>{
  indCtx.clearRect(0,0,width,height);
  dropCtx.clearRect(0,0,width,height);
  confCtx.clearRect(0,0,width,height);
  phInput.value = 7;
  hintEl.innerText = '{% trans "Enter a pH value (0–14) and click Update to see the color change." %}';
  propEl.innerText = '';
  drawIndicator(7);
});

// Initial draw
window.addEventListener('load', ()=> drawIndicator(7));
