// static/virtual_lab/js/code_editor.js

// Simple CSRF helper
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

// Bootstrap Ace
const editor = ace.edit("editor");
editor.setTheme("ace/theme/github");
editor.session.setMode("ace/mode/python");
editor.setOptions({ fontSize: "14px", showPrintMargin: false });

const runBtn   = document.getElementById("run-btn");
const outputEl = document.getElementById("output");
const stdinEl  = document.getElementById("stdin-input");
const langSel  = document.getElementById("language-select");

runBtn.addEventListener("click", () => {
  const code     = editor.getValue();
  const stdin    = stdinEl.value;
  const language = langSel.value;

  if (!code.trim()) {
    outputEl.textContent = "🛑 Please type some code first.";
    return;
  }
  outputEl.textContent = "Running…";
  runBtn.disabled = true;

  fetch(window.EVALUATE_CODE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken":  getCookie("csrftoken")
    },
    body: JSON.stringify({ code, language, stdin })
  })
  .then(res => res.json())
  .then(data => {
    let out = "";
    if (data.stderr) out += `ERROR:\n${data.stderr}\n`;
    if (data.stdout) out += data.stdout;
    outputEl.textContent = out || "[no output]";
  })
  .catch(err => {
    outputEl.textContent = `Request failed: ${err.message}`;
  })
  .finally(() => {
    runBtn.disabled = false;
  });
});
