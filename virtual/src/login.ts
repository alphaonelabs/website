import { isAuthenticated, storeAuth, type AuthUser } from "./auth";
import { LEARN_API_BASE } from "./config";

interface AuthResponse {
  token: string;
  user: AuthUser;
}

interface ApiEnvelope<T> {
  error?: string;
  message?: string;
  data?: T;
}

function el<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Missing #${id} element in login.html`);
  return found as T;
}

const tabLogin = el<HTMLButtonElement>("tab-login");
const tabRegister = el<HTMLButtonElement>("tab-register");
const panelLogin = el<HTMLDivElement>("panel-login");
const panelRegister = el<HTMLDivElement>("panel-register");

function switchTab(tab: "login" | "register"): void {
  const isLogin = tab === "login";
  panelLogin.classList.toggle("hidden", !isLogin);
  panelRegister.classList.toggle("hidden", isLogin);
  tabLogin.classList.toggle("active", isLogin);
  tabRegister.classList.toggle("active", !isLogin);
}

tabLogin.addEventListener("click", () => switchTab("login"));
tabRegister.addEventListener("click", () => switchTab("register"));

/** Only same-origin, path-only redirects are honored to prevent open-redirect abuse. */
function safeNextPath(raw: string | null): string {
  if (raw && /^\/(?!\/)/.test(raw)) return raw;
  return "/";
}

function handlePostLoginRedirect(): void {
  const next = safeNextPath(params.get("next"));
  window.location.href = next;
}

function showToast(msg: string): void {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

function showErr(boxId: string, msgId: string, msg: string): void {
  const box = el<HTMLDivElement>(boxId);
  el<HTMLSpanElement>(msgId).textContent = msg;
  box.classList.add("show");
  setTimeout(() => box.classList.remove("show"), 5000);
}

const REQUEST_TIMEOUT_MS = 15000;

async function callApi<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(`${LEARN_API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const data = (await res.json()) as ApiEnvelope<T>;
    if (!res.ok) {
      throw new Error(data.error || data.message || "Request failed");
    }
    return (data.data ?? (data as unknown as T));
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

const params = new URLSearchParams(location.search);
if (isAuthenticated()) {
  handlePostLoginRedirect();
}
if (params.get("tab") === "register") {
  switchTab("register");
}

el<HTMLFormElement>("form-login").addEventListener("submit", async (event) => {
  event.preventDefault();
  el<HTMLDivElement>("login-err").classList.remove("show");

  const btn = (event.target as HTMLFormElement).querySelector<HTMLButtonElement>("button[type=submit]")!;
  const originalText = btn.textContent;
  btn.textContent = "Signing in...";
  btn.disabled = true;

  try {
    const username = el<HTMLInputElement>("l-username").value.trim();
    const password = el<HTMLInputElement>("l-password").value;

    if (!username || !password) {
      throw new Error("Please enter both username and password");
    }

    const auth = await callApi<AuthResponse>("/api/login", { username, password });
    storeAuth(auth.token, auth.user);
    showToast("Redirecting...");
    setTimeout(handlePostLoginRedirect, 500);
  } catch (err) {
    showErr("login-err", "login-err-msg", (err as Error).message);
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

el<HTMLFormElement>("form-register").addEventListener("submit", async (event) => {
  event.preventDefault();
  el<HTMLDivElement>("register-err").classList.remove("show");

  const btn = (event.target as HTMLFormElement).querySelector<HTMLButtonElement>("button[type=submit]")!;
  const originalText = btn.textContent;
  btn.textContent = "Creating...";
  btn.disabled = true;

  try {
    const name = el<HTMLInputElement>("r-name").value.trim();
    const username = el<HTMLInputElement>("r-username").value.trim();
    const email = el<HTMLInputElement>("r-email").value.trim();
    const password = el<HTMLInputElement>("r-password").value;
    const confirmPassword = el<HTMLInputElement>("r-confirm-password").value;
    const referralCode = el<HTMLInputElement>("r-referral-code").value.trim();

    if (!username || !email || !password) {
      throw new Error("Please fill in all required fields");
    }
    if (password.length < 6) {
      throw new Error("Password must be at least 6 characters");
    }
    if (password !== confirmPassword) {
      throw new Error("Passwords do not match");
    }

    const result = await callApi<{ message?: string }>("/api/register", {
      name,
      username,
      email,
      password,
      referral_code: referralCode,
    });

    showRegisterSuccess(result.message || "Registration successful! Please check your email to verify your account.");
  } catch (err) {
    showErr("register-err", "register-err-msg", (err as Error).message);
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

function showRegisterSuccess(msg: string): void {
  const panel = panelRegister;

  const container = document.createElement("div");
  container.className = "success";

  const iconDiv = document.createElement("div");
  iconDiv.className = "icon";
  iconDiv.textContent = "✉️";

  const heading = document.createElement("h2");
  heading.textContent = "Check your email";
  heading.tabIndex = -1;

  const msgPara = document.createElement("p");
  msgPara.textContent = msg;

  const actionButton = document.createElement("button");
  actionButton.type = "button";
  actionButton.textContent = "Once verified, sign in here";
  actionButton.addEventListener("click", () => switchTab("login"));

  container.append(iconDiv, heading, msgPara, actionButton);

  panel.replaceChildren(container);
  heading.focus();
}
