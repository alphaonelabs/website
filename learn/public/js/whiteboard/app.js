/**
 * Main application coordinator for the collaborative whiteboard.
 */

import {
  getAuthToken,
  preserveWhiteboardRedirect,
  getViewerId,
  generateEventId,
  saveBackground,
  loadBackground,
  removeBackground,
  computeInitialImageBounds,
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
  let uploadedImage = null;
  let imageDataUrl = '';
  let imageBounds = null;

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

  function updateImageUi() {
    const removeBtn = document.getElementById('removeImage');
    if (removeBtn) {
      if (uploadedImage) {
        removeBtn.classList.remove('hidden');
        removeBtn.classList.add('flex');
      } else {
        removeBtn.classList.add('hidden');
        removeBtn.classList.remove('flex');
      }
    }
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
    onCoordinates: (point) => {
      if (coordinates) {
        coordinates.textContent = `x: ${Math.round(point.x * canvas.width)}, y: ${Math.round(point.y * canvas.height)}`;
      }
    },
    onImageResize: (newBounds) => {
      imageBounds = newBounds;
    },
    onImageResizeEnd: (finalBounds) => {
      imageBounds = finalBounds;
      if (imageDataUrl) {
        saveBackground(getRoomName(), imageDataUrl, imageBounds);
      }
    }
  });

  function loadBackgroundFromStorage() {
    uploadedImage = null;
    imageDataUrl = '';
    imageBounds = null;
    const stored = loadBackground(getRoomName());
    if (!stored) {
      renderer.setImage(null, null);
      renderer.redrawAll(events);
      updateImageUi();
      return;
    }

    imageDataUrl = stored.dataUrl;
    const img = new Image();
    img.onload = () => {
      uploadedImage = img;
      if (stored.bounds && stored.bounds.width) {
        imageBounds = stored.bounds;
      } else {
        imageBounds = computeInitialImageBounds(img, canvas);
      }
      renderer.setImage(uploadedImage, imageBounds);
      renderer.redrawAll(events);
      updateImageUi();
    };
    img.src = imageDataUrl;
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
        imageDataUrl = loadEvent.target.result;
        const img = new Image();
        img.onload = () => {
          uploadedImage = img;
          imageBounds = computeInitialImageBounds(img, canvas);
          saveBackground(getRoomName(), imageDataUrl, imageBounds);
          renderer.setImage(uploadedImage, imageBounds);
          renderer.redrawAll(events);
          updateImageUi();
        };
        img.src = imageDataUrl;
      };
      reader.readAsDataURL(file);
    },
    onImageScale: () => {},
    onImageRemove: () => {
      uploadedImage = null;
      imageDataUrl = '';
      imageBounds = null;
      removeBackground(getRoomName());
      renderer.setImage(null, null);
      renderer.redrawAll(events);
      updateImageUi();
    },
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