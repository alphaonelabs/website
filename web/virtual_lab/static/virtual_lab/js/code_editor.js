// static/virtual_lab/js/code_editor.js

// Simple CSRF helper
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

// Language boilerplate templates:
const BOILERPLATES = {
  python: `print("Hello, World!")`,

  javascript: `console.log("Hello, World!");`,

  c: `#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}`,

  cpp: `#include <iostream>
using namespace std;

int main() {
    cout << "Hello, World!\\n";
    return 0;
}`
};

// Bootstrap Ace
const editor = ace.edit("editor");
editor.setTheme("ace/theme/github");
editor.session.setMode("ace/mode/python");
editor.setOptions({ fontSize: "14px", showPrintMargin: false });

const runBtn   = document.getElementById("run-btn");
const outputEl = document.getElementById("output");
const stdinEl  = document.getElementById("stdin-input");
const langSel  = document.getElementById("language-select");

function updateEditorMode(language) {
  let mode;
  switch(language) {
    case 'python':
      mode = 'ace/mode/python';
      break;
    case 'javascript':
      mode = 'ace/mode/javascript';
      break;
    case 'c':
    case 'cpp':
      mode = 'ace/mode/c_cpp';
      break;
    default:
      mode = 'ace/mode/text';
  }
  editor.session.setMode(mode);
}

function setBoilerplate(language) {
  editor.setValue(BOILERPLATES[language] || '', -1);
  editor.clearSelection();
  editor.focus();
}

// Language change handler
langSel.addEventListener("change", (e) => {
  const language = e.target.value;

  // Asking user if they want to replace current code with boilerplate:
  if (editor.getValue().trim() &&
    !confirm(`Switch to ${language}? This will replace your current code with a '${language}' boilerplate template.`)) {
    e.target.value = e.target.dataset.lastValue || 'python';
    return;
  }

  updateEditorMode(language);

  setBoilerplate(language);

  e.target.dataset.lastValue = language;
});

window.addEventListener('load', () => {
  setBoilerplate('python');
  langSel.dataset.lastValue = 'python';
});

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
