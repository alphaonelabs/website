/**
 * Handles pointer, touch, and mouse input on the canvas to coordinate freehand and shape drawing.
 */

import { generateEventId } from './storage.js';

const SHAPE_TOOLS = ['line', 'rectangle', 'circle', 'arrow'];

const TOOL_MODE_MAP = {
  eraser: 'eraser',
  highlighter: 'highlighter',
  text: 'text',
};

export class DrawingController {
  constructor(canvas, renderer, textEditor, options = {}) {
    this.canvas = canvas;
    this.renderer = renderer;
    this.textEditor = textEditor;
    this.onSendEvent = options.onSendEvent || (() => {});
    this.onPreview = options.onPreview || (() => {});
    this.onRequireLogin = options.onRequireLogin || (() => {});
    this.getTool = options.getTool || (() => 'pen');
    this.getPenColor = options.getPenColor || (() => '#7a6418');
    this.getPenWidth = options.getPenWidth || (() => 4);
    this.canInteract = options.canInteract ?? true;
    this.getEvents = options.getEvents || (() => []);
    this.getImages = options.getImages || (() => []);
    this.onCoordinates = options.onCoordinates || (() => {});
    this.onImageResize = options.onImageResize || (() => {});
    this.onImageResizeEnd = options.onImageResizeEnd || (() => {});
    this.onSelectImage = options.onSelectImage || (() => {});

    this.drawing = false;
    this.startPoint = null;
    this.lastPoint = null;
    this.draftEvent = null;
    this.imageDrag = null;
    this.selectedImageIndex = -1;

    this.bindEvents();
  }

  currentMode() {
    const tool = this.getTool();
    return TOOL_MODE_MAP[tool] ?? (SHAPE_TOOLS.includes(tool) ? 'shape' : 'pen');
  }

  makeEvent(kind, from, to, text = '') {
    const mode = this.currentMode();
    return {
      event_id: generateEventId(),
      kind,
      from,
      to: to || from,
      color: this.getPenColor(),
      size: Number(this.getPenWidth() || 4),
      mode,
      alpha: mode === 'highlighter' ? 0.3 : 1,
      text
    };
  }

  getCanvasPixelPoint(e) {
    const rect = this.canvas.getBoundingClientRect();
    const touch = e.touches?.[0] ?? e.changedTouches?.[0] ?? e;
    const scaleX = rect.width > 0 ? (this.canvas.width / rect.width) : 1;
    const scaleY = rect.height > 0 ? (this.canvas.height / rect.height) : 1;
    return {
      x: (touch.clientX - rect.left) * scaleX,
      y: (touch.clientY - rect.top) * scaleY
    };
  }

  getImageHandleAt(point) {
    const images = this.getImages();
    const dist = (ax, ay) => Math.hypot(point.x - ax, point.y - ay);
    const radius = 15;
    const edgeTol = 7;

    // Iterate in reverse so topmost (last-added) image takes priority
    for (let i = images.length - 1; i >= 0; i--) {
      const b = images[i].bounds;
      if (!b) continue;

      const pillW = 60, pillH = 20;
      const pillX = b.x + b.width / 2 - pillW / 2;
      const pillY = b.y - pillH - 6;
      if (point.x >= pillX && point.x <= pillX + pillW && point.y >= pillY && point.y <= pillY + pillH) {
        return { type: 'move', cursor: 'move', imageIndex: i };
      }

      if (dist(b.x, b.y) <= radius)                       return { type: 'resize', handle: 'nw', cursor: 'nwse-resize', imageIndex: i };
      if (dist(b.x + b.width, b.y) <= radius)             return { type: 'resize', handle: 'ne', cursor: 'nesw-resize', imageIndex: i };
      if (dist(b.x + b.width, b.y + b.height) <= radius)  return { type: 'resize', handle: 'se', cursor: 'nwse-resize', imageIndex: i };
      if (dist(b.x, b.y + b.height) <= radius)            return { type: 'resize', handle: 'sw', cursor: 'nesw-resize', imageIndex: i };

      if (dist(b.x + b.width / 2, b.y) <= radius)          return { type: 'resize', handle: 'n', cursor: 'ns-resize', imageIndex: i };
      if (dist(b.x + b.width / 2, b.y + b.height) <= radius) return { type: 'resize', handle: 's', cursor: 'ns-resize', imageIndex: i };
      if (dist(b.x, b.y + b.height / 2) <= radius)         return { type: 'resize', handle: 'w', cursor: 'ew-resize', imageIndex: i };
      if (dist(b.x + b.width, b.y + b.height / 2) <= radius) return { type: 'resize', handle: 'e', cursor: 'ew-resize', imageIndex: i };

      const inX = point.x >= b.x - edgeTol && point.x <= b.x + b.width + edgeTol;
      const inY = point.y >= b.y - edgeTol && point.y <= b.y + b.height + edgeTol;

      if (inX && Math.abs(point.y - b.y) <= edgeTol)              return { type: 'resize', handle: 'n', cursor: 'ns-resize', imageIndex: i };
      if (inX && Math.abs(point.y - (b.y + b.height)) <= edgeTol) return { type: 'resize', handle: 's', cursor: 'ns-resize', imageIndex: i };
      if (inY && Math.abs(point.x - b.x) <= edgeTol)              return { type: 'resize', handle: 'w', cursor: 'ew-resize', imageIndex: i };
      if (inY && Math.abs(point.x - (b.x + b.width)) <= edgeTol)  return { type: 'resize', handle: 'e', cursor: 'ew-resize', imageIndex: i };
    }
    return null;
  }

  updateToolCursor() {
    if (!this.canInteract) {
      this.canvas.style.cursor = 'not-allowed';
      return;
    }
    const tool = this.getTool();
    if (tool === 'eraser') this.canvas.style.cursor = 'cell';
    else if (tool === 'text') this.canvas.style.cursor = 'text';
    else this.canvas.style.cursor = 'crosshair';
  }

  start(e) {
    const pixelPoint = this.getCanvasPixelPoint(e);
    const handle = this.getImageHandleAt(pixelPoint);

    if (handle) {
      e.preventDefault();
      if (!this.canInteract) { this.onRequireLogin(); return; }
      this.selectedImageIndex = handle.imageIndex;
      this.onSelectImage(handle.imageIndex);
      const b = this.getImages()[handle.imageIndex].bounds;
      this.imageDrag = {
        type: handle.type,
        handle: handle.handle,
        startPixel: pixelPoint,
        startBounds: { ...b },
        aspectRatio: b.height / b.width,
        imageIndex: handle.imageIndex
      };
      return;
    }

    // Clicking blank canvas deselects any image
    this.selectedImageIndex = -1;
    this.onSelectImage(-1);

    e.preventDefault();
    if (!this.canInteract) { this.onRequireLogin(); return; }

    const point = this.renderer.pointFromEvent(e);
    this.onCoordinates(point);

    if (this.getTool() === 'text') {
      const existing = this.textEditor.findTextEventAt(point, this.getEvents());
      this.textEditor.open(point, existing, this.getPenWidth(), this.getPenColor());
      return;
    }

    this.drawing = true;
    this.startPoint = point;
    this.lastPoint = point;
    this.draftEvent = null;
  }

  _handleImageDragMove(pixelPoint) {
    const { type, handle, startPixel, startBounds, aspectRatio, imageIndex } = this.imageDrag;
    const dx = pixelPoint.x - startPixel.x;
    const dy = pixelPoint.y - startPixel.y;
    let b = { ...startBounds };

    if (type === 'move') {
      b.x = Math.round(startBounds.x + dx);
      b.y = Math.round(startBounds.y + dy);
    } else if (handle === 'se') {
      const w = Math.max(50, startBounds.width + dx);
      b.width = Math.round(w);
      b.height = Math.round(w * aspectRatio);
    } else if (handle === 'sw') {
      const w = Math.max(50, startBounds.width - dx);
      b.x = Math.round(startBounds.x + (startBounds.width - w));
      b.width = Math.round(w);
      b.height = Math.round(w * aspectRatio);
    } else if (handle === 'ne') {
      const w = Math.max(50, startBounds.width + dx);
      const h = w * aspectRatio;
      b.y = Math.round(startBounds.y + (startBounds.height - h));
      b.width = Math.round(w);
      b.height = Math.round(h);
    } else if (handle === 'nw') {
      const w = Math.max(50, startBounds.width - dx);
      const h = w * aspectRatio;
      b.x = Math.round(startBounds.x + (startBounds.width - w));
      b.y = Math.round(startBounds.y + (startBounds.height - h));
      b.width = Math.round(w);
      b.height = Math.round(h);
    } else if (handle === 'e') {
      const w = Math.max(50, startBounds.width + dx);
      b.width = Math.round(w);
      b.height = Math.round(w * aspectRatio);
    } else if (handle === 'w') {
      const w = Math.max(50, startBounds.width - dx);
      b.x = Math.round(startBounds.x + (startBounds.width - w));
      b.width = Math.round(w);
      b.height = Math.round(w * aspectRatio);
    } else if (handle === 's') {
      const h = Math.max(40, startBounds.height + dy);
      b.height = Math.round(h);
      b.width = Math.round(h / aspectRatio);
    } else if (handle === 'n') {
      const h = Math.max(40, startBounds.height - dy);
      b.y = Math.round(startBounds.y + (startBounds.height - h));
      b.height = Math.round(h);
      b.width = Math.round(h / aspectRatio);
    }

    this.onImageResize(imageIndex, b);
    this.renderer.redrawAll(this.getEvents());
  }

  move(e) {
    const pixelPoint = this.getCanvasPixelPoint(e);

    if (this.imageDrag) {
      e.preventDefault();
      this._handleImageDragMove(pixelPoint);
      return;
    }

    if (!this.drawing) {
      const handle = this.getImageHandleAt(pixelPoint);
      this.canvas.style.cursor = handle ? handle.cursor : (this.updateToolCursor(), this.canvas.style.cursor);
    }

    const point = this.renderer.pointFromEvent(e);
    this.onCoordinates(point);
    if (!this.drawing || !this.lastPoint) return;
    e.preventDefault();

    const tool = this.getTool();
    if (tool === 'pen' || tool === 'eraser' || tool === 'highlighter') {
      this.onSendEvent(this.makeEvent('stroke', this.lastPoint, point));
      this.lastPoint = point;
    } else {
      this.draftEvent = this.makeEvent(tool, this.startPoint, point);
      this.onPreview(this.draftEvent);
    }
  }

  stop(e) {
    if (this.imageDrag) {
      const { imageIndex } = this.imageDrag;
      const images = this.getImages();
      const finalBounds = images[imageIndex]?.bounds ?? null;
      this.imageDrag = null;
      if (finalBounds) this.onImageResizeEnd(imageIndex, finalBounds);
      this.updateToolCursor();
      return;
    }

    if (!this.drawing) return;
    this.drawing = false;

    const hasPointer = e && (
      typeof e.clientX === 'number' ||
      e.touches?.[0] ||
      e.changedTouches?.[0]
    );
    const pointSource = e.changedTouches?.[0] ?? e;
    const point = hasPointer ? this.renderer.pointFromEvent(pointSource) : this.lastPoint;

    if (SHAPE_TOOLS.includes(this.getTool())) {
      this.onSendEvent(this.makeEvent(this.getTool(), this.startPoint, point));
    }

    this.startPoint = null;
    this.lastPoint = null;
    this.draftEvent = null;
    this.updateToolCursor();
  }

  bindEvents() {
    this.start = this.start.bind(this);
    this.move = this.move.bind(this);
    this.stop = this.stop.bind(this);

    this.canvas.addEventListener('mousedown', this.start);
    this.canvas.addEventListener('mousemove', this.move);
    window.addEventListener('mouseup', this.stop);

    this.canvas.addEventListener('touchstart', this.start, { passive: false });
    this.canvas.addEventListener('touchmove', this.move, { passive: false });
    this.canvas.addEventListener('touchend', this.stop, { passive: false });

    this.canvas.addEventListener('mouseleave', (e) => {
      this.stop(e);
      this.updateToolCursor();
    });

    // Double-click to edit existing text elements
    this.canvas.addEventListener('dblclick', (e) => {
      if (!this.canInteract) return;
      const point = this.renderer.pointFromEvent(e);
      const textEv = this.textEditor.findTextEventAt(point, this.getEvents());
      if (textEv) this.textEditor.open(point, textEv, this.getPenWidth(), this.getPenColor());
    });
  }
}
