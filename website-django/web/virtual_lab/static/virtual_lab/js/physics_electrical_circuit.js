// web/virtual_lab/static/virtual_lab/js/physics_electrical_circuit.js

document.addEventListener("DOMContentLoaded", () => {
  // ==== 1. Tutorial Overlay Logic ====
  const tutorialOverlay = document.getElementById("tutorial-overlay");
  const stepNumberElem   = document.getElementById("step-number");
  const stepList         = document.getElementById("step-list");
  const prevBtn          = document.getElementById("tutorial-prev");
  const nextBtn          = document.getElementById("tutorial-next");
  const skipBtn          = document.getElementById("tutorial-skip");

  const steps = [
    ["Use the sliders to set battery voltage \(V_0\), resistor \(R\), and capacitor \(C\)."],
    ["Click “Start” to begin charging the capacitor through \(R\). Watch \(V_C(t)\) rise."],
    ["Observe how \(I(t)\) decreases as the capacitor charges."],
    ["After \(5\ tau\), answer the quiz questions."]
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
  const canvas         = document.getElementById("circuit-canvas");
  const ctx            = canvas.getContext("2d");

  const VSlider        = document.getElementById("V-slider");
  const VValue         = document.getElementById("V-value");
  const RSlider        = document.getElementById("R-slider");
  const RValue         = document.getElementById("R-value");
  const CSlider        = document.getElementById("C-slider");
  const CValue         = document.getElementById("C-value");

  const startBtn       = document.getElementById("start-circuit");
  const stopBtn        = document.getElementById("stop-circuit");
  const resetBtn       = document.getElementById("reset-circuit");

  const quizDiv        = document.getElementById("postlab-quiz");

  const readoutT       = document.getElementById("readout-t");
  const readoutVc      = document.getElementById("readout-vc");
  const readoutI       = document.getElementById("readout-i");
  const readoutTau     = document.getElementById("readout-tau");

  const vcCtx          = document.getElementById("vc-chart").getContext("2d");
  const iCtx           = document.getElementById("i-chart").getContext("2d");

  // Physical parameters (will update on slider changes)
  let V0 = parseFloat(VSlider.value);      // battery voltage in volts
  let R  = parseFloat(RSlider.value);      // resistance in ohms
  let C  = parseFloat(CSlider.value) * 1e-6; // convert µF → F

  let tau = R * C;                         // time constant (s)

  // Simulation state
  let t0       = null;
  let animId   = null;
  let running  = false;
  let maxTime  = 5 * tau;  // simulate up to 5τ for quiz reveal

  // Chart.js setups
  const vcData = {
    labels: [],
    datasets: [{
      label: "Vc(t) (V)",
      data: [],
      borderColor: "#1E40AF",
      borderWidth: 2,
      fill: false,
      pointRadius: 0
    }]
  };
  const vcChart = new Chart(vcCtx, {
    type: "line",
    data: vcData,
    options: {
      animation: false,
      scales: {
        x: { title: { display: true, text: "Time (s)" } },
        y: { title: { display: true, text: "Vc (V)" }, suggestedMax: V0 }
      },
      plugins: { legend: { display: false } }
    }
  });

  const iData = {
    labels: [],
    datasets: [{
      label: "I(t) (A)",
      data: [],
      borderColor: "#DC2626",
      borderWidth: 2,
      fill: false,
      pointRadius: 0
    }]
  };
  const iChart = new Chart(iCtx, {
    type: "line",
    data: iData,
    options: {
      animation: false,
      scales: {
        x: { title: { display: true, text: "Time (s)" } },
        y: { title: { display: true, text: "I (A)" } }
      },
      plugins: { legend: { display: false } }
    }
  });

  // Disable controls until tutorial ends
  startBtn.disabled = true;
  stopBtn.disabled  = true;
  resetBtn.disabled = true;
  VSlider.disabled  = true;
  RSlider.disabled  = true;
  CSlider.disabled  = true;

  // ==== 3. Enable Controls & Initial Draw ====
  function enableControls() {
    startBtn.disabled = false;
    resetBtn.disabled = false;
    VSlider.disabled  = false;
    RSlider.disabled  = false;
    CSlider.disabled  = false;
    tau = R * C;
    readoutTau.textContent = tau.toFixed(3);
    drawCircuit(0); // initial draw at t=0
  }

  // Draw the schematic of battery→resistor→capacitor and a current arrow
  function drawCircuit(t) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Coordinates for schematic
    const leftX = 50;
    const midX  = 250;
    const rightX = 450;
    const centerY = canvas.height / 2;

    // 1) Draw battery as two plates
    ctx.fillStyle = "#333";
    ctx.fillRect(leftX - 10, centerY - 40, 10, 80); // negative plate
    ctx.fillRect(leftX + 10, centerY - 20, 5, 40);  // positive plate
    ctx.fillStyle = "#000";
    ctx.font = "14px sans-serif";
    ctx.fillText("Battery", leftX - 20, centerY - 50);
    ctx.fillText(`V₀ = ${V0.toFixed(1)}V`, leftX - 30, centerY + 60);

    // 2) Draw resistor as zig-zag between leftX+20 and midX
    drawResistor(leftX + 20, centerY, midX, centerY);
    ctx.fillStyle = "#000";
    ctx.fillText(`R = ${R.toFixed(0)}Ω`, (leftX + 20 + midX) / 2 - 20, centerY - 20);

    // 3) Draw capacitor between midX+20 and midX+20 horizontally (two parallel plates)
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(midX + 20, centerY - 30);
    ctx.lineTo(midX + 20, centerY + 30);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(midX + 45, centerY - 30);
    ctx.lineTo(midX + 45, centerY + 30);
    ctx.stroke();
    ctx.fillStyle = "#000";
    ctx.fillText(`C = ${(C * 1e6).toFixed(0)}µF`, midX + 5, centerY + 60);

    // 4) Draw wires connecting ends
    ctx.strokeStyle = "#555";
    ctx.lineWidth = 2;
    ctx.beginPath();
    // Top wire: battery positive → resistor start
    ctx.moveTo(leftX + 10, centerY - 20);
    ctx.lineTo(leftX + 20, centerY - 20);
    // Continue through resistor zigzag (already drawn), then to capacitor start
    ctx.lineTo(midX, centerY - 20);
    ctx.lineTo(midX + 20, centerY - 20);
    // From capacitor top plate back to battery negative via right wire
    ctx.lineTo(midX + 45, centerY - 20);
    ctx.lineTo(rightX, centerY - 20);
    ctx.lineTo(rightX, centerY + 60);
    // Bottom wire: capacitor bottom plate back to battery negative
    ctx.lineTo(midX + 45, centerY + 60);
    ctx.lineTo(midX + 20, centerY + 60);
    ctx.lineTo(midX, centerY + 60);
    ctx.lineTo(leftX + 20, centerY + 60);
    ctx.lineTo(leftX + 10, centerY + 60);
    ctx.stroke();

    // 5) Compute Vc(t) and I(t)
    const VC = V0 * (1 - Math.exp(-t / tau));
    const I  = (V0 - VC) / R;

    // 6) Draw current arrow on top wire (direction: left→right). Length proportional to I.
    const arrowLength = Math.min(I * 1000, 100); // scale for visibility
    if (running) {
      ctx.strokeStyle = "#DC2626";
      ctx.fillStyle = "#DC2626";
      ctx.lineWidth = 2;
      // arrow shaft
      ctx.beginPath();
      ctx.moveTo(leftX + 20, centerY - 20);
      ctx.lineTo(leftX + 20 + arrowLength, centerY - 20);
      ctx.stroke();
      // arrowhead
      const tipX = leftX + 20 + arrowLength;
      const tipY = centerY - 20;
      ctx.beginPath();
      ctx.moveTo(tipX, tipY);
      ctx.lineTo(tipX - 8, tipY - 5);
      ctx.lineTo(tipX - 8, tipY + 5);
      ctx.closePath();
      ctx.fill();
    }

    // 7) Update numeric readouts
    readoutT.textContent = t.toFixed(2);
    readoutVc.textContent = VC.toFixed(2);
    readoutI.textContent = I.toFixed(3);
    readoutTau.textContent = tau.toFixed(3);
  }

  // Draw a zig-zag resistor between (x1,y) and (x2,y)
  function drawResistor(x1, y, x2, y2) {
    const totalLength = x2 - x1;
    const peaks = 6;
    const segment = totalLength / (peaks * 2);
    ctx.strokeStyle = "#555";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(x1, y);
    for (let i = 0; i < peaks * 2; i++) {
      const dx = x1 + segment * (i + 1);
      const dy = y + (i % 2 === 0 ? -10 : 10);
      ctx.lineTo(dx, dy);
    }
    ctx.lineTo(x2, y);
    ctx.stroke();
  }

  // ==== 4. Slider Handlers ====
  VSlider.addEventListener("input", () => {
    V0 = parseFloat(VSlider.value);
    VValue.textContent = V0.toFixed(1);
    // Update chart Y‐axis max
    vcChart.options.scales.y.suggestedMax = V0;
    vcChart.update("none");
    if (!running) {
      drawCircuit(0);
    }
  });

  RSlider.addEventListener("input", () => {
    R = parseFloat(RSlider.value);
    RValue.textContent = R.toFixed(0);
    tau = R * C;
    readoutTau.textContent = tau.toFixed(3);
    if (!running) {
      drawCircuit(0);
    }
  });

  CSlider.addEventListener("input", () => {
    C = parseFloat(CSlider.value) * 1e-6;
    CValue.textContent = (C * 1e6).toFixed(0);
    tau = R * C;
    readoutTau.textContent = tau.toFixed(3);
    if (!running) {
      drawCircuit(0);
    }
  });

  // ==== 5. Animation Loop & Launch ====
  function step(timestamp) {
    if (!t0) t0 = timestamp;
    const elapsed = (timestamp - t0) / 1000; // seconds
    if (elapsed >= maxTime) {
      drawCircuit(maxTime);
      revealQuiz();
      return;
    }
    drawCircuit(elapsed);

    // Update graphs
    //  Vc(t)
    const VC = V0 * (1 - Math.exp(-elapsed / tau));
    vcChart.data.labels.push(elapsed.toFixed(2));
    vcChart.data.datasets[0].data.push(VC.toFixed(2));
    vcChart.update("none");

    //  I(t)
    const I = (V0 - VC) / R;
    iChart.data.labels.push(elapsed.toFixed(2));
    iChart.data.datasets[0].data.push(I.toFixed(3));
    iChart.update("none");

    animId = requestAnimationFrame(step);
  }

  startBtn.addEventListener("click", () => {
    // Disable controls
    VSlider.disabled = true;
    RSlider.disabled = true;
    CSlider.disabled = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    resetBtn.disabled = true;

    tau = R * C;
    maxTime = 5 * tau;
    t0 = null;

    // Clear graphs
    vcChart.data.labels = [];
    vcChart.data.datasets[0].data = [];
    vcChart.update("none");
    iChart.data.labels = [];
    iChart.data.datasets[0].data = [];
    iChart.update("none");

    running = true;
    animId = requestAnimationFrame(step);
  });

  stopBtn.addEventListener("click", () => {
    if (animId) cancelAnimationFrame(animId);
    running = false;
    stopBtn.disabled = true;
    startBtn.disabled = false;
    resetBtn.disabled = false;
  });

  resetBtn.addEventListener("click", () => {
    if (animId) cancelAnimationFrame(animId);
    running = false;
    t0 = null;
    // Re-enable controls
    VSlider.disabled = false;
    RSlider.disabled = false;
    CSlider.disabled = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    resetBtn.disabled = false;
    quizDiv.classList.add("hidden");

    // Clear graphs
    vcChart.data.labels = [];
    vcChart.data.datasets[0].data = [];
    vcChart.update("none");
    iChart.data.labels = [];
    iChart.data.datasets[0].data = [];
    iChart.update("none");

    drawCircuit(0);
  });

  // ==== 6. Quiz Reveal ====
  function revealQuiz() {
    stopBtn.disabled = true;
    resetBtn.disabled = false;
    quizDiv.classList.remove("hidden");
  }

  // ==== 7. Initial Draw ====
  tau = R * C;
  readoutTau.textContent = tau.toFixed(3);
  drawCircuit(0);
});
