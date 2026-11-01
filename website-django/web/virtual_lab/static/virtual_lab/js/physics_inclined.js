// web/virtual_lab/static/virtual_lab/js/physics_inclined.js

document.addEventListener("DOMContentLoaded", () => {
  // ==== 1. Tutorial Overlay Logic ====
  const tutorialOverlay = document.getElementById("tutorial-overlay");
  const stepNumberElem   = document.getElementById("step-number");
  const stepList         = document.getElementById("step-list");
  const prevBtn          = document.getElementById("tutorial-prev");
  const nextBtn          = document.getElementById("tutorial-next");
  const skipBtn          = document.getElementById("tutorial-skip");

  const steps = [
    ["Drag the block along the ramp to set its starting position."],
    ["Adjust angle, friction, and mass to see how physics changes."],
    ["Click “Launch” and watch live readouts, force vectors, and energy bars."],
    ["Observe the real-time Position vs Time graph and answer the quiz!"]
  ];

  let currentStep = 0;
  function showStep(i) {
    stepNumberElem.textContent = i + 1;
    stepList.innerHTML = "";
    steps[i].forEach((text, idx) => {
      const li = document.createElement("li");
      li.textContent = text;
      li.className = "opacity-0 transition-opacity duration-500";
      stepList.appendChild(li);
      setTimeout(() => {
        li.classList.remove("opacity-0");
        li.classList.add("opacity-100");
      }, idx * 200);
    });
    prevBtn.disabled = i === 0;
    nextBtn.textContent = i === steps.length - 1 ? "Begin Experiment" : "Next";
  }

  showStep(currentStep);
  prevBtn.addEventListener("click", () => {
    if (currentStep > 0) {
      currentStep--;
      showStep(currentStep);
    }
  });
  nextBtn.addEventListener("click", () => {
    if (currentStep < steps.length - 1) {
      currentStep++;
      showStep(currentStep);
    } else {
      tutorialOverlay.style.display = "none";
      enableControls();
    }
  });
  skipBtn.addEventListener("click", () => {
    tutorialOverlay.style.display = "none";
    enableControls();
  });
  // ==== End Tutorial Overlay Logic ====


  // ==== 2. DOM References & State ====
  const canvas         = document.getElementById("inclined-canvas");
  const ctx            = canvas.getContext("2d");
  if(!ctx)
  {
    console.error("Failed to get 2D context for canvas");
    return;
  }

  const angleSlider    = document.getElementById("angle-slider");
  const angleValue     = document.getElementById("angle-value");
  const frictionSlider = document.getElementById("friction-slider");
  const frictionValue  = document.getElementById("friction-value");
  const massSlider     = document.getElementById("mass-slider");
  const massValue      = document.getElementById("mass-value");

  const startBtn       = document.getElementById("start-inclined");
  const stopBtn        = document.getElementById("stop-inclined");
  const resetBtn       = document.getElementById("reset-inclined");

  const quizDiv        = document.getElementById("postlab-quiz");

  const readoutS       = document.getElementById("readout-s");
  const readoutV       = document.getElementById("readout-v");
  const readoutA       = document.getElementById("readout-a");
  const readoutPE      = document.getElementById("readout-pe");
  const readoutKE      = document.getElementById("readout-ke");

  const barPE          = document.getElementById("bar-pe");
  const barKE          = document.getElementById("bar-ke");

  const positionCtx    = document.getElementById("position-chart").getContext("2d");

  // Physical constants & scaling
  const G       = 9.81;                 // m/s²
  const pxToM   = 0.01;                 // 1 px = 0.01 m
  const mToPx   = 1 / pxToM;            // inverse
  const rampPx  = 300;                  // 300 px → 3 m
  const rampLen = rampPx * pxToM;       // 3 m

  // Canvas dimensions & ramp origin
  const W       = canvas.width;         // 600 px
  const H       = canvas.height;        // 400 px
  const originX = 50;                   // left margin
  const originY = H - 50;               // bottom margin

  // Experiment state
  let alphaDeg = Number.parseFloat(angleSlider.value);     // initial angle
  let alphaRad = (alphaDeg * Math.PI) / 180;

  let mu       = Number.parseFloat(frictionSlider.value);  // friction coefficient
  let mass     = Number.parseFloat(massSlider.value);      // mass in kg

  let aAcc     = G * Math.sin(alphaRad)            // net accel down-ramp
                 - mu * G * Math.cos(alphaRad);

  // Block state
  let s        = 0;       // distance along plane (m) from top
  let v        = 0;       // speed (m/s)
  let t0       = null;    // timestamp at launch
  let animId   = null;    // requestAnimationFrame id
  let running  = false;   // true while animating

  // Ramp geometry (recompute whenever angle changes)
  let basePx, heightPx;
  function updateRampGeometry() {
    basePx   = rampPx * Math.cos(alphaRad);
    heightPx = rampPx * Math.sin(alphaRad);
  }
  updateRampGeometry();

  // Chart.js: Position vs Time
  const posData = {
    labels: [],
    datasets: [{
      label: "Position (m)",
      data: [],
      borderColor: "#1E40AF",
      borderWidth: 2,
      fill: false,
      pointRadius: 0
    }]
  };
  const posChart = new Chart(positionCtx, {
    type: "line",
    data: posData,
    options: {
      animation: false,
      scales: {
        x: { title: { display: true, text: "Time (s)" } },
        y: { title: { display: true, text: "s (m)" } }
      },
      plugins: { legend: { display: false } }
    }
  });

  // Disable controls until tutorial ends
  startBtn.disabled       = true;
  stopBtn.disabled        = true;
  resetBtn.disabled       = true;
  angleSlider.disabled    = true;
  frictionSlider.disabled = true;
  massSlider.disabled     = true;


  // ==== 3. Enable Controls & Initial Draw ====
  function enableControls() {
    startBtn.disabled       = false;
    resetBtn.disabled       = false;
    angleSlider.disabled    = false;
    frictionSlider.disabled = false;
    massSlider.disabled     = false;
    drawScene();
  }

  // Draw wedge, block, forces, and update UI
  function drawScene() {
    ctx.clearRect(0, 0, W, H);

    // --- 3a) Draw ramp as a 3D‐style wedge with gradient ---
    const grad = ctx.createLinearGradient(
      originX, originY - heightPx,
      originX + basePx, originY
    );
    grad.addColorStop(0, "#F3F4F6");
    grad.addColorStop(1, "#E5E7EB");

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(originX, originY);
    ctx.lineTo(originX + basePx, originY);
    ctx.lineTo(originX, originY - heightPx);
    ctx.closePath();
    ctx.fill();

    // Outline the triangle
    ctx.strokeStyle = "#4B5563";
    ctx.lineWidth   = 2;
    ctx.beginPath();
    ctx.moveTo(originX, originY);
    ctx.lineTo(originX + basePx, originY);
    ctx.lineTo(originX, originY - heightPx);
    ctx.closePath();
    ctx.stroke();

    // --- 3b) Compute block’s pixel position on ramp ---
    const topX = originX;
    const topY = originY - heightPx;
    const d_px = (s / rampLen) * rampPx;  // px from top down the plane
    const blockX = topX + d_px * Math.cos(alphaRad);
    const blockY = topY + d_px * Math.sin(alphaRad);

    // Draw block as rotated square (12×12 px)
    const blkSize = 12;
    ctx.save();
    ctx.translate(blockX, blockY);
    ctx.rotate(-alphaRad);
    ctx.fillStyle = "#DC2626";
    ctx.fillRect(-blkSize / 2, -blkSize / 2, blkSize, blkSize);
    ctx.strokeStyle = "#991B1B";
    ctx.lineWidth = 1;
    ctx.strokeRect(-blkSize / 2, -blkSize / 2, blkSize, blkSize);
    ctx.restore();

    // --- 3c) Draw force vectors at block center ---
    drawForceVectors(blockX, blockY);

    // --- 3d) Update numeric readouts ---
    readoutS.textContent = s.toFixed(2);
    readoutV.textContent = v.toFixed(2);
    readoutA.textContent = aAcc.toFixed(2);

    const heightM = (rampLen - s) * Math.sin(alphaRad);
    const PE = mass * G * heightM;
    const KE = 0.5 * mass * v * v;
    readoutPE.textContent = PE.toFixed(2);
    readoutKE.textContent = KE.toFixed(2);

    // --- 3e) Update energy bars ---
    const maxPE = mass * G * (rampLen * Math.sin(alphaRad));
    const peFrac = maxPE > 0 ? Math.min(PE / maxPE, 1) : 0;
    const keFrac = maxPE > 0 ? Math.min(KE / maxPE, 1) : 0;
    barPE.style.height = `${peFrac * 100}%`;
    barKE.style.height = `${keFrac * 100}%`;
  }

  // Draw mg sinα (red), mg cosα (blue), friction (yellow) at block pos
  function drawForceVectors(cx, cy) {
    ctx.save();
    ctx.translate(cx, cy);

    // 1) mg sin α (red)
    const redLen = 30; // px
    ctx.strokeStyle = "#DC2626";
    ctx.lineWidth   = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(redLen * Math.cos(alphaRad), redLen * Math.sin(alphaRad));
    ctx.stroke();
    drawArrowhead(redLen * Math.cos(alphaRad), redLen * Math.sin(alphaRad), alphaRad);

    // 2) mg cos α (blue) → perpendicular
    const blueLen = 20;
    const perpAngle = alphaRad - Math.PI / 2;
    ctx.strokeStyle = "#3B82F6";
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(blueLen * Math.cos(perpAngle), blueLen * Math.sin(perpAngle));
    ctx.stroke();
    drawArrowhead(blueLen * Math.cos(perpAngle), blueLen * Math.sin(perpAngle), perpAngle);

    // 3) friction (yellow) uphill (opposite motion) if μ>0
    if (mu > 0) {
      const yellowLen = 25;
      const fricAngle = alphaRad + Math.PI; // uphill
      ctx.strokeStyle = "#FBBF24";
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(yellowLen * Math.cos(fricAngle), yellowLen * Math.sin(fricAngle));
      ctx.stroke();
      drawArrowhead(yellowLen * Math.cos(fricAngle), yellowLen * Math.sin(fricAngle), fricAngle);
    }

    ctx.restore();
  }

  // Draw an arrowhead at (x,y), pointing angle θ
  function drawArrowhead(x, y, θ) {
    const size = 6;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(θ);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(-size, size / 2);
    ctx.lineTo(-size, -size / 2);
    ctx.closePath();
    ctx.fillStyle = ctx.strokeStyle;
    ctx.fill();
    ctx.restore();
  }


  // ==== 4. Slider Change Handlers ====
  angleSlider.addEventListener("input", () => {
    alphaDeg = Number.parseFloat(angleSlider.value);
    alphaRad = (alphaDeg * Math.PI) / 180;
    angleValue.textContent = `${alphaDeg}°`;
    updateDynamics();
    updateRampGeometry();
    if (!running) {
      s = 0;
      drawScene();
    }
  });

  frictionSlider.addEventListener("input", () => {
    mu = Number.parseFloat(frictionSlider.value);
    frictionValue.textContent = mu.toFixed(2);
    updateDynamics();
    if (!running) drawScene();
  });

  massSlider.addEventListener("input", () => {
    mass = Number.parseFloat(massSlider.value);
    massValue.textContent = `${mass.toFixed(1)} kg`;
    if (!running) drawScene();
  });

  function updateDynamics() {
    aAcc = G * Math.sin(alphaRad) - mu * G * Math.cos(alphaRad);
  }


  // ==== Helper: Map MouseEvent → Canvas Coordinates ====
  function getMousePos(evt) {
    const rect = canvas.getBoundingClientRect();
    // How many canvas pixels correspond to one CSS px?
    const scaleX = canvas.width  / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
      x: (evt.clientX - rect.left) * scaleX,
      y: (evt.clientY - rect.top)  * scaleY
    };
  }


  // ==== 5. Drag-to-Place Logic (with scaling) ====
  let isDragging = false;

  canvas.addEventListener("mousedown", (e) => {
    const mouse = getMousePos(e);

    // Block’s pixel position (in internal 600×400 coordinate):
    const topX = originX;
    const topY = originY - heightPx;
    const d_px = (s / rampLen) * rampPx;
    const bx = topX + d_px * Math.cos(alphaRad);
    const by = topY + d_px * Math.sin(alphaRad);

    // If click is within ~10 px (in canvas coords) of the block, start dragging:
    if (Math.hypot(mouse.x - bx, mouse.y - by) < 10) {
      isDragging = true;
      stopAnimation();
    }
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const mouse = getMousePos(e);

    // Project onto the ramp line to find new s:
    const topX = originX;
    const topY = originY - heightPx;
    const dx = mouse.x - topX;
    const dy = mouse.y - topY;
    // t* = ( (mx-topX)cosα + (my-topY)sinα ), in px along ramp
    const tStar = dx * Math.cos(alphaRad) + dy * Math.sin(alphaRad);
    const tClamped = Math.min(Math.max(tStar, 0), rampPx);

    s = (tClamped / rampPx) * rampLen; // convert px→m
    drawScene();
  });

  canvas.addEventListener("mouseup", () => {
    if (isDragging) isDragging = false;
  });


  // ==== 6. Animation Loop & Launch (with scaled coords) ====
  let s0 = 0;

  function step(timestamp) {
    if (!t0) {
      t0 = timestamp;
      v  = 0;
    }
    const t = (timestamp - t0) / 1000; // seconds
    const sNew = s0 + 0.5 * aAcc * t * t;

    // If net acceleration ≤ 0, it will not move
    if (aAcc <= 0) {
      cancelAnimationFrame(animId);
      running = false;
      stopBtn.disabled  = true;
      startBtn.disabled = false;
      resetBtn.disabled = false;
      return;
    }

    if (sNew >= rampLen) {
      s = rampLen;
      v = aAcc * t;
      drawScene();
      revealQuiz();
      return;
    }

    s = sNew;
    v = aAcc * t;
    drawScene();

    // Update Position vs Time chart
    posChart.data.labels.push(t.toFixed(2));
    posChart.data.datasets[0].data.push(s.toFixed(2));
    posChart.update("none");

    animId = requestAnimationFrame(step);
  }

  startBtn.addEventListener("click", () => {
    angleSlider.disabled    = true;
    frictionSlider.disabled = true;
    massSlider.disabled     = true;
    startBtn.disabled       = true;
    stopBtn.disabled        = false;
    resetBtn.disabled       = true;

    s0       = s;
    v        = 0;
    t0       = null;
    running  = true;

    // Clear chart
    posChart.data.labels = [];
    posChart.data.datasets[0].data = [];
    posChart.update("none");

    animId = requestAnimationFrame(step);
  });

  function stopAnimation() {
    if (animId) {
      cancelAnimationFrame(animId);
      running = false;
      stopBtn.disabled    = true;
      startBtn.disabled   = false;
      resetBtn.disabled   = false;
    }
  }

  stopBtn.addEventListener("click", stopAnimation);

  resetBtn.addEventListener("click", () => {
    if (animId) cancelAnimationFrame(animId);
    running = false;
    s       = 0;
    v       = 0;
    t0      = null;
    angleSlider.disabled    = false;
    frictionSlider.disabled = false;
    massSlider.disabled     = false;
    startBtn.disabled       = false;
    stopBtn.disabled        = true;
    resetBtn.disabled       = false;
    quizDiv.classList.add("hidden");

    // Clear chart
    posChart.data.labels = [];
    posChart.data.datasets[0].data = [];
    posChart.update("none");

    drawScene();
  });


  // ==== 7. Quiz Reveal ====
  function revealQuiz() {
    stopBtn.disabled  = true;
    resetBtn.disabled = false;
    quizDiv.classList.remove("hidden");
  }


  // ==== 8. Initial Draw ====
  drawScene();
});
