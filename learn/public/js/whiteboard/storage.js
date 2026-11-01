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

function backgroundsKey(roomName) {
  return 'whiteboard_backgrounds_' + (roomName || 'main-whiteboard');
}

// Downscale a data URL through an offscreen canvas to fit localStorage quota.
function downscaleDataUrl(dataUrl, maxSize) {
  try {
    const img = new Image();
    img.src = dataUrl;
    const w = img.naturalWidth || img.width;
    const h = img.naturalHeight || img.height;
    if (!w || !h) return null;
    const scale = Math.min(1, maxSize / Math.max(w, h));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(w * scale));
    canvas.height = Math.max(1, Math.round(h * scale));
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.82);
  } catch (_) {
    return null;
  }
}

/**
 * Compute initial placement bounds for a newly added image.
 * Targets ~36% of screen width, clamped to 20%–85% of canvas width and 80% of canvas height,
 * then centered. The display-to-canvas scale factor accounts for CSS scaling of the canvas element.
 */
export function computeInitialImageBounds(img, canvas) {
  const naturalWidth = img.naturalWidth || img.width || 400;
  const naturalHeight = img.naturalHeight || img.height || 300;
  const aspectRatio = naturalHeight / naturalWidth;

  const screenWidth = typeof window !== 'undefined' ? (window.innerWidth || 1200) : 1200;
  const canvasWidth = canvas?.width || 1500;
  const canvasHeight = canvas?.height || 800;

  let scaleToCanvas = 1;
  if (canvas && typeof canvas.getBoundingClientRect === 'function') {
    const rect = canvas.getBoundingClientRect();
    if (rect.width > 0) scaleToCanvas = canvasWidth / rect.width;
  }

  const minWidth = Math.min(160, canvasWidth * 0.2);
  const maxWidth = canvasWidth * 0.85;
  let initialWidth = Math.max(minWidth, Math.min(maxWidth, screenWidth * 0.36 * scaleToCanvas));

  let initialHeight = initialWidth * aspectRatio;
  const maxHeight = canvasHeight * 0.8;
  if (initialHeight > maxHeight) {
    initialHeight = maxHeight;
    initialWidth = initialHeight / aspectRatio;
  }

  return {
    x: Math.max(20, Math.round((canvasWidth - initialWidth) / 2)),
    y: Math.max(20, Math.round((canvasHeight - initialHeight) / 2)),
    width: Math.round(initialWidth),
    height: Math.round(initialHeight)
  };
}

export function saveBackgrounds(roomName, imagesData) {
  try {
    const items = (imagesData || []).map((item) => ({ data: item.dataUrl, bounds: item.bounds }));
    try {
      localStorage.setItem(backgroundsKey(roomName), JSON.stringify(items));
    } catch (_quotaErr) {
      // On quota error, downscale each image and retry once
      const downscaled = items.map((item) => ({
        data: downscaleDataUrl(item.data, 1400) || item.data,
        bounds: item.bounds
      }));
      try {
        localStorage.setItem(backgroundsKey(roomName), JSON.stringify(downscaled));
      } catch (_) {}
    }
  } catch (_) {}
}

export function loadBackgrounds(roomName) {
  try {
    const raw = localStorage.getItem(backgroundsKey(roomName));
    if (!raw) return [];
    const items = JSON.parse(raw);
    if (!Array.isArray(items)) return [];
    return items
      .filter((item) => item && item.data)
      .map((item) => ({ dataUrl: item.data, bounds: item.bounds || null }));
  } catch (_) {
    return [];
  }
}

/** @deprecated Use saveBackgrounds for multi-image rooms. */
export function saveBackground(roomName, imageDataUrl, boundsOrScale) {
  try {
    if (imageDataUrl) {
      const payload = { data: imageDataUrl };
      if (typeof boundsOrScale === 'object' && boundsOrScale !== null) {
        payload.bounds = boundsOrScale;
      } else {
        payload.scale = Number(boundsOrScale || 1);
      }
      try {
        localStorage.setItem(backgroundKey(roomName), JSON.stringify(payload));
      } catch (_quotaErr) {
        const downscaled = downscaleDataUrl(imageDataUrl, 1400);
        if (downscaled) {
          payload.data = downscaled;
          localStorage.setItem(backgroundKey(roomName), JSON.stringify(payload));
        }
      }
    } else {
      removeBackground(roomName);
    }
  } catch (_) {}
}

/** @deprecated Use loadBackgrounds for multi-image rooms. */
export function loadBackground(roomName) {
  try {
    const raw = localStorage.getItem(backgroundKey(roomName));
    if (!raw) return null;
    const payload = JSON.parse(raw);
    if (!payload || !payload.data) return null;
    return {
      dataUrl: payload.data,
      bounds: payload.bounds || null,
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
