export interface AuthUser {
  id: number | string;
  username: string;
  name?: string;
  email?: string;
  [key: string]: unknown;
}

const TOKEN_KEY = "edu_token";
const USER_KEY = "edu_user";

function isAlphaOneDomain(): boolean {
  return location.hostname === 'alphaonelabs.com' || location.hostname.endsWith('.alphaonelabs.com');
}

function getCookie(name: string): string | null {
  try {
    const prefix = name + "=";
    const cookies = document.cookie ? document.cookie.split("; ") : [];
    for (let i = 0; i < cookies.length; i++) {
      const c = cookies[i];
      if (c.indexOf(prefix) === 0) {
        return decodeURIComponent(c.substring(prefix.length));
      }
    }
  } catch (_) {}
  return null;
}

function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return true;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (payload && typeof payload.exp === "number") {
      return (Date.now() / 1000) >= payload.exp;
    }
    return false;
  } catch {
    return true;
  }
}

export function getToken(): string | null {
  const cToken = getCookie('a1_token');
  if (cToken) {
    if (isTokenExpired(cToken)) {
      logoutCookiesOnly();
      return null;
    }
    return cToken;
  }
  if (isAlphaOneDomain()) {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch (_) {}
    return null;
  }
  try {
    const local = localStorage.getItem(TOKEN_KEY);
    if (local && !isTokenExpired(local)) return local;
  } catch (_) {}
  return null;
}

export function getUser(): AuthUser | null {
  const token = getToken();
  if (!token) return null;
  const cUserRaw = getCookie('a1_user');
  if (cUserRaw) {
    try {
      return JSON.parse(cUserRaw) as AuthUser;
    } catch (_) {}
  }
  if (!isAlphaOneDomain()) {
    try {
      const raw = localStorage.getItem(USER_KEY);
      if (raw) return JSON.parse(raw) as AuthUser;
    } catch (_) {}
  }
  return null;
}

export function isAuthenticated(): boolean {
  return getToken() !== null && getUser() !== null;
}

function sanitizeUser(user: AuthUser): Record<string, unknown> {
  const rawAvatar = typeof user.avatar_url === 'string' ? user.avatar_url : '';
  const avatar = (rawAvatar && !rawAvatar.startsWith('data:') && rawAvatar.length < 500) ? rawAvatar : '';
  return {
    id: user.id,
    username: user.username,
    name: user.name || user.username,
    role: user.role || 'member',
    avatar_url: avatar
  };
}

export function storeAuth(token: string, user: AuthUser): void {
  const clean = sanitizeUser(user);
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(clean));
  } catch (_) {}
  try {
    const isAlphaOne = isAlphaOneDomain();
    const domain = isAlphaOne ? '; domain=.alphaonelabs.com' : '';
    const secure = location.protocol === 'https:' ? '; Secure' : '';
    const maxAge = 60 * 60 * 24 * 7;
    document.cookie = `a1_token=${encodeURIComponent(token)}; path=/; max-age=${maxAge}; SameSite=Lax${domain}${secure}`;
    document.cookie = `a1_user=${encodeURIComponent(JSON.stringify(clean))}; path=/; max-age=${maxAge}; SameSite=Lax${domain}${secure}`;
    document.dispatchEvent(new CustomEvent('a1-authchange', { detail: { user: clean, token } }));
  } catch (_) {}
}

function logoutCookiesOnly(): void {
  try {
    const domain = isAlphaOneDomain() ? '; domain=.alphaonelabs.com' : '';
    document.cookie = `a1_token=; path=/; max-age=0; SameSite=Lax${domain}`;
    document.cookie = `a1_user=; path=/; max-age=0; SameSite=Lax${domain}`;
    document.cookie = 'a1_token=; path=/; max-age=0; SameSite=Lax';
    document.cookie = 'a1_user=; path=/; max-age=0; SameSite=Lax';
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    sessionStorage.clear();
  } catch (_) {}
}

export function logout(): void {
  logoutCookiesOnly();
  try {
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
