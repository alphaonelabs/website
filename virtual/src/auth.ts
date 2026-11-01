export interface AuthUser {
  id: number | string;
  username: string;
  name?: string;
  email?: string;
  [key: string]: unknown;
}

const TOKEN_KEY = "edu_token";
const USER_KEY = "edu_user";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

export function storeAuth(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  window.location.href = "/login.html";
}

/**
 * Redirects to the login page if there is no stored session, preserving the
 * current path so login can send the user back. Returns whether the caller
 * is authenticated — callers should bail out immediately when false, since
 * navigation doesn't halt script execution.
 */
export function requireAuth(): boolean {
  if (isAuthenticated()) return true;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `/login.html?next=${next}`;
  return false;
}
