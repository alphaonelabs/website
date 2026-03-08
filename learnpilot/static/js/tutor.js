/**
 * LearnPilot – Tutor session JavaScript
 *
 * Handles:
 *  - Real-time AI tutoring chat
 *  - AI practice question generation
 *  - Answer evaluation with feedback
 */

(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Utilities                                                            */
  /* ------------------------------------------------------------------ */

  function scrollToBottom() {
    const el = document.getElementById("chat-messages");
    if (el) el.scrollTop = el.scrollHeight;
  }

  function setTyping(visible) {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) {
      indicator.classList.toggle("hidden", !visible);
      scrollToBottom();
    }
  }

  function appendMessage(role, content) {
    const container = document.getElementById("chat-messages");
    if (!container) return;

    const wrapper = document.createElement("div");
    wrapper.className = `flex ${role === "user" ? "justify-end" : "justify-start"}`;

    const bubble = document.createElement("div");
    bubble.className = [
      "max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed",
      role === "user"
        ? "bg-indigo-600 text-white rounded-br-sm"
        : "bg-gray-100 text-gray-800 rounded-bl-sm",
    ].join(" ");

    if (role === "assistant") {
      const label = document.createElement("div");
      label.className = "text-xs font-semibold text-indigo-500 mb-1";
      label.textContent = "🤖 AI Tutor";
      bubble.appendChild(label);
    }

    // Render newlines as <br>
    const text = document.createElement("span");
    text.innerHTML = content.replace(/\n/g, "<br>");
    bubble.appendChild(text);
    wrapper.appendChild(bubble);

    // Insert before typing indicator
    const typingIndicator = document.getElementById("typing-indicator");
    container.insertBefore(wrapper, typingIndicator);
    scrollToBottom();
  }

  /* ------------------------------------------------------------------ */
  /* Chat                                                                 */
  /* ------------------------------------------------------------------ */

  async function sendChatMessage(message) {
    const input = document.getElementById("chat-input");
    const form = document.getElementById("chat-form");
    if (!input || !form) return;

    // Disable input while waiting
    input.disabled = true;
    form.querySelector("button[type=submit]").disabled = true;

    appendMessage("user", message);
    setTyping(true);

    try {
      const response = await fetch(CHAT_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": CSRF_TOKEN,
        },
        body: JSON.stringify({ message }),
      });

      const data = await response.json();

      if (!response.ok) {
        appendMessage("assistant", `⚠️ Error: ${data.error || "Something went wrong."}`);
      } else {
        appendMessage("assistant", data.response);
      }
    } catch (err) {
      appendMessage("assistant", "⚠️ Network error. Please check your connection and try again.");
    } finally {
      setTyping(false);
      input.disabled = false;
      form.querySelector("button[type=submit]").disabled = false;
      input.focus();
    }
  }

  function initChat() {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    if (!form || !input) return;

    scrollToBottom();

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const message = input.value.trim();
      if (!message) return;
      input.value = "";
      sendChatMessage(message);
    });
  }

  /* ------------------------------------------------------------------ */
  /* Practice questions                                                   */
  /* ------------------------------------------------------------------ */

  async function loadPracticeQuestion() {
    const btn = document.getElementById("get-question-btn");
    const area = document.getElementById("practice-area");
    const questionText = document.getElementById("question-text");
    const feedbackArea = document.getElementById("feedback-area");
    const answerInput = document.getElementById("answer-input");

    if (!btn || !area || !questionText) return;

    btn.disabled = true;
    btn.textContent = "Generating…";

    try {
      const response = await fetch(PRACTICE_API_URL);
      const data = await response.json();

      if (response.ok && data.question) {
        questionText.textContent = data.question;
        answerInput.value = "";
        feedbackArea.classList.add("hidden");
        feedbackArea.textContent = "";
        area.classList.remove("hidden");
        btn.textContent = "New Question";
      } else {
        btn.textContent = "Try Again";
      }
    } catch {
      btn.textContent = "Try Again";
    } finally {
      btn.disabled = false;
    }
  }

  async function evaluateAnswer() {
    const submitBtn = document.getElementById("submit-answer-btn");
    const answerInput = document.getElementById("answer-input");
    const questionText = document.getElementById("question-text");
    const feedbackArea = document.getElementById("feedback-area");

    if (!submitBtn || !answerInput || !questionText || !feedbackArea) return;

    const answer = answerInput.value.trim();
    if (!answer) {
      answerInput.focus();
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Evaluating…";

    try {
      const response = await fetch(EVALUATE_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": CSRF_TOKEN,
        },
        body: JSON.stringify({
          question: questionText.textContent,
          answer,
          lesson_id: LESSON_ID,
        }),
      });
      const data = await response.json();

      feedbackArea.classList.remove("hidden", "bg-green-50", "bg-red-50", "border-green-200", "border-red-200");

      const score = parseFloat(data.score) || 0;
      if (score >= 0.7) {
        feedbackArea.className =
          "mt-3 p-4 rounded-xl text-sm bg-green-50 border border-green-200 text-green-800";
      } else {
        feedbackArea.className =
          "mt-3 p-4 rounded-xl text-sm bg-red-50 border border-red-200 text-red-800";
      }

      let html = `<strong>Score: ${Math.round(score * 100)}%</strong><br>`;
      html += `${data.feedback || ""}`;
      if (data.correct_answer) {
        html += `<br><em class="text-gray-600">Reference: ${data.correct_answer}</em>`;
      }
      feedbackArea.innerHTML = html;
    } catch {
      feedbackArea.className = "mt-3 p-4 rounded-xl text-sm bg-gray-50 text-gray-600";
      feedbackArea.textContent = "Could not evaluate answer. Please try again.";
      feedbackArea.classList.remove("hidden");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Answer";
    }
  }

  function initPractice() {
    const btn = document.getElementById("get-question-btn");
    const submitBtn = document.getElementById("submit-answer-btn");
    if (btn) btn.addEventListener("click", loadPracticeQuestion);
    if (submitBtn) submitBtn.addEventListener("click", evaluateAnswer);
  }

  /* ------------------------------------------------------------------ */
  /* Bootstrap                                                            */
  /* ------------------------------------------------------------------ */

  document.addEventListener("DOMContentLoaded", () => {
    initChat();
    initPractice();
  });
})();
