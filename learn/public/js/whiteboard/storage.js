/**
 * Storage and identifier utilities for the Whiteboard module.
 */

export function getAuthToken() {
  return localStorage.getItem('edu_token') || localStorage.getItem('token') || '';
}

export function preserveWhiteboardRedirect() {
  try {
    sessionStorage.setItem('post_login_redirect', location.pathname + location.search);
  } catch (_) {}
}

export function getViewerId() {
  try {
    let id = localStorage.getItem('classroom_participant_id');
    if (!id) {
      id = typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : String(Date.now()) + Math.random().toString(16).slice(2);
      localStorage.setItem('classroom_participant_id', id);
    }
    return id;
  } catch (_) {
    return String(Date.now()) + Math.random().toString(16).slice(2);
  }
}

export function generateEventId() {
  try {
    return crypto.randomUUID().replace(/[^A-Za-z0-9_-]/g, '');
  } catch (_) {
    return 'evt_' + Date.now() + '_' + Math.random().toString(16).slice(2);
  }
}

function backgroundKey(roomName) {
  return 'whiteboard_background_' + (roomName || 'main-whiteboard');
}

export function saveBackground(roomName, imageDataUrl, scale) {
  try {
    if (imageDataUrl) {
      localStorage.setItem(backgroundKey(roomName), JSON.stringify({ data: imageDataUrl, scale: scale || 1 }));
    } else {
      removeBackground(roomName);
    }
  } catch (_) {}
}

export function loadBackground(roomName) {
  try {
    const raw = localStorage.getItem(backgroundKey(roomName));
    if (!raw) return null;
    const payload = JSON.parse(raw);
    if (!payload || !payload.data) return null;
    return {
      dataUrl: payload.data,
      scale: Number(payload.scale || 1)
    };
  } catch (_) {
    return null;
  }
}

export function removeBackground(roomName) {
  try {
    localStorage.removeItem(backgroundKey(roomName));
  } catch (_) {}
}
