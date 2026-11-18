/**
 * 2D Canvas Graphics Engine for Graphing Calculator
 */

export class GraphRenderer {
  /**
   * @param {HTMLCanvasElement} mainCanvas
   * @param {HTMLCanvasElement} [fsCanvas]
   */
  constructor(mainCanvas, fsCanvas) {
    this.mainCanvas = mainCanvas;
    this.mainCtx = mainCanvas ? mainCanvas.getContext('2d') : null;
    this.fsCanvas = fsCanvas || null;
    this.fsCtx = fsCanvas ? fsCanvas.getContext('2d') : null;
    this.dpr = window.devicePixelRatio || 1;
    this.fsDpr = window.devicePixelRatio || 1;
  }

  isDark() {
    return document.documentElement.classList.contains('dark');
  }

  getMainWidth() {
    return this.mainCanvas ? this.mainCanvas.clientWidth : 0;
  }

  getMainHeight() {
    return this.mainCanvas ? this.mainCanvas.clientHeight : 0;
  }

  getFsWidth() {
    return this.fsCanvas ? this.fsCanvas.clientWidth : 0;
  }

  getFsHeight() {
    return this.fsCanvas ? this.fsCanvas.clientHeight : 0;
  }

  /**
   * Resizes the main canvas to match its parent container at device pixel ratio.
   * @returns {{ width: number, height: number }}
   */
  resizeMain() {
    if (!this.mainCanvas || !this.mainCanvas.parentElement) {
      return { width: 0, height: 0 };
    }
    const parent = this.mainCanvas.parentElement;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    this.dpr = window.devicePixelRatio || 1;

    this.mainCanvas.width = w * this.dpr;
    this.mainCanvas.height = h * this.dpr;
    this.mainCanvas.style.width = w + 'px';
    this.mainCanvas.style.height = h + 'px';

    this.mainCtx.setTransform(1, 0, 0, 1, 0, 0);
    this.mainCtx.scale(this.dpr, this.dpr);

    return { width: w, height: h };
  }

  /**
   * Resizes the fullscreen canvas.
   * @param {number} w
   * @param {number} h
   * @returns {{ width: number, height: number }}
   */
  resizeFullscreen(w, h) {
    if (!this.fsCanvas) return { width: 0, height: 0 };
    this.fsDpr = window.devicePixelRatio || 1;

    this.fsCanvas.width = w * this.fsDpr;
    this.fsCanvas.height = h * this.fsDpr;
    this.fsCanvas.style.width = w + 'px';
    this.fsCanvas.style.height = h + 'px';

    this.fsCtx.setTransform(1, 0, 0, 1, 0, 0);
    this.fsCtx.scale(this.fsDpr, this.fsDpr);

    return { width: w, height: h };
  }

  /**
   * Maps a mathematical coordinate (x, y) to canvas pixels.
   */
  toPixel(x, y, w, h, V) {
    return {
      px: ((x - V.xMin) / (V.xMax - V.xMin)) * w,
      py: h - ((y - V.yMin) / (V.yMax - V.yMin)) * h,
    };
  }

  /**
   * Maps canvas pixel coordinates (px, py) to mathematical values (x, y).
   */
  toMath(px, py, w, h, V) {
    return {
      x: V.xMin + (px / w) * (V.xMax - V.xMin),
      y: V.yMin + ((h - py) / h) * (V.yMax - V.yMin),
    };
  }

  /**
   * Calculates a human-friendly grid step interval.
   */
  niceStep(range, maxTicks, gridSizeMul = 1) {
    const raw = range / maxTicks;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const r = raw / mag;
    const step = r < 1.5 ? 1 : r < 3.5 ? 2 : r < 7.5 ? 5 : 10;
    return step * mag * (gridSizeMul || 1);
  }

  /**
   * Formats numbers cleanly for tick labels.
   */
  formatNumber(n) {
    const s = parseFloat(n.toPrecision(5)).toString();
    return s.length > 8 ? n.toExponential(1) : s;
  }

  /**
   * Draws coordinate grid lines and tick labels.
   */
  drawGrid(ctx, w, h, V, dark, gridSizeMul = 1, maxTicksX = 10, maxTicksY = 8) {
    const xStep = this.niceStep(V.xMax - V.xMin, maxTicksX, gridSizeMul);
    const yStep = this.niceStep(V.yMax - V.yMin, maxTicksY, gridSizeMul);

    ctx.strokeStyle = dark ? 'rgba(255,255,255,0.055)' : 'rgba(0,0,0,0.065)';
    ctx.lineWidth = 1;

    const x0 = Math.ceil(V.xMin / xStep) * xStep;
    for (let x = x0; x <= V.xMax + xStep * 0.01; x += xStep) {
      const { px } = this.toPixel(x, 0, w, h, V);
      ctx.beginPath();
      ctx.moveTo(px, 0);
      ctx.lineTo(px, h);
      ctx.stroke();
    }

    const y0 = Math.ceil(V.yMin / yStep) * yStep;
    for (let y = y0; y <= V.yMax + yStep * 0.01; y += yStep) {
      const { py } = this.toPixel(0, y, w, h, V);
      ctx.beginPath();
      ctx.moveTo(0, py);
      ctx.lineTo(w, py);
      ctx.stroke();
    }

    // Tick labels
    const origin = this.toPixel(0, 0, w, h, V);
    const lx = Math.min(Math.max(origin.px + 5, 5), w - 36);
    const ly = Math.min(Math.max(origin.py + 4, 4), h - 14);

    ctx.fillStyle = dark ? 'rgba(156,163,175,0.85)' : 'rgba(115,115,115,0.85)';
    ctx.font = '10.5px system-ui,sans-serif';

    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    for (let x = x0; x <= V.xMax + xStep * 0.01; x += xStep) {
      if (Math.abs(x) < xStep * 0.01) continue;
      const { px } = this.toPixel(x, 0, w, h, V);
      ctx.fillText(this.formatNumber(x), px, ly);
    }

    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    for (let y = y0; y <= V.yMax + yStep * 0.01; y += yStep) {
      if (Math.abs(y) < yStep * 0.01) continue;
      const { py } = this.toPixel(0, y, w, h, V);
      ctx.fillText(this.formatNumber(y), lx, py);
    }
  }

  /**
   * Draws primary X and Y axes with arrow markers and coordinate labels.
   */
  drawAxes(ctx, w, h, V, dark) {
    const o = this.toPixel(0, 0, w, h, V);
    ctx.strokeStyle = dark ? 'rgba(255,255,255,0.28)' : 'rgba(0,0,0,0.32)';
    ctx.lineWidth = 1.5;

    // X Axis
    ctx.beginPath();
    ctx.moveTo(0, o.py);
    ctx.lineTo(w, o.py);
    ctx.stroke();

    // Y Axis
    ctx.beginPath();
    ctx.moveTo(o.px, 0);
    ctx.lineTo(o.px, h);
    ctx.stroke();

    // Axis arrows
    const s = 5;
    ctx.fillStyle = ctx.strokeStyle;

    // X arrow
    ctx.beginPath();
    ctx.moveTo(w - 1, o.py);
    ctx.lineTo(w - s * 2, o.py - s);
    ctx.lineTo(w - s * 2, o.py + s);
    ctx.closePath();
    ctx.fill();

    // Y arrow
    ctx.beginPath();
    ctx.moveTo(o.px, 1);
    ctx.lineTo(o.px - s, s * 2);
    ctx.lineTo(o.px + s, s * 2);
    ctx.closePath();
    ctx.fill();

    // Axis labels
    ctx.fillStyle = dark ? 'rgba(163,163,163,0.9)' : 'rgba(74,74,74,0.9)';
    ctx.font = 'bold 12px system-ui,sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('x', w - 14, o.py - 8);
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('y', o.px + 6, 4);
  }

  /**
   * Plots curves for all active equations with discontinuity detection.
   */
  drawCurves(ctx, w, h, V, equations, lineWidth) {
    const steps = Math.ceil(w * 2.5);
    const dx = (V.xMax - V.xMin) / steps;
    const yRange = V.yMax - V.yMin;

    for (const eq of equations) {
      if (!eq.enabled) continue;

      for (const fn of eq.fns) {
        ctx.strokeStyle = eq.color;
        ctx.lineWidth = lineWidth;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        ctx.beginPath();

        let penDown = false;
        let prevY = null;

        for (let i = 0; i <= steps; i++) {
          const x = V.xMin + i * dx;
          let y;
          try {
            y = fn(x);
          } catch (_) {
            penDown = false;
            prevY = null;
            continue;
          }

          if (!isFinite(y) || isNaN(y)) {
            penDown = false;
            prevY = null;
            continue;
          }

          // Discontinuity guard (e.g. asymptotes for tan(x), 1/x)
          if (prevY !== null && Math.abs(y - prevY) > yRange * 2.5) {
            penDown = false;
          }
          prevY = y;

          const { px, py } = this.toPixel(x, y, w, h, V);
          if (!penDown) {
            ctx.moveTo(px, py);
            penDown = true;
          } else {
            ctx.lineTo(px, py);
          }
        }
        ctx.stroke();
      }
    }
  }

  /**
   * Renders the complete scene on the main canvas.
   */
  drawMain(V, equations, settings) {
    if (!this.mainCtx) return;
    const w = this.getMainWidth();
    const h = this.getMainHeight();
    const dark = this.isDark();

    this.mainCtx.clearRect(0, 0, w, h);

    // Background
    this.mainCtx.fillStyle = dark ? '#000000' : '#ffffff';
    this.mainCtx.fillRect(0, 0, w, h);

    if (settings.showGrid) {
      this.drawGrid(this.mainCtx, w, h, V, dark, settings.gridSizeMul, 10, 8);
    }
    this.drawAxes(this.mainCtx, w, h, V, dark);
    this.drawCurves(this.mainCtx, w, h, V, equations, settings.lineWidth);
  }

  /**
   * Renders the complete scene on the fullscreen canvas.
   */
  drawFullscreen(V, equations, settings) {
    if (!this.fsCtx) return;
    const w = this.getFsWidth();
    const h = this.getFsHeight();
    const dark = this.isDark();

    this.fsCtx.clearRect(0, 0, w, h);
    this.fsCtx.fillStyle = dark ? '#000000' : '#ffffff';
    this.fsCtx.fillRect(0, 0, w, h);

    if (settings.showGrid) {
      this.drawGrid(this.fsCtx, w, h, V, dark, settings.gridSizeMul, 12, 9);
    }
    this.drawAxes(this.fsCtx, w, h, V, dark);
    this.drawCurves(this.fsCtx, w, h, V, equations, settings.lineWidth + 0.5);
  }

  /**
   * Exports either the main canvas or fullscreen canvas to a PNG image download.
   * @param {boolean} fromFs
   * @param {string} [filename='graph.png']
   */
  exportToPng(fromFs = false, filename = 'graph.png') {
    const src = fromFs ? this.fsCanvas : this.mainCanvas;
    if (!src) return;
    const link = document.createElement('a');
    link.download = filename;
    link.href = src.toDataURL('image/png');
    link.click();
  }
}
