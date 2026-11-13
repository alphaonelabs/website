/**
 * RobotAPI — mock robot command interface that logs output to #command-log.
 * Plain JS, no ES modules, no build step required.
 */
const RobotAPI = (() => {
  let state = { x: 0, y: 0, heading: 0 };

  function log(msg) {
    const logEl = document.getElementById('command-log');
    if (!logEl) return;
    // Remove placeholder on first real log
    const placeholder = logEl.querySelector('.log-placeholder');
    if (placeholder) placeholder.remove();
    const line = document.createElement('div');
    line.className = 'log-line';
    line.textContent = msg;
    logEl.appendChild(line);
    logEl.scrollTop = logEl.scrollHeight;
  }

  return {
    moveForward(steps = 10) {
      state.y += steps;
      log('\u{1F916} Move forward ' + steps + ' steps  [pos: ' + state.x + ', ' + state.y + ']');
    },
    moveBackward(steps = 10) {
      state.y -= steps;
      log('\u{1F916} Move backward ' + steps + ' steps  [pos: ' + state.x + ', ' + state.y + ']');
    },
    turnLeft(deg = 90) {
      state.heading = (state.heading - deg + 360) % 360;
      log('\u{21BA} Turn left ' + deg + '\u00B0  [heading: ' + state.heading + '\u00B0]');
    },
    turnRight(deg = 90) {
      state.heading = (state.heading + deg) % 360;
      log('\u{21BB} Turn right ' + deg + '\u00B0  [heading: ' + state.heading + '\u00B0]');
    },
    wait(ms = 500) {
      log('\u{23F1} Wait ' + ms + 'ms...');
      return new Promise(resolve => setTimeout(resolve, ms));
    },
    scan() {
      const dist = (Math.random() * 9 + 0.5).toFixed(2);
      log('\u{1F4E1} Scan: ' + dist + 'm detected');
      return parseFloat(dist);
    },
    reset() {
      state = { x: 0, y: 0, heading: 0 };
      const logEl = document.getElementById('command-log');
      if (logEl) {
        logEl.innerHTML = '<div class="log-placeholder" style="color: var(--a1-text-muted, #666); font-style: italic;">// Command output will appear here...</div>';
      }
      log('\u{1F504} Robot reset. Position: (0, 0), Heading: 0\u00B0');
    }
  };
})();
