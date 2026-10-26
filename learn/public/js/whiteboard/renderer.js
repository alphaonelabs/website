/**
 * Canvas 2D rendering engine for the Whiteboard.
 */

export class WhiteboardRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.images = []; // [{ img, bounds }]
    this.selectedImageIndex = -1;
    this.lastEvents = [];
  }

  setImages(images) {
    this.images = images || [];
  }

  addImage(img, bounds) {
    this.images.push({ img, bounds });
    this.selectedImageIndex = this.images.length - 1;
    return this.selectedImageIndex;
  }

  removeImage(index) {
    this.images.splice(index, 1);
    this.selectedImageIndex = -1;
  }

  pointFromEvent(event) {
    const rect = this.canvas.getBoundingClientRect();
    const touch = event.touches && event.touches[0] ? event.touches[0] : event;
    return {
      x: Math.max(0, Math.min(1, (touch.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (touch.clientY - rect.top) / rect.height))
    };
  }

  px(point) {
    return {
      x: point.x * this.canvas.width,
      y: point.y * this.canvas.height
    };
  }

  setStyle(event) {
    const ctx = this.ctx;
    ctx.lineWidth = Number(event.size || 4);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = event.color || '#0f766e';
    ctx.fillStyle = event.color || '#0f766e';
    ctx.globalAlpha = Number(event.alpha || 1);
    ctx.globalCompositeOperation = event.mode === 'eraser' ? 'destination-out' : 'source-over';
  }

  drawArrow(from, to) {
    const ctx = this.ctx;
    const headlen = Math.max(10, Number(ctx.lineWidth || 4) * 3);
    const angle = Math.atan2(to.y - from.y, to.x - from.x);
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(to.x, to.y);
    ctx.lineTo(to.x - headlen * Math.cos(angle - Math.PI / 6), to.y - headlen * Math.sin(angle - Math.PI / 6));
    ctx.moveTo(to.x, to.y);
    ctx.lineTo(to.x - headlen * Math.cos(angle + Math.PI / 6), to.y - headlen * Math.sin(angle + Math.PI / 6));
    ctx.stroke();
  }

  drawEvent(event) {
    if (!event || !event.from) return;
    const kind = event.kind || 'stroke';
    const from = this.px(event.from);
    const to = this.px(event.to || event.from);
    const ctx = this.ctx;

    ctx.save();
    this.setStyle(event);

    if (kind === 'stroke' || kind === 'line') {
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    } else if (kind === 'rectangle') {
      ctx.strokeRect(from.x, from.y, to.x - from.x, to.y - from.y);
    } else if (kind === 'circle') {
      const radius = Math.hypot(to.x - from.x, to.y - from.y);
      ctx.beginPath();
      ctx.arc(from.x, from.y, radius, 0, Math.PI * 2);
      ctx.stroke();
    } else if (kind === 'arrow') {
      this.drawArrow(from, to);
    } else if (kind === 'text') {
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      ctx.font = Math.max(12, Number(event.size || 4) * 5) + 'px sans-serif';
      ctx.fillText(event.text || '', from.x, from.y);
    }
    ctx.restore();
  }

  drawBackground(drawHandles = true) {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    for (let i = 0; i < this.images.length; i++) {
      const { img, bounds } = this.images[i];
      const b = bounds || this.defaultBounds(img);
      this.ctx.drawImage(img, b.x, b.y, b.width, b.height);
    }
    if (drawHandles && this.selectedImageIndex >= 0 && this.images[this.selectedImageIndex]) {
      this.drawImageHandles(this.images[this.selectedImageIndex].bounds);
    }
  }

  defaultBounds(img) {
    const w = img.naturalWidth || img.width || 400;
    const h = img.naturalHeight || img.height || 300;
    const ar = h / w;
    let bw = Math.min(this.canvas.width * 0.36, w);
    let bh = bw * ar;
    if (bh > this.canvas.height * 0.8) {
      bh = this.canvas.height * 0.8;
      bw = bh / ar;
    }
    return {
      x: Math.round((this.canvas.width - bw) / 2),
      y: Math.round((this.canvas.height - bh) / 2),
      width: bw,
      height: bh
    };
  }

  drawImageHandles(bounds) {
    if (!bounds) return;
    const ctx = this.ctx;
    ctx.save();

    // Subtle dashed bounding box
    ctx.strokeStyle = '#0f766e';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 4]);
    ctx.strokeRect(bounds.x, bounds.y, bounds.width, bounds.height);
    ctx.setLineDash([]);

    // Move badge at top center
    const pillW = 60;
    const pillH = 20;
    const pillX = bounds.x + bounds.width / 2 - pillW / 2;
    const pillY = bounds.y - pillH - 6;
    if (pillY >= 4) {
      ctx.fillStyle = '#0f766e';
      ctx.beginPath();
      if (typeof ctx.roundRect === 'function') {
        ctx.roundRect(pillX, pillY, pillW, pillH, 6);
      } else {
        ctx.rect(pillX, pillY, pillW, pillH);
      }
      ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('✥ Move', pillX + pillW / 2, pillY + pillH / 2);
    }

    // Circular handle renderer
    const drawHandle = (hx, hy) => {
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#0f766e';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(hx, hy, 5.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    };

    // 4 Corner handles
    drawHandle(bounds.x, bounds.y); // NW
    drawHandle(bounds.x + bounds.width, bounds.y); // NE
    drawHandle(bounds.x + bounds.width, bounds.y + bounds.height); // SE
    drawHandle(bounds.x, bounds.y + bounds.height); // SW

    // 4 Edge handles
    drawHandle(bounds.x + bounds.width / 2, bounds.y); // N
    drawHandle(bounds.x + bounds.width / 2, bounds.y + bounds.height); // S
    drawHandle(bounds.x, bounds.y + bounds.height / 2); // W
    drawHandle(bounds.x + bounds.width, bounds.y + bounds.height / 2); // E

    ctx.restore();
  }

  redrawAll(events = [], extraEvent = null, drawHandles = true) {
    this.lastEvents = events;
    this.drawBackground(drawHandles);
    for (let i = 0; i < events.length; i++) {
      this.drawEvent(events[i]);
    }
    if (extraEvent) {
      this.drawEvent(extraEvent);
    }
  }

  exportToPng(filenamePrefix = 'whiteboard') {
    const offscreen = document.createElement('canvas');
    offscreen.width = this.canvas.width;
    offscreen.height = this.canvas.height;
    const offCtx = offscreen.getContext('2d');
    offCtx.fillStyle = '#f8f9fa';
    offCtx.fillRect(0, 0, offscreen.width, offscreen.height);

    // Render cleanly without handles for export
    this.redrawAll(this.lastEvents || [], null, false);
    offCtx.drawImage(this.canvas, 0, 0);

    // Restore interactive handle view
    this.redrawAll(this.lastEvents || [], null, true);

    const safeName = filenamePrefix.replace(/[^A-Za-z0-9_-]+/g, '-');
    const link = document.createElement('a');
    link.href = offscreen.toDataURL('image/png');
    link.download = `${safeName}-whiteboard.png`;
    link.click();
  }
}
