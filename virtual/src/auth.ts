export interface AuthUser {
  id: number | string;
  username: string;
  name?: string;
  email?: string;
  [key: string]: unknown;
}

const TOKEN_KEY = "edu_token";
const USER_KEY = "edu_user";

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[1]) : null;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY) || getCookie('a1_token');
}

export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY) || getCookie('a1_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null && getUser() !== null;
}

export function storeAuth(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  try {
    const isAlphaOne = location.hostname === 'alphaonelabs.com' || location.hostname.endsWith('.alphaonelabs.com');
    const domain = isAlphaOne ? '; domain=.alphaonelabs.com' : '';
    const secure = location.protocol === 'https:' ? '; Secure' : '';
    const maxAge = 60 * 60 * 24 * 7;
    document.cookie = `a1_token=${encodeURIComponent(token)}; path=/; max-age=${maxAge}; SameSite=Lax${domain}${secure}`;
    document.cookie = `a1_user=${encodeURIComponent(JSON.stringify(user))}; path=/; max-age=${maxAge}; SameSite=Lax${domain}${secure}`;
    document.dispatchEvent(new CustomEvent('a1-authchange', { detail: { user, token } }));
  } catch (_) {}
}

export function logout(): void {
  try {
    const isAlphaOne = location.hostname === 'alphaonelabs.com' || location.hostname.endsWith('.alphaonelabs.com');
    const domain = isAlphaOne ? '; domain=.alphaonelabs.com' : '';
    document.cookie = `a1_token=; path=/; max-age=0; SameSite=Lax${domain}`;
    document.cookie = `a1_user=; path=/; max-age=0; SameSite=Lax${domain}`;
    document.cookie = 'a1_token=; path=/; max-age=0; SameSite=Lax';
    document.cookie = 'a1_user=; path=/; max-age=0; SameSite=Lax';
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    sessionStorage.clear();
    document.dispatchEvent(new CustomEvent('a1-authchange', { detail: { user: null, token: null } }));
  } catch (_) {}
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
