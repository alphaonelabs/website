// web/virtual_lab/static/virtual_lab/js/physics_projectile.js

document.addEventListener("DOMContentLoaded", () => {
  // -------- 1. Tutorial Overlay Logic (animated bullet points) -------- //
  const tutorialOverlay = document.getElementById("tutorial-overlay");
  const stepNumberElem = document.getElementById("step-number");
  const stepList = document.getElementById("step-list");
  const prevBtn = document.getElementById("tutorial-prev");
  const nextBtn = document.getElementById("tutorial-next");
  const skipBtn = document.getElementById("tutorial-skip");

  const steps = [
    ["Click-and-drag FROM the launch pad (white circle at bottom-left) to set initial speed and angle."],
    [
      "Drag length sets speed (longer drag → higher speed), direction sets angle.",
      "Release to start the simulation."
    ],
    [
      "Adjust gravity and wind sliders BEFORE dragging; they affect the predicted trajectory.",
      "After release, the full path animates."
    ],
    [
      "During flight, small x/y axes are drawn on the ball, showing velocity components.",
      "Watch the “y vs x” plot updating in real time."
    ],
    ["Click “Begin Experiment” when ready, then drag from the launch pad!"]
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
      tutorialOverlay.style.display = "none";
      enableControls();
    }
  });
  skipBtn.addEventListener("click", () => {
    tutorialOverlay.style.display = "none";
    enableControls();
  });
  // -------- End Tutorial Logic -------- //


  // -------- 2. DOM References & State -------- //
  const canvas = document.getElementById("projectile-canvas");
  const ctx = canvas.getContext("2d");

  const trajectoryCanvas = document.getElementById("trajectory-chart").getContext("2d");

  const gravitySlider = document.getElementById("gravity-slider");
  const gravityValue = document.getElementById("gravity-value");
  const windSlider = document.getElementById("wind-slider");
  const windValue = document.getElementById("wind-value");
  const resetButton = document.getElementById("reset-button");

  const timeReadout = document.getElementById("time-readout");
  const xReadout = document.getElementById("x-readout");
  const yReadout = document.getElementById("y-readout");
  const vxReadout = document.getElementById("vx-readout");
  const vyReadout = document.getElementById("vy-readout");

  let g = Number.parseFloat(gravitySlider.value);
  let windAccel = Number.parseFloat(windSlider.value);

  let originY = canvas.height - 10;
  let pixelsPerMeter = 10;

  let v0 = 0, thetaRad = 0, vx = 0, vy0 = 0;
  let maxRange = 0, maxHeight = 0;

  // Stores trajectory points and velocities
  let trajectoryPoints = []; // { x_m, y_m, vx_t, vy_t }
  let currentFrame = 0;
  let animationId = null;

  const trajData = {
    labels: [],
    datasets: [{
      label: "y vs x (m)",
      data: [],
      borderColor: "#3182CE",
      borderWidth: 2,
      fill: false,
      pointRadius: 0
    }]
  };
  const trajChart = new Chart(trajectoryCanvas, {
    type: "line",
    data: trajData,
    options: {
      animation: false,
      scales: {
        x: { title: { display: true, text: "x (m)" } },
        y: { title: { display: true, text: "y (m)" } }
      },
      plugins: { legend: { display: false } }
    }
  });

  gravitySlider.disabled = true;
  windSlider.disabled = true;
  resetButton.disabled = true;


  // -------- 3. Enable Controls & Initial Drawing -------- //
  function enableControls() {
    gravitySlider.disabled = false;
    windSlider.disabled = false;
    resetButton.disabled = false;
    drawScene();
  }

  function drawAxes() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.moveTo(0, originY);
    ctx.lineTo(canvas.width, originY);
    ctx.strokeStyle = "#2D3748";
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  function drawLaunchPad() {
    const padX = 10, padY = originY, padR = 8;
    ctx.beginPath();
    ctx.arc(padX, padY, padR, 0, 2 * Math.PI);
    ctx.fillStyle = "#FFFFFF";
    ctx.fill();
    ctx.strokeStyle = "#4A5568";
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  function drawScene() {
    drawAxes();
    drawLaunchPad();
  }

  // -------- 4. Gravity & Wind Slider Handlers -------- //
  gravitySlider.addEventListener("input", () => {
    g = Number.parseFloat(gravitySlider.value);
    gravityValue.textContent = g.toFixed(2);
  });
  windSlider.addEventListener("input", () => {
    windAccel = Number.parseFloat(windSlider.value);
    windValue.textContent = windAccel.toFixed(2);
  });


  // -------- 5. Aim-by-Drag Logic -------- //
  let isAiming = false;
  let aimStartX = 0, aimStartY = 0;
  let aimCurrentX = 0, aimCurrentY = 0;

  canvas.addEventListener("mousedown", (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const padX = 10, padY = originY, padR = 8;
    const dist = Math.hypot(mouseX - padX, mouseY - padY);
    if (dist <= padR + 4) {
      isAiming = true;
      aimStartX = padX;
      aimStartY = padY;
      aimCurrentX = mouseX;
      aimCurrentY = mouseY;

      trajChart.data.labels = [];
      trajChart.data.datasets[0].data = [];
      trajChart.update("none");

      timeReadout.textContent = "0.00";
      xReadout.textContent = "0.00";
      yReadout.textContent = "0.00";
      vxReadout.textContent = "0.00";
      vyReadout.textContent = "0.00";

      drawScene();
    }
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!isAiming) return;
    const rect = canvas.getBoundingClientRect();
    aimCurrentX = e.clientX - rect.left;
    aimCurrentY = e.clientY - rect.top;

    drawScene();

    ctx.beginPath();
    ctx.moveTo(aimStartX, aimStartY);
    ctx.lineTo(aimCurrentX, aimCurrentY);
    ctx.strokeStyle = "#DD6B20";
    ctx.lineWidth = 3;
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.setLineDash([]);
  });

  canvas.addEventListener("mouseup", (e) => {
    if (!isAiming) return;
    isAiming = false;

    const dx_px = aimCurrentX - aimStartX;
    const dy_px = aimCurrentY - aimStartY;
    if (dx_px <= 0) {
      drawScene();
      return;
    }

    // Convert drag to meters using temporary scale: 1 px → 0.1 m
    const tmpScale = 0.1;
    const dx_m = dx_px * tmpScale;
    const dy_m = (originY - aimCurrentY) * tmpScale; // invert y-axis

    v0 = Math.hypot(dx_m, dy_m);
    thetaRad = Math.atan2(dy_m, dx_m);
    vx = v0 * Math.cos(thetaRad);
    vy0 = v0 * Math.sin(thetaRad);

    // Compute theoretical max range & height
    maxRange = (v0 * v0 * Math.sin(2 * thetaRad)) / g;
    maxHeight = (v0 * v0 * Math.sin(thetaRad) * Math.sin(thetaRad)) / (2 * g);

    // Recalculate pixelsPerMeter so full path fits
    const marginX = 60, marginY = 60;
    const availableWidth = canvas.width - marginX;
    const availableHeight = originY - marginY;
    const scaleX = availableWidth / (maxRange + 1);
    const scaleY = availableHeight / (maxHeight + 1);
    pixelsPerMeter = Math.min(scaleX, scaleY);

    // Build the discrete trajectory points
    buildTrajectoryPoints();

    // Clear and draw static full trajectory faintly
    drawScene();
    drawStaticTrajectory();

    // Start animation loop
    currentFrame = 0;
    if (animationId) cancelAnimationFrame(animationId);
    animationId = requestAnimationFrame(animateBall);
  });


  // -------- 6. Build Trajectory Points & Velocities -------- //
  function buildTrajectoryPoints() {
    trajectoryPoints = [];
    const timeOfFlight = (2 * vy0) / g;
    const steps = 200;
    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * timeOfFlight;
      const x_m = vx * t + 0.5 * windAccel * t * t;
      const y_m = vy0 * t - 0.5 * g * t * t;
      if (y_m < 0) {
        trajectoryPoints.push({ x_m, y_m: 0, vx_t: vx + windAccel * t, vy_t: 0 });
        break;
      }
      const vx_t = vx + windAccel * t;
      const vy_t = vy0 - g * t;
      trajectoryPoints.push({ x_m, y_m, vx_t, vy_t });
    }
  }

  // -------- 7. Draw Static Full Trajectory (faint) -------- //
  function drawStaticTrajectory() {
    ctx.beginPath();
    trajectoryPoints.forEach((pt, idx) => {
      const px = pt.x_m * pixelsPerMeter + 10;
      const py = originY - pt.y_m * pixelsPerMeter;
      if (idx === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.strokeStyle = "rgba(221, 107, 32, 0.3)"; // faint orange
    ctx.lineWidth = 2;
    ctx.setLineDash([]);
    ctx.stroke();
  }

  // -------- 8. Animation Loop: Move Ball & Draw Axes-On-Ball -------- //
  function animateBall() {
    if (currentFrame >= trajectoryPoints.length) return;

    // Clear and redraw background & static path
    drawScene();
    drawStaticTrajectory();

    const pt = trajectoryPoints[currentFrame];
    const canvasX = pt.x_m * pixelsPerMeter + 10;
    const canvasY = originY - pt.y_m * pixelsPerMeter;

    // Draw the ball
    ctx.beginPath();
    ctx.arc(canvasX, canvasY, 6, 0, 2 * Math.PI);
    ctx.fillStyle = "#E53E3E";
    ctx.fill();
    ctx.strokeStyle = "#9B2C2C";
    ctx.stroke();

    // Draw small x/y axes on the ball, and show velocity components
    drawAxesOnBall(canvasX, canvasY, pt.vx_t, pt.vy_t);

    // Update numeric readouts
    const t = (currentFrame / (trajectoryPoints.length - 1)) * ((2 * vy0) / g);
    timeReadout.textContent = t.toFixed(2);
    xReadout.textContent = pt.x_m.toFixed(2);
    yReadout.textContent = pt.y_m.toFixed(2);
    vxReadout.textContent = pt.vx_t.toFixed(2);
    vyReadout.textContent = pt.vy_t.toFixed(2);

    // Update live plot with just this point
    trajChart.data.labels.push(pt.x_m.toFixed(2));
    trajChart.data.datasets[0].data.push(pt.y_m.toFixed(2));
    trajChart.update("none");

    currentFrame++;
    animationId = requestAnimationFrame(animateBall);
  }

  function drawAxesOnBall(cx, cy, vx_t, vy_t) {
    // Draw a small cross (x and y axes) centered on the ball
    const axisLen = 12; // total length of each axis line
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 1;
    ctx.beginPath();
    // Horizontal axis line
    ctx.moveTo(cx - axisLen / 2, cy);
    ctx.lineTo(cx + axisLen / 2, cy);
    // Vertical axis line
    ctx.moveTo(cx, cy - axisLen / 2);
    ctx.lineTo(cx, cy + axisLen / 2);
    ctx.stroke();

    // Now plot velocity components as small dots on those axes:
    // Scale velocities so they fit within half-axis length
    const vScale = 0.2; // 1 m/s → 0.2 px
    let vx_px = vx_t * vScale;
    let vy_px = vy_t * vScale;
    // Clamp so dot stays on axis line
    vx_px = Math.max(Math.min(vx_px, axisLen / 2), -axisLen / 2);
    vy_px = Math.max(Math.min(vy_px, axisLen / 2), -axisLen / 2);

    // Draw x-velocity dot (blue) on horizontal axis
    ctx.beginPath();
    ctx.arc(cx + vx_px, cy, 2.5, 0, 2 * Math.PI);
    ctx.fillStyle = "#3182CE";
    ctx.fill();

    // Draw y-velocity dot (green) on vertical axis
    ctx.beginPath();
    ctx.arc(cx, cy - vy_px, 2.5, 0, 2 * Math.PI);
    ctx.fillStyle = "#38A169";
    ctx.fill();
  }

  // -------- 9. Reset Handler -------- //
  resetButton.addEventListener("click", () => {
    if (animationId) cancelAnimationFrame(animationId);
    trajectoryPoints = [];
    currentFrame = 0;
    trajChart.data.labels = [];
    trajChart.data.datasets[0].data = [];
    trajChart.update("none");

    drawScene();

    g = 9.81;
    windAccel = 0;
    gravitySlider.value = "9.81";
    windSlider.value = "0";
    gravityValue.textContent = "9.81";
    windValue.textContent = "0.00";

    timeReadout.textContent = "0.00";
    xReadout.textContent = "0.00";
    yReadout.textContent = "0.00";
    vxReadout.textContent = "0.00";
    vyReadout.textContent = "0.00";
  });


  // -------- 10. Initial Draw -------- //
  drawScene();
});
