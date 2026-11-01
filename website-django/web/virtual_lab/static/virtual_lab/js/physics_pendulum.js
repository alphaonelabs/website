// web/virtual_lab/static/virtual_lab/js/physics_pendulum.js

document.addEventListener("DOMContentLoaded", () => {
  // -------- Tutorial Logic with Animated Steps -------- //
  const tutorialOverlay = document.getElementById("tutorial-overlay");
  const stepNumberElem = document.getElementById("step-number");
  const stepList = document.getElementById("step-list");
  const prevBtn = document.getElementById("tutorial-prev");
  const nextBtn = document.getElementById("tutorial-next");
  const skipBtn = document.getElementById("tutorial-skip");

  // Each step is an array of bullet‐point strings
  const steps = [
    ["A pendulum consists of a mass (bob) attached to a string, swinging under gravity."],
    [
      "The length (L) of the string determines how fast it swings.",
      "Longer pendulum → slower oscillation; shorter → faster."
    ],
    [
      "The angular frequency ω = √(g / L), where g ≈ 9.81 m/s².",
      "ω tells us how quickly the pendulum oscillates."
    ],
    [
      "The motion follows θ(t) = θ₀ · cos(ω t),",
      "where θ₀ is the initial amplitude in radians."
    ],
    [
      "After one period T = 2π / ω, the pendulum returns to its start.",
      "Click 'Next' to begin the experiment!"
    ]
  ];

  let currentStep = 0;

  function showStep(index) {
    stepNumberElem.textContent = index + 1;
    stepList.innerHTML = "";
    steps[index].forEach((text, idx) => {
      const li = document.createElement("li");
      li.textContent = text;
      li.className = "opacity-0 transition-opacity duration-500";
      stepList.appendChild(li);
      setTimeout(() => {
        li.classList.remove("opacity-0");
        li.classList.add("opacity-100");
      }, idx * 200);
    });
    prevBtn.disabled = index === 0;
    nextBtn.textContent = index === steps.length - 1 ? "Begin Experiment" : "Next";
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
      tutorialOverlay.classList.add("hidden");
      enableControls();
    }
  });

  skipBtn.addEventListener("click", () => {
    tutorialOverlay.classList.add("hidden");
    enableControls();
  });
  // -------- End Animated Tutorial Logic -------- //

  // -------- Simulation, Chart, Energy, Trail & Readouts -------- //
  const canvas = document.getElementById("pendulum-canvas");
  const ctx = canvas.getContext("2d");
  const lengthSlider = document.getElementById("length-slider");
  const lengthValue = document.getElementById("length-value");
  const startButton = document.getElementById("start-pendulum");
  const stopButton = document.getElementById("stop-pendulum");
  const postlabQuiz = document.getElementById("postlab-quiz");

  // Energy bars
  const peBar = document.getElementById("pe-bar");
  const keBar = document.getElementById("ke-bar");

  // Numeric readouts
  const timeReadout = document.getElementById("time-readout");
  const angleReadout = document.getElementById("angle-readout");
  const speedReadout = document.getElementById("speed-readout");

  // Chart.js mini‐graph
  const chartCanvas = document.getElementById("angle-chart").getContext("2d");

  // Physical constants and state
  const g = 9.81;             // m/s²
  const originX = canvas.width / 2;
  const originY = 50;         // pivot-point y-coordinate
  const pixelsPerMeter = 100; // 1 m → 100 px
  const bobRadius = 15;       // px

  let L = Number.parseFloat(lengthSlider.value); // length in meters
  let omega = Math.sqrt(g / L);           // angular frequency
  let theta0 = 0.3;    // initial amplitude (rad)
  let currentAngle = theta0;
  let animationId = null;
  let startTime = null;

  // For drag-and-release
  let isDragging = false;
  let dragAngle = 0;

  // Initialize Chart.js
  const angleChart = new Chart(chartCanvas, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label: "θ(t) (rad)",
        data: [],
        borderColor: "#FF6633",
        borderWidth: 2,
        fill: false,
        pointRadius: 0,
      }]
    },
    options: {
      animation: false,
      scales: {
        x: { title: { display: true, text: "Time (s)" } },
        y: { title: { display: true, text: "Angle (rad)" }, min: -theta0, max: theta0 }
      },
      plugins: { legend: { display: false } }
    }
  });

  // Draw pendulum with a "trail" effect
  function drawPendulum(angle, length) {
    ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const r = length * pixelsPerMeter;
    const bobX = originX + r * Math.sin(angle);
    const bobY = originY + r * Math.cos(angle);

    // Draw rod
    ctx.beginPath();
    ctx.moveTo(originX, originY);
    ctx.lineTo(bobX, bobY);
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw bob
    ctx.beginPath();
    ctx.arc(bobX, bobY, bobRadius, 0, 2 * Math.PI);
    ctx.fillStyle = "#007BFF";
    ctx.fill();
    ctx.strokeStyle = "#0056b3";
    ctx.stroke();
  }

  // Convert mouse coords → angle from vertical
  function computeAngleFromMouse(mouseX, mouseY, length) {
    const dx = mouseX - originX;
    const dy = mouseY - originY;
    const r = length * pixelsPerMeter;
    const dist = Math.hypot(dx, dy);
    const scale = r / dist;
    const px = dx * scale;
    const py = dy * scale;
    return Math.atan2(px, py);
  }

  // Animation loop: updates everything each frame
  function animatePendulum(timestamp) {
    if (!startTime) startTime = timestamp;
    const elapsedSec = (timestamp - startTime) / 1000; // ms → s

    // Angle: θ(t) = θ₀ cos(ω t)
    const angle = theta0 * Math.cos(omega * elapsedSec);
    currentAngle = angle;

    // 1) Draw pendulum with trail
    drawPendulum(angle, L);

    // 2) Update mini-graph
    if (angleChart.data.labels.length > 100) {
      angleChart.data.labels.shift();
      angleChart.data.datasets[0].data.shift();
    }
    angleChart.data.labels.push(elapsedSec.toFixed(2));
    angleChart.data.datasets[0].data.push(angle);
    angleChart.update("none");

    // 3) Compute energies (m = 1 kg)
    const h = L * (1 - Math.cos(angle));   // height above bottom
    const pe = g * h;                      // PE = m g h (m=1)
    // Velocity: v = L * (dθ/dt) = L * (−θ₀ ω sin(ωt))
    const v = -L * theta0 * omega * Math.sin(omega * elapsedSec);
    const ke = 0.5 * v * v;                // KE = ½ m v² (m=1)
    const E = pe + ke;
    const pePct = E ? (pe / E) * 100 : 0;
    const kePct = E ? (ke / E) * 100 : 0;
    peBar.style.width = `${pePct.toFixed(1)}%`;
    keBar.style.width = `${kePct.toFixed(1)}%`;

    // 4) Update numeric readouts
    timeReadout.textContent = elapsedSec.toFixed(2);
    angleReadout.textContent = (angle * (180 / Math.PI)).toFixed(1);
    speedReadout.textContent = Math.abs(v).toFixed(2);

    // 5) Reveal quiz after one full period
    const period = (2 * Math.PI) / omega;
    if (elapsedSec >= period && postlabQuiz.classList.contains("hidden")) {
      postlabQuiz.classList.remove("hidden");
    }

    animationId = requestAnimationFrame(animatePendulum);
  }

  // Enable controls after tutorial ends
  function enableControls() {
    startButton.disabled = false;
    stopButton.disabled = false;
    lengthSlider.disabled = false;
    currentAngle = theta0;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawPendulum(currentAngle, L);
  }

  // Initially disable controls
  startButton.disabled = true;
  stopButton.disabled = true;
  lengthSlider.disabled = true;

  // Update length L & ω on slider input
  lengthSlider.addEventListener("input", () => {
    L = Number.parseFloat(lengthSlider.value);
    lengthValue.textContent = `${L.toFixed(1)} m`;
    omega = Math.sqrt(g / L);
    // Adjust chart y-axis
    angleChart.options.scales.y.min = -theta0;
    angleChart.options.scales.y.max = theta0;
    angleChart.update("none");

    if (!isDragging && !animationId) {
      currentAngle = theta0;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      drawPendulum(currentAngle, L);
    }
  });

  // Start button: reset chart, energy bars, trail
  startButton.addEventListener("click", () => {
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
      postlabQuiz.classList.add("hidden");
    }

    // Clear canvas fully
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Reset chart
    angleChart.data.labels = [];
    angleChart.data.datasets[0].data = [];
    angleChart.update("none");

    // Reset energy bars
    peBar.style.width = "0%";
    keBar.style.width = "0%";

    // Reset numeric readouts
    timeReadout.textContent = "0.00";
    angleReadout.textContent = (theta0 * (180 / Math.PI)).toFixed(1);
    speedReadout.textContent = "0.00";

    // Use currentAngle (maybe from drag) as θ₀
    theta0 = currentAngle;
    angleChart.options.scales.y.min = -theta0;
    angleChart.options.scales.y.max = theta0;
    angleChart.update("none");

    startTime = null;
    animationId = requestAnimationFrame(animatePendulum);
  });

  // Stop button: cancel animation
  stopButton.addEventListener("click", () => {
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawPendulum(currentAngle, L);
  });

  // -------- Drag & Release Logic (Mouse + Touch) -------- //

  // Helper function to get coordinates from mouse or touch event
  function getEventCoords(e) {
    const rect = canvas.getBoundingClientRect();
    if (e.type.startsWith('touch')) {
      return {
        x: e.touches[0].clientX - rect.left,
        y: e.touches[0].clientY - rect.top
      };
    } else {
      return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      };
    }
  }

  // Helper function to start dragging
  function startDrag(e) {
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }

    const coords = getEventCoords(e);
    const r = L * pixelsPerMeter;
    const bobX = originX + r * Math.sin(currentAngle);
    const bobY = originY + r * Math.cos(currentAngle);
    const distToBob = Math.hypot(coords.x - bobX, coords.y - bobY);

    if (distToBob <= bobRadius + 3) {
      isDragging = true;
      dragAngle = currentAngle;
      e.preventDefault(); // Prevent default for touch events
    }
  }

  // Helper function to handle dragging
  function handleDrag(e) {
    if (!isDragging) return;

    const coords = getEventCoords(e);
    dragAngle = computeAngleFromMouse(coords.x, coords.y, L);
    currentAngle = dragAngle;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawPendulum(currentAngle, L);

    // Update numeric readouts during drag
    timeReadout.textContent = "0.00";
    angleReadout.textContent = (currentAngle * (180 / Math.PI)).toFixed(1);
    speedReadout.textContent = "0.00";

    // Reset energy bars (PE only)
    const h = L * (1 - Math.cos(currentAngle));
    const pe = g * h;
    const total = pe;
    peBar.style.width = total ? `${((pe / total) * 100).toFixed(1)}%` : "0%";
    keBar.style.width = "0%";

    e.preventDefault(); // Prevent scrolling on touch
  }

  // Helper function to end dragging
  function endDrag() {
    if (!isDragging) return;
    isDragging = false;
    theta0 = dragAngle;
    angleChart.options.scales.y.min = -theta0;
    angleChart.options.scales.y.max = theta0;
    angleChart.update("none");

    startTime = null;
    animationId = requestAnimationFrame(animatePendulum);
  }

  // Mouse events
  canvas.addEventListener("mousedown", startDrag);
  canvas.addEventListener("mousemove", handleDrag);
  canvas.addEventListener("mouseup", endDrag);
  canvas.addEventListener("mouseleave", endDrag);

  // Touch events for mobile
  canvas.addEventListener("touchstart", startDrag);
  canvas.addEventListener("touchmove", handleDrag);
  canvas.addEventListener("touchend", endDrag);
  canvas.addEventListener("touchcancel", endDrag);

  // Prevent default drag behavior
  canvas.addEventListener("dragstart", (e) => {
    e.preventDefault();
  });

  // -------- End Drag & Release Logic -------- //
});
