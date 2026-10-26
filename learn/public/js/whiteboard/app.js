/**
 * Main application coordinator for the collaborative whiteboard.
 */

import {
  getAuthToken,
  preserveWhiteboardRedirect,
  getViewerId,
  generateEventId,
  computeInitialImageBounds,
  saveBackgrounds,
  loadBackgrounds,
} from './storage.js';

import { WhiteboardRenderer } from './renderer.js';
import { InlineTextEditor } from './text-editor.js';
import { WhiteboardSocket } from './socket.js';
import { DrawingController } from './drawing-controller.js';
import {
  setStatus,
  syncToolButtons,
  updateActiveUsersList,
  applyViewerRestrictions,
  bindWhiteboardControls,
} from './ui.js';

(function initWhiteboardApp() {
  const token = getAuthToken();
  const canInteract = Boolean(token);

  // DOM Elements
  const canvas = document.getElementById('whiteboard');
  const viewportEl = document.getElementById('canvas-viewport');
  const roomInput = document.getElementById('room');
  const statusEl = document.getElementById('status');
  const loginLink = document.getElementById('whiteboard-login');
  const toolSelect = document.getElementById('toolSelect');
  const penColorInput = document.getElementById('penColor');
  const penWidthInput = document.getElementById('penWidth');
  const activeUsers = document.getElementById('activeUsers');
  const activeCount = document.getElementById('active-count');
  const coordinates = document.getElementById('coordinates');

  // App State
  let currentParticipantId = '';
  let events = [];
  let seenEventIds = new Set();
  let redoStack = [];
  // Multi-image state: [{ img, bounds, dataUrl }]
  let images = [];

  // Subsystem Instances
  const renderer = new WhiteboardRenderer(canvas);

  const textEditor = new InlineTextEditor(viewportEl, canvas, {
    onCommit(text, point, existingEvent) {
      if (!text) {
        if (existingEvent?.event_id) {
          events = events.filter((e) => e.event_id !== existingEvent.event_id);
          renderer.redrawAll(events);
        }
        return;
      }

      if (existingEvent?.event_id) {
        const idx = events.findIndex((e) => e.event_id === existingEvent.event_id);
        if (idx !== -1) {
          events[idx] = Object.assign({}, events[idx], { text });
          renderer.redrawAll(events);
          socket.sendEvent(events[idx]);
        }
      } else {
        const textEvent = drawingController.makeEvent('text', point, point, text);
        sendEvent(textEvent);
      }
    },
    onCancel() {}
  });

  const socket = new WhiteboardSocket({
    onStatusChange(text, isConnected) {
      setStatus(statusEl, text, isConnected);
    },
    onUserInfo(participantId) {
      currentParticipantId = participantId;
    },
    onWhiteboardState(incomingEvents) {
      events = incomingEvents;
      seenEventIds = new Set(events.map((e) => e?.event_id).filter(Boolean));
      renderer.redrawAll(events);
    },
    onWhiteboardEvent(event) {
      applyIncomingEvent(event);
    },
    onWhiteboardClear() {
      events = [];
      seenEventIds = new Set();
      redoStack = [];
      renderer.redrawAll(events);
    },
    onRoomState(participants) {
      updateActiveUsersList(activeUsers, activeCount, participants);
    }
  });

  function getRoomName() {
    return (roomInput?.value || 'main-whiteboard').trim() || 'main-whiteboard';
  }

  function loginForWhiteboard() {
    preserveWhiteboardRedirect();
    window.location.href = '/login';
  }

  function applyIncomingEvent(event) {
    if (!event) return;
    if (event.event_id && seenEventIds.has(event.event_id)) return;
    if (event.event_id) seenEventIds.add(event.event_id);
    events.push(event);
    if (events.length > 1000) events = events.slice(-1000);
    renderer.drawEvent(event);
  }

  function sendEvent(event) {
    if (!canInteract) {
      loginForWhiteboard();
      return;
    }
    if (!socket.isOpen()) return;

    redoStack = [];
    if (currentParticipantId) event.participant_id = currentParticipantId;
    if (event.event_id) seenEventIds.add(event.event_id);
    events.push(event);
    if (events.length > 1000) events = events.slice(-1000);
    renderer.drawEvent(event);
    socket.sendEvent(event);
  }

  function serializeImages() {
    return images.map((i) => ({ dataUrl: i.dataUrl, bounds: i.bounds }));
  }

  const drawingController = new DrawingController(canvas, renderer, textEditor, {
    canInteract,
    onSendEvent: (event) => sendEvent(event),
    onPreview: (draftEvent) => renderer.redrawAll(events, draftEvent),
    onRequireLogin: loginForWhiteboard,
    getTool: () => toolSelect?.value || 'pen',
    getPenColor: () => penColorInput?.value || '#0f766e',
    getPenWidth: () => Number(penWidthInput?.value || 4),
    getEvents: () => events,
    getImages: () => images.map((i) => ({ img: i.img, bounds: i.bounds })),
    onCoordinates: (point) => {
      if (coordinates) {
        coordinates.textContent = `x: ${Math.round(point.x * canvas.width)}, y: ${Math.round(point.y * canvas.height)}`;
      }
    },
    onSelectImage: (idx) => {
      renderer.selectedImageIndex = idx;
      renderer.redrawAll(events);
    },
    onImageResize: (idx, newBounds) => {
      if (images[idx]) images[idx].bounds = newBounds;
      if (renderer.images[idx]) renderer.images[idx].bounds = newBounds;
    },
    onImageResizeEnd: (idx, finalBounds) => {
      if (images[idx]) images[idx].bounds = finalBounds;
      if (renderer.images[idx]) renderer.images[idx].bounds = finalBounds;
      saveBackgrounds(getRoomName(), serializeImages());
    }
  });

  function loadBackgroundFromStorage() {
    images = [];
    renderer.setImages([]);
    renderer.selectedImageIndex = -1;

    const stored = loadBackgrounds(getRoomName());
    if (!stored || stored.length === 0) {
      renderer.redrawAll(events);
      return;
    }

    let loaded = 0;
    stored.forEach((item, i) => {
      const img = new Image();
      img.onload = () => {
        const bounds = (item.bounds && item.bounds.width)
          ? item.bounds
          : computeInitialImageBounds(img, canvas);
        images[i] = { img, bounds, dataUrl: item.dataUrl };
        loaded++;
        if (loaded === stored.length) {
          // Remove any gaps from out-of-order loads
          const compact = images.filter(Boolean);
          images = compact;
          renderer.setImages(compact.map((im) => ({ img: im.img, bounds: im.bounds })));
          renderer.redrawAll(events);
        }
      };
      img.onerror = () => {
        loaded++;
        if (loaded === stored.length) {
          const compact = images.filter(Boolean);
          images = compact;
          renderer.setImages(compact.map((im) => ({ img: im.img, bounds: im.bounds })));
          renderer.redrawAll(events);
        }
      };
      img.src = item.dataUrl;
    });
  }

  function connectToRoom() {
    socket.disconnect();
    events = [];
    seenEventIds = new Set();
    redoStack = [];
    renderer.redrawAll(events);
    loadBackgroundFromStorage();
    socket.connect(getRoomName(), token, getViewerId());
  }

  function clearRoom() {
    if (!canInteract) {
      loginForWhiteboard();
      return;
    }
    if (!confirm('Clear this whiteboard room for everyone?')) return;
    events = [];
    seenEventIds = new Set();
    redoStack = [];
    renderer.redrawAll(events);
    socket.clearRoom();
  }

  function undo() {
    if (!canInteract) {
      loginForWhiteboard();
      return;
    }
    const idx = [...events].reverse().find(
      (ev) => !currentParticipantId || ev.participant_id === currentParticipantId || !ev.participant_id
    );
    if (idx) redoStack.push(idx);
    socket.undo();
  }

  function redo() {
    if (!canInteract) {
      loginForWhiteboard();
      return;
    }
    const event = redoStack.pop();
    if (!event) return;
    const copy = Object.assign({}, event, { event_id: generateEventId() });
    sendEvent(copy);
  }

  // Backspace to delete the selected image
  window.addEventListener('keydown', (e) => {
    if (e.key !== 'Backspace') return;
    const tag = document.activeElement && document.activeElement.tagName.toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
    const selectedIndex = renderer.selectedImageIndex;
    if (selectedIndex < 0 || selectedIndex >= images.length) return;
    e.preventDefault();
    images.splice(selectedIndex, 1);
    renderer.removeImage(selectedIndex);
    saveBackgrounds(getRoomName(), serializeImages());
    renderer.redrawAll(events);
  });

  // Bind DOM controls
  if (loginLink) loginLink.addEventListener('click', preserveWhiteboardRedirect);

  bindWhiteboardControls({
    canInteract,
    onConnect: connectToRoom,
    onToolChange: (tool) => syncToolButtons(tool, canvas),
    onColorChange: () => {},
    onWidthChange: () => {},
    onImageUpload: (file) => {
      const reader = new FileReader();
      reader.onload = (loadEvent) => {
        const dataUrl = loadEvent.target.result;
        const img = new Image();
        img.onload = () => {
          const bounds = computeInitialImageBounds(img, canvas);
          images.push({ img, bounds, dataUrl });
          renderer.addImage(img, bounds);
          renderer.redrawAll(events);
          saveBackgrounds(getRoomName(), serializeImages());
        };
        img.src = dataUrl;
      };
      reader.readAsDataURL(file);
    },
    onImageScale: () => {},
    onImageRemove: () => {},
    onDownload: () => renderer.exportToPng(getRoomName()),
    onClear: clearRoom,
    onUndo: undo,
    onRedo: redo,
    onRequireLogin: loginForWhiteboard
  });

  if (!canInteract) {
    applyViewerRestrictions(canvas);
  }

  // Initial render & connection
  syncToolButtons(toolSelect?.value || 'pen', canvas);
  renderer.redrawAll(events);
  connectToRoom();
})();
