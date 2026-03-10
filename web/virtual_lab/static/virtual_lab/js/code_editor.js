// static/virtual_lab/js/code_editor.js

// Simple CSRF helper
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

// Language configuration for Ace editor
const languageConfig = {
  python: {
    mode: "ace/mode/python",
    sample: 'print("Hello, World!")'
  },
  javascript: {
    mode: "ace/mode/javascript",
    sample: 'console.log("Hello, World!");'
  },
  c: {
    mode: "ace/mode/c_cpp",
    sample: '#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}'
  },
  cpp: {
    mode: "ace/mode/c_cpp",
    sample: '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}'
  }
};

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {

// Bootstrap Ace
const editor = ace.edit("editor");
editor.setTheme("ace/theme/github");
editor.setOptions({
  fontSize: "14px",
  showPrintMargin: false,
  wrap: true
});

const runBtn   = document.getElementById("run-btn");
const outputEl = document.getElementById("output");
const stdinEl  = document.getElementById("stdin-input");
const langSel  = document.getElementById("language-select");

// Track the currently active language
let currentLanguage = "python";

// Helper to detect if the editor contains unsaved (non-sample) code
function hasUnsavedChanges() {
  const currentCode = editor.getValue();
  const normalizedCurrent = currentCode.trimEnd();

  // Empty editor is treated as having no unsaved changes
  if (!normalizedCurrent) {
    return false;
  }

  // If the current code matches any sample (ignoring trailing whitespace), we treat it as not modified
  const matchesAnySample = Object.values(languageConfig).some((config) => {
    return config.sample.trimEnd() === normalizedCurrent;
  });

  return !matchesAnySample;
}

// Function to update editor mode and sample code based on selected language
function updateEditorLanguage(language) {
  const config = languageConfig[language];
  if (config) {
    // Only overwrite the editor contents if there are no unsaved changes,
    // or if the user explicitly confirms discarding their current code.
    if (hasUnsavedChanges()) {
      const confirmDiscard = window.confirm(
        "You have code in the editor that differs from the default samples. " +
        "Switching languages will replace it with example code for the selected language. " +
        "Do you want to discard your current code?"
      );

      if (!confirmDiscard) {
        // Revert the dropdown to the previously active language
        langSel.value = currentLanguage;
        return;
      }
    }

    currentLanguage = language;
    editor.session.setMode(config.mode);
    editor.setValue(config.sample, -1); // -1 moves cursor to start
  }
}

// Language selector change handler
langSel.addEventListener("change", (e) => {
  const selectedLanguage = e.target.value;
  updateEditorLanguage(selectedLanguage);
});

// Initialize with Python sample code
updateEditorLanguage("python");

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

}); // End DOMContentLoaded
