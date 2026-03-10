// static/virtual_lab/js/chemistry/titration.js

const beakerCanvas = document.getElementById('titration-canvas');
const bctx         = beakerCanvas.getContext('2d');
const dropCanvas   = document.getElementById('drop-canvas');
const dctx         = dropCanvas.getContext('2d');

let titrantVolume = 0, loopID;

// Draw beaker + liquid
function drawBeaker(pH) {
  bctx.clearRect(0,0,600,400);
  bctx.fillStyle = '#ccc'; bctx.fillRect(200,100,200,250);
  bctx.fillStyle = getColor(pH); bctx.fillRect(205,105,190,240);
  bctx.strokeStyle = '#333'; bctx.strokeRect(200,100,200,250);
  bctx.fillStyle = '#000'; bctx.font = '16px Arial';
  bctx.fillText(`pH: ${pH.toFixed(2)}`, 240, 380);
}

// Indicator color mapping
function getColor(pH) {
  if (pH < 4)   return '#ff4d4d';
  if (pH < 6)   return '#ff944d';
  if (pH < 7.5) return '#ffff66';
  if (pH < 9)   return '#66ff99';
                 return '#66b3ff';
}

// Compute pH
function computePH(aC,bC,aV,bV) {
  const molA = aC*aV/1000, molB = bC*bV/1000;
  const net  = molB - molA, totV = (aV + bV)/1000;
  if (Math.abs(net) < 1e-6) return 7;
  return net < 0
    ? -Math.log10(-net/totV)
    : 14 + Math.log10(net/totV);
}

// Update the hint message
function updateHint(pH) {
  const hint = document.getElementById('hint');
  if (pH < 3)        hint.innerText = '🔴 Very acidic! Add more base slowly.';
  else if (pH < 6)   hint.innerText = '🟠 Still acidic—keep titrant coming.';
  else if (pH < 6.5) hint.innerText = '🟡 Approaching endpoint—go slow!';
  else if (pH < 7.5) hint.innerText = '🟢 Almost neutral—nice!';
  else if (pH < 9)   hint.innerText = '🔵 Slightly basic now.';
  else               hint.innerText = '💙 Basic—endpoint passed.';
}

// Display final property
function displayProperty(pH) {
  const propEl = document.getElementById('property');
  if (!propEl) return; // Defensive check

  let prop;
  const translations = window.translations || {}; // More robust null handling

  if (pH < 7)      prop = translations.acidic || 'Acidic';
  else if (pH === 7) prop = translations.neutral || 'Neutral';
  else              prop = translations.basic || 'Basic';

  const solutionIs = translations.solution_is || 'Solution is';
  propEl.innerText = solutionIs + ' ' + prop;
}

// Animate one drop
function animateDrop() {
  dctx.clearRect(0,0,600,400);
  let y = 0, x = 300;
  const id = setInterval(()=>{
    dctx.clearRect(0,0,600,400);
    dctx.fillStyle = '#66b3ff';
    dctx.beginPath(); dctx.arc(x,y,6,0,2*Math.PI); dctx.fill();
    y += 5;
    if (y > 110) {
      clearInterval(id);
      setTimeout(()=> dctx.clearRect(0,0,600,400), 50);
    }
  }, 20);
}

// Start titration
function startTitration() {
  const aC = parseFloat(document.getElementById('acid-conc').value);
  const bC = parseFloat(document.getElementById('base-conc').value);
  const aV = parseFloat(document.getElementById('acid-vol').value);
  titrantVolume = 0;
  clearInterval(loopID);

  loopID = setInterval(()=>{
    titrantVolume += 0.2;
    if (titrantVolume > 50) {
      clearInterval(loopID);
      const finalPH = computePH(aC,bC,aV,titrantVolume);
      displayProperty(finalPH);
      return;
    }
    animateDrop();
    setTimeout(()=>{
      const pH = computePH(aC,bC,aV,titrantVolume);
      drawBeaker(pH);
      document.getElementById('titrant-volume').innerText = titrantVolume.toFixed(1);
      updateHint(pH);
    }, 400);
  }, 600);
}

// Reset everything
function resetTitration() {
  clearInterval(loopID);
  dctx.clearRect(0,0,600,400);
  titrantVolume = 0;
  document.getElementById('titrant-volume').innerText = '0';
  document.getElementById('hint').innerText = '';
  document.getElementById('property').innerText = '';
  drawBeaker(1);
}

// Initial draw
window.addEventListener('load', () => {
  drawBeaker(1);
  updateHint(1);
});
