/**
 * Graph Controller: Viewport state and input handling (mouse, touch, wheel, keyboard).
 */

import { NAVIGATION } from './config.js';

export class GraphController {
  /**
   * @param {HTMLCanvasElement} mainCanvas
   * @param {HTMLCanvasElement} [fsCanvas]
   * @param {Object} initialView
   * @param {Object} [options]
   * @param {((V: Object) => void)} [options.onViewChange]
   * @param {((x: number, y: number) => void)} [options.onCoordinates]
   * @param {(() => void)} [options.onCoordinatesLeave]
   */
  constructor(mainCanvas, fsCanvas, initialView, options = {}) {
    this.mainCanvas = mainCanvas;
    this.fsCanvas = fsCanvas || null;
    this.V = { ...initialView };
    this.options = options;

    this.drag = { on: false, sx: 0, sy: 0, V0: null };
    this.touch = { dist: null, cx: null, cy: null };
    this.fsDrag = { on: false, sx: 0, sy: 0, V0: null };

    this._bindEvents();
  }

  getView() {
    return { ...this.V };
  }

  setView(newV) {
    this.V = { ...newV };
    this.notifyViewChange();
  }

  notifyViewChange() {
    if (typeof this.options.onViewChange === 'function') {
      this.options.onViewChange(this.getView());
    }
  }

  viewCenter() {
    return {
      x: (this.V.xMin + this.V.xMax) / 2,
      y: (this.V.yMin + this.V.yMax) / 2,
    };
  }

  /**
   * Adjusts the yMin and yMax to preserve a 1:1 square aspect ratio based on width and height.
   */
  fitAspect(w, h, silent = false) {
    if (!w || !h) return;
    const cx = (this.V.xMin + this.V.xMax) / 2;
    const cy = (this.V.yMin + this.V.yMax) / 2;
    const rx = (this.V.xMax - this.V.xMin) / 2;
    const ratio = h / w;
    this.V.yMin = cy - rx * ratio;
    this.V.yMax = cy + rx * ratio;
    if (!silent) {
      this.notifyViewChange();
    }
  }

  resetView(w, h) {
    const ratio = h > 0 && w > 0 ? h / w : 0.7;
    this.V = {
      xMin: -10,
      xMax: 10,
      yMin: -10 * ratio,
      yMax: 10 * ratio,
    };
    this.notifyViewChange();
  }

  zoomAround(cx, cy, factor) {
    if (!isFinite(factor) || factor <= 0) return;
    const nextXMin = cx + (this.V.xMin - cx) * factor;
    const nextXMax = cx + (this.V.xMax - cx) * factor;
    const nextYMin = cy + (this.V.yMin - cy) * factor;
    const nextYMax = cy + (this.V.yMax - cy) * factor;
    const rx = nextXMax - nextXMin;
    const ry = nextYMax - nextYMin;
    if (!isFinite(rx) || !isFinite(ry) || rx <= 1e-12 || ry <= 1e-12 || rx >= 1e14 || ry >= 1e14) {
      return;
    }
    this.V.xMin = nextXMin;
    this.V.xMax = nextXMax;
    this.V.yMin = nextYMin;
    this.V.yMax = nextYMax;
    this.notifyViewChange();
  }

  zoomIn() {
    const c = this.viewCenter();
    this.zoomAround(c.x, c.y, NAVIGATION.ZOOM_IN_FACTOR);
  }

  zoomOut() {
    const c = this.viewCenter();
    this.zoomAround(c.x, c.y, NAVIGATION.ZOOM_OUT_FACTOR);
  }

  panBy(fx, fy) {
    const rx = this.V.xMax - this.V.xMin;
    const ry = this.V.yMax - this.V.yMin;
    this.V.xMin += rx * fx;
    this.V.xMax += rx * fx;
    this.V.yMin += ry * fy;
    this.V.yMax += ry * fy;
    this.notifyViewChange();
  }

  panLeft() {
    this.panBy(-NAVIGATION.PAN_STEP, 0);
  }

  panRight() {
    this.panBy(NAVIGATION.PAN_STEP, 0);
  }

  panUp() {
    this.panBy(0, NAVIGATION.PAN_STEP);
  }

  panDown() {
    this.panBy(0, -NAVIGATION.PAN_STEP);
  }

  _toMath(px, py, w, h) {
    return {
      x: this.V.xMin + (px / w) * (this.V.xMax - this.V.xMin),
      y: this.V.yMin + ((h - py) / h) * (this.V.yMax - this.V.yMin),
    };
  }

  _bindEvents() {
    if (!this.mainCanvas) return;

    // --- Main Canvas Wheel Zoom ---
    this.mainCanvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const rect = this.mainCanvas.getBoundingClientRect();
      const w = this.mainCanvas.clientWidth;
      const h = this.mainCanvas.clientHeight;
      const { x, y } = this._toMath(e.clientX - rect.left, e.clientY - rect.top, w, h);
      this.zoomAround(x, y, e.deltaY > 0 ? NAVIGATION.WHEEL_ZOOM_OUT : NAVIGATION.WHEEL_ZOOM_IN);
    }, { passive: false });

    // --- Main Canvas Mouse Drag & Coordinates ---
    this.mainCanvas.addEventListener('mousedown', (e) => {
      this.drag = { on: true, sx: e.clientX, sy: e.clientY, V0: { ...this.V } };
      this.mainCanvas.classList.add('grabbing');
    });

    window.addEventListener('mousemove', (e) => {
      const w = this.mainCanvas.clientWidth;
      const h = this.mainCanvas.clientHeight;
      const rect = this.mainCanvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      // Coordinate tracking
      if (mx >= 0 && mx <= w && my >= 0 && my <= h) {
        const { x, y } = this._toMath(mx, my, w, h);
        if (typeof this.options.onCoordinates === 'function') {
          this.options.onCoordinates(x, y);
        }
      }

      if (!this.drag.on) return;
      const rx = this.drag.V0.xMax - this.drag.V0.xMin;
      const ry = this.drag.V0.yMax - this.drag.V0.yMin;
      const shx = -((e.clientX - this.drag.sx) / w) * rx;
      const shy = ((e.clientY - this.drag.sy) / h) * ry;

      this.V.xMin = this.drag.V0.xMin + shx;
      this.V.xMax = this.drag.V0.xMax + shx;
      this.V.yMin = this.drag.V0.yMin + shy;
      this.V.yMax = this.drag.V0.yMax + shy;
      this.notifyViewChange();
    });

    window.addEventListener('mouseup', () => {
      if (this.drag.on) {
        this.drag.on = false;
        this.mainCanvas.classList.remove('grabbing');
      }
    });

    // --- Touch Events ---
    this._bindTouchEvents(this.mainCanvas);

    // --- Keyboard Navigation ---
    this.mainCanvas.addEventListener('keydown', (e) => {
      switch (e.key) {
        case 'ArrowLeft':
          this.panLeft();
          break;
        case 'ArrowRight':
          this.panRight();
          break;
        case 'ArrowUp':
          this.panUp();
          break;
        case 'ArrowDown':
          this.panDown();
          break;
        case '+':
        case '=':
          this.zoomIn();
          break;
        case '-':
        case '_':
          this.zoomOut();
          break;
        default:
          return;
      }
      e.preventDefault();
    });

    // --- Fullscreen Canvas Interactions ---
    if (this.fsCanvas) {
      this.fsCanvas.addEventListener('mousedown', (e) => {
        this.fsDrag = { on: true, sx: e.clientX, sy: e.clientY, V0: { ...this.V } };
        this.fsCanvas.classList.add('grabbing');
      });

      window.addEventListener('mousemove', (e) => {
        if (!this.fsDrag.on) return;
        const w = this.fsCanvas.clientWidth;
        const h = this.fsCanvas.clientHeight;
        const rx = this.fsDrag.V0.xMax - this.fsDrag.V0.xMin;
        const ry = this.fsDrag.V0.yMax - this.fsDrag.V0.yMin;

        this.V.xMin = this.fsDrag.V0.xMin - ((e.clientX - this.fsDrag.sx) / w) * rx;
        this.V.xMax = this.fsDrag.V0.xMax - ((e.clientX - this.fsDrag.sx) / w) * rx;
        this.V.yMin = this.fsDrag.V0.yMin + ((e.clientY - this.fsDrag.sy) / h) * ry;
        this.V.yMax = this.fsDrag.V0.yMax + ((e.clientY - this.fsDrag.sy) / h) * ry;
        this.notifyViewChange();
      });

      window.addEventListener('mouseup', () => {
        if (this.fsDrag.on) {
          this.fsDrag.on = false;
          this.fsCanvas.classList.remove('grabbing');
        }
      });

      this.fsCanvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const w = this.fsCanvas.clientWidth;
        const h = this.fsCanvas.clientHeight;
        const rect = this.fsCanvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        const { x, y } = this._toMath(mx, my, w, h);
        const factor = e.deltaY > 0 ? NAVIGATION.WHEEL_ZOOM_OUT : NAVIGATION.WHEEL_ZOOM_IN;
        this.zoomAround(x, y, factor);
      }, { passive: false });

      this._bindTouchEvents(this.fsCanvas);
    }
  }

  /**
   * Helper to bind touch drag and pinch-to-zoom gestures for a given canvas.
   * @param {HTMLCanvasElement} targetCanvas
   */
  _bindTouchEvents(targetCanvas) {
    if (!targetCanvas) return;

    const touchState = {
      drag: { on: false, sx: 0, sy: 0, V0: null },
      pinch: { dist: null, cx: null, cy: null },
    };

    targetCanvas.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        touchState.drag = { on: true, sx: e.touches[0].clientX, sy: e.touches[0].clientY, V0: { ...this.V } };
        touchState.pinch.dist = null;
      } else if (e.touches.length === 2) {
        touchState.drag.on = false;
        const [t1, t2] = [e.touches[0], e.touches[1]];
        touchState.pinch.dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
        const rect = targetCanvas.getBoundingClientRect();
        touchState.pinch.cx = ((t1.clientX + t2.clientX) / 2) - rect.left;
        touchState.pinch.cy = ((t1.clientY + t2.clientY) / 2) - rect.top;
      }
      e.preventDefault();
    }, { passive: false });

    targetCanvas.addEventListener('touchmove', (e) => {
      const w = targetCanvas.clientWidth;
      const h = targetCanvas.clientHeight;
      if (!w || !h) return;

      if (e.touches.length === 1 && touchState.drag.on && touchState.drag.V0) {
        const rx = touchState.drag.V0.xMax - touchState.drag.V0.xMin;
        const ry = touchState.drag.V0.yMax - touchState.drag.V0.yMin;
        this.V.xMin = touchState.drag.V0.xMin - ((e.touches[0].clientX - touchState.drag.sx) / w) * rx;
        this.V.xMax = touchState.drag.V0.xMax - ((e.touches[0].clientX - touchState.drag.sx) / w) * rx;
        this.V.yMin = touchState.drag.V0.yMin + ((e.touches[0].clientY - touchState.drag.sy) / h) * ry;
        this.V.yMax = touchState.drag.V0.yMax + ((e.touches[0].clientY - touchState.drag.sy) / h) * ry;
        this.notifyViewChange();
      } else if (e.touches.length === 2 && touchState.pinch.dist !== null) {
        const [t1, t2] = [e.touches[0], e.touches[1]];
        const d2 = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
        if (d2 > 0) {
          const { x, y } = this._toMath(touchState.pinch.cx, touchState.pinch.cy, w, h);
          this.zoomAround(x, y, touchState.pinch.dist / d2);
          touchState.pinch.dist = d2;
        }
      }
      e.preventDefault();
    }, { passive: false });

    const endTouch = () => {
      touchState.drag.on = false;
      touchState.pinch.dist = null;
    };
    targetCanvas.addEventListener('touchend', endTouch);
    targetCanvas.addEventListener('touchcancel', endTouch);
  }
}
