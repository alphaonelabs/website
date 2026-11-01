// web/virtual_lab/static/virtual_lab/js/physics_mass_spring.js

document.addEventListener("DOMContentLoaded", () => {
  // ==== 1. Tutorial Overlay Logic ====
  const tutorialOverlay = document.getElementById("tutorial-overlay");
  const stepNumberElem   = document.getElementById("step-number");
  const stepList         = document.getElementById("step-list");
  const prevBtn          = document.getElementById("tutorial-prev");
  const nextBtn          = document.getElementById("tutorial-next");
  const skipBtn          = document.getElementById("tutorial-skip");

  const steps = [
    ["Drag the mass horizontally to set its initial displacement \(A\)."],
    ["Adjust the spring constant \(k\) and mass \(m\)."],
    ["Click “Start” to watch \(x(t) = A \cos(\omega t)\) with \(\omega = \sqrt{k/m}\)."],
    ["Observe the Position vs. Time graph and answer the quiz!"]
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
  const canvas         = document.getElementById("mass-spring-canvas");
  const ctx            = canvas.getContext("2d");

  const kSlider        = document.getElementById("k-slider");
  const kValue         = document.getElementById("k-value");
  const mSlider        = document.getElementById("m-slider");
  const mValue         = document.getElementById("m-value");
  const ASlider        = document.getElementById("A-slider");
  const AValue         = document.getElementById("A-value");

  const startBtn       = document.getElementById("start-mass-spring");
  const stopBtn        = document.getElementById("stop-mass-spring");
  const resetBtn       = document.getElementById("reset-mass-spring");

  const quizDiv        = document.getElementById("postlab-quiz");

  const readoutT       = document.getElementById("readout-t");
  const readoutX       = document.getElementById("readout-x");
  const readoutV       = document.getElementById("readout-v");
  const readoutA       = document.getElementById("readout-a");
  const readoutPE      = document.getElementById("readout-pe");
  const readoutKE      = document.getElementById("readout-ke");

  const barPE          = document.getElementById("bar-pe");
  const barKE          = document.getElementById("bar-ke");

  const positionCtx    = document.getElementById("position-chart").getContext("2d");

  // Physical constants & scaling
  const pxToM   = 0.01;          // 1 px = 0.01 m
  const mToPx   = 1 / pxToM;     // invert
  const equilibriumX = canvas.width / 2; // center pixel is equilibrium (x=0)

  // DOM Element–related state
  let k = Number.parseFloat(kSlider.value);    // N/m
  let m = Number.parseFloat(mSlider.value);    // kg
  let A = Number.parseFloat(ASlider.value);    // m
  let omega = Math.sqrt(k / m);         // rad/s

  // Simulation state
  let t0       = null;      // timestamp at “Start”
  let animId   = null;      // requestAnimationFrame ID
  let running  = false;     // true while animating

  // Derived state for this run
  let maxT     = (2 * Math.PI) / omega; // one full period

  // Chart.js: Position vs Time
  const posData = {
    labels: [],
    datasets: [{
      label: "x(t) (m)",
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
        y: { title: { display: true, text: "x (m)" } }
      },
      plugins: { legend: { display: false } }
    }
  });

  // Disable controls until tutorial ends
  startBtn.disabled      = true;
  stopBtn.disabled       = true;
  resetBtn.disabled      = true;
  kSlider.disabled       = true;
  mSlider.disabled       = true;
  ASlider.disabled       = true;


  // ==== 3. Enable Controls & Initial Draw ====
  function enableControls() {
    startBtn.disabled      = false;
    resetBtn.disabled      = false;
    kSlider.disabled       = false;
    mSlider.disabled       = false;
    ASlider.disabled       = false;
    drawScene(0); // draw mass at initial x = +A
  }

  // Draw mass‐spring system at time t (in seconds)
  function drawScene(t) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 3a) Parameters at current run
    const kVal = k;
    const mVal = m;
    const omegaVal = Math.sqrt(kVal / mVal);

    // 3b) Position x(t) in meters: x = A cos(omega t)
    const x_m = A * Math.cos(omegaVal * t);
    const v_m = -A * omegaVal * Math.sin(omegaVal * t);
    const a_m = -A * omegaVal * omegaVal * Math.cos(omegaVal * t);

    // 3c) Convert x_m to pixel: 0 m → equilibriumX px, positive → right
    const x_px = equilibriumX + x_m * mToPx;
    const massY = canvas.height / 2; // vertical position for the block
    const massSize = 20;             // 20×20 px block

    // Draw horizontal line (spring baseline)
    ctx.strokeStyle = "#4B5563";
    ctx.lineWidth   = 2;
    ctx.beginPath();
    ctx.moveTo(0, massY);
    ctx.lineTo(canvas.width, massY);
    ctx.stroke();

    // Draw spring “coils” from left wall (10 px) to mass position
    drawSpring(10, massY, x_px - massSize / 2, massY);

    // Draw mass as a square
    ctx.fillStyle = "#DC2626";
    ctx.fillRect(x_px - massSize / 2, massY - massSize / 2, massSize, massSize);
    ctx.strokeStyle = "#991B1B";
    ctx.strokeRect(x_px - massSize / 2, massY - massSize / 2, massSize, massSize);

    // 3d) Update numeric readouts
    readoutT.textContent  = t.toFixed(2);
    readoutX.textContent  = x_m.toFixed(2);
    readoutV.textContent  = v_m.toFixed(2);
    readoutA.textContent  = a_m.toFixed(2);

    const PE = 0.5 * kVal * x_m * x_m;      // ½ k x²
    const KE = 0.5 * mVal * v_m * v_m;      // ½ m v²
    readoutPE.textContent = PE.toFixed(2);
    readoutKE.textContent = KE.toFixed(2);

    // 3f) Update energy bars
    // Max total energy = ½ k A²
    const Emax = 0.5 * kVal * A * A;
    const peFrac = Emax > 0 ? Math.min(PE / Emax, 1) : 0;
    const keFrac = Emax > 0 ? Math.min(KE / Emax, 1) : 0;
    barPE.style.height = `${peFrac * 100}%`;
    barKE.style.height = `${keFrac * 100}%`;
  }

  // Draw a coiled spring from (x1,y1) to (x2,y2)
  function drawSpring(x1, y1, x2, y2) {
    const totalLength = x2 - x1;
    const coilCount = 12;               // number of loops
    const coilSpacing = totalLength / (coilCount + 1);
    const amplitude = 10;               // amplitude of the sine wave (px)

    ctx.strokeStyle = "#4A5568";
    ctx.lineWidth   = 2;
    ctx.beginPath();

    // Start at x1,y1
    ctx.moveTo(x1, y1);

    // For each coil, draw a half sine wave segment
    for (let i = 1; i <= coilCount; i++) {
      const cx = x1 + coilSpacing * i;
      const phase = (i % 2 === 0) ? Math.PI : 0; // alternate phase for up/down
      const px = cx;
      const py = y1 + Math.sin(phase) * amplitude;

      // Instead of a straight line, approximate with a small sine curve
      const steps = 10; // subdivide each coil into 10 segments
      for (let j = 0; j <= steps; j++) {
        const t = (j / steps);
        const sx = x1 + coilSpacing * (i - 1) + t * coilSpacing;
        const angle = ((i - 1 + t) * Math.PI);
        const sy = y1 + Math.sin(angle) * amplitude * ((i - 1 + t) % 2 === 0 ? 1 : -1);
        ctx.lineTo(sx, sy);
      }
    }

    // Finally connect to x2,y2
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }


  // ==== 4. Slider Change Handlers ====
  kSlider.addEventListener("input", () => {
    k = Number.parseFloat(kSlider.value);
    kValue.textContent = k.toFixed(0);
    omega = Math.sqrt(k / m);
    maxT  = (2 * Math.PI) / omega;
    if (!running) {
      drawScene(0);
    }
  });

  mSlider.addEventListener("input", () => {
    m = Number.parseFloat(mSlider.value);
    mValue.textContent = `${m.toFixed(1)} kg`;
    omega = Math.sqrt(k / m);
    maxT  = (2 * Math.PI) / omega;
    if (!running) {
      drawScene(0);
    }
  });

  ASlider.addEventListener("input", () => {
    A = Number.parseFloat(ASlider.value);
    AValue.textContent = A.toFixed(2);
    if (!running) {
      drawScene(0);
    }
  });


  // ==== 5. Animation Loop & Launch ====
  function step(timestamp) {
    if (!t0) {
      t0 = timestamp;
    }
    let elapsed = (timestamp - t0) / 1000; // seconds since start
    if (elapsed >= maxT) {
      // One full oscillation complete → reveal quiz
      drawScene(maxT);
      revealQuiz();
      return;
    }
    drawScene(elapsed);

    // Update Position vs Time chart
    posChart.data.labels.push(elapsed.toFixed(2));
    const x_m = A * Math.cos(omega * elapsed);
    posChart.data.datasets[0].data.push(x_m.toFixed(2));
    posChart.update("none");

    animId = requestAnimationFrame(step);
  }

  startBtn.addEventListener("click", () => {
    // Disable controls while animating
    kSlider.disabled    = true;
    mSlider.disabled    = true;
    ASlider.disabled    = true;
    startBtn.disabled   = true;
    stopBtn.disabled    = false;
    resetBtn.disabled   = true;

    // Prepare for launch
    omega = Math.sqrt(k / m);
    maxT  = (2 * Math.PI) / omega;
    t0    = null;

    // Clear chart
    posChart.data.labels = [];
    posChart.data.datasets[0].data = [];
    posChart.update("none");

    running = true;
    animId = requestAnimationFrame(step);
  });

  stopBtn.addEventListener("click", () => {
    if (animId) cancelAnimationFrame(animId);
    running = false;
    stopBtn.disabled    = true;
    startBtn.disabled   = false;
    resetBtn.disabled   = false;
  });

  resetBtn.addEventListener("click", () => {
    if (animId) cancelAnimationFrame(animId);
    running = false;
    t0       = null;
    // Re-enable sliders
    kSlider.disabled    = false;
    mSlider.disabled    = false;
    ASlider.disabled    = false;
    startBtn.disabled   = false;
    stopBtn.disabled    = true;
    resetBtn.disabled   = false;
    quizDiv.classList.add("hidden");

    // Clear chart
    posChart.data.labels = [];
    posChart.data.datasets[0].data = [];
    posChart.update("none");

    // Redraw at t=0
    drawScene(0);
  });


  // ==== 6. Quiz Reveal ====
  function revealQuiz() {
    stopBtn.disabled    = true;
    resetBtn.disabled   = false;
    quizDiv.classList.remove("hidden");
  }


  // ==== 7. Initial Draw ====
  drawScene(0);
});
