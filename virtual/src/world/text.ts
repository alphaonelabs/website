import * as THREE from "three";

/** Brand signage face; the fallbacks keep the condensed look if the webfont fails. */
const DISPLAY = '"Barlow Condensed", "Arial Narrow", Impact, sans-serif';
const GOLD = "#D4AF37";
const INK = "#0a0a0a";

let maxAnisotropy = 4;
export function setMaxAnisotropy(value: number): void {
  maxAnisotropy = Math.min(8, Math.max(1, value));
}

/** Resolves once Barlow Condensed is usable in canvas, or after a short timeout. */
export function loadBrandFont(timeoutMs = 3000): Promise<void> {
  if (!("fonts" in document)) return Promise.resolve();
  const loads = Promise.all(
    ["700", "800", "900"].map((w) => document.fonts.load(`${w} 48px "Barlow Condensed"`)),
  ).then(() => undefined);
  const timeout = new Promise<void>((resolve) => window.setTimeout(resolve, timeoutMs));
  return Promise.race([loads, timeout]).catch(() => undefined);
}

function makeCanvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  return [canvas, canvas.getContext("2d")!];
}

function toTexture(canvas: HTMLCanvasElement): THREE.CanvasTexture {
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = maxAnisotropy;
  return tex;
}

function font(weight: number, size: number): string {
  return `${weight} ${size}px ${DISPLAY}`;
}

/** Greedy word wrap; the final line is ellipsized when text overflows maxLines. */
function wrap(ctx: CanvasRenderingContext2D, text: string, maxWidth: number, maxLines: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  let i = 0;
  for (; i < words.length; i++) {
    const test = line ? `${line} ${words[i]}` : words[i];
    if (ctx.measureText(test).width <= maxWidth || !line) {
      line = test;
    } else {
      lines.push(line);
      line = words[i];
      if (lines.length === maxLines) break;
    }
  }
  if (lines.length < maxLines && line) {
    lines.push(line);
    line = "";
    i = words.length;
  }
  if (i < words.length || line) {
    let last = lines[maxLines - 1] ?? "";
    while (last && ctx.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1);
    lines[maxLines - 1] = `${last.trimEnd()}…`;
  }
  // A single overlong word: shrink-by-truncation so it never spills off the sign.
  return lines.map((l) => {
    let out = l;
    while (out.length > 1 && ctx.measureText(out).width > maxWidth) out = `${out.slice(0, -2)}…`;
    return out;
  });
}

/** Wide building sign: black panel, gold rule, white condensed title. */
export function buildingSignTexture(title: string, subtitle: string): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(1024, 256);
  ctx.fillStyle = INK;
  ctx.fillRect(0, 0, 1024, 256);
  ctx.strokeStyle = GOLD;
  ctx.lineWidth = 6;
  ctx.strokeRect(10, 10, 1004, 236);
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "#ffffff";
  let size = 132;
  ctx.font = font(800, size);
  while (ctx.measureText(title.toUpperCase()).width > 940 && size > 60) {
    size -= 6;
    ctx.font = font(800, size);
  }
  ctx.fillText(title.toUpperCase(), 512, 160);
  ctx.fillStyle = GOLD;
  ctx.fillRect(412, 182, 200, 4);
  ctx.font = font(700, 34);
  ctx.fillText(subtitle.toUpperCase().split("").join(" "), 512, 228);
  return toTexture(canvas);
}

export interface KioskSignInfo {
  eyebrow: string;
  title: string;
  footer: string;
  badge?: string;
  live?: boolean;
}

/** Square kiosk face for one activity. */
export function kioskSignTexture(info: KioskSignInfo): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(512, 512);
  ctx.fillStyle = INK;
  ctx.fillRect(0, 0, 512, 512);
  ctx.fillStyle = GOLD;
  ctx.fillRect(0, 0, 512, 10);

  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
  ctx.font = font(700, 30);
  ctx.fillStyle = GOLD;
  ctx.fillText(info.eyebrow, 32, 66);

  if (info.live) {
    ctx.font = font(800, 30);
    const w = ctx.measureText("LIVE").width + 34;
    ctx.fillStyle = "#e11d2e";
    ctx.fillRect(512 - 32 - w, 38, w, 38);
    ctx.fillStyle = "#ffffff";
    ctx.fillText("LIVE", 512 - 32 - w + 17, 68);
  }

  ctx.fillStyle = "#ffffff";
  let size = 64;
  let lines: string[] = [];
  for (; size >= 44; size -= 6) {
    ctx.font = font(800, size);
    lines = wrap(ctx, info.title.toUpperCase(), 448, 4);
    if (!lines.some((l) => l.endsWith("…"))) break;
  }
  const lineHeight = size * 1.02;
  lines.forEach((l, i) => ctx.fillText(l, 32, 140 + lineHeight * 0.75 + i * lineHeight));

  ctx.fillStyle = "#2e2e2e";
  ctx.fillRect(32, 430, 448, 2);
  ctx.font = font(700, 28);
  ctx.fillStyle = "#a3a3a3";
  ctx.fillText(info.footer.toUpperCase(), 32, 476);

  if (info.badge) {
    ctx.font = font(800, 28);
    const w = ctx.measureText(info.badge).width + 28;
    ctx.strokeStyle = GOLD;
    ctx.lineWidth = 3;
    ctx.strokeRect(480 - w, 448, w, 40);
    ctx.fillStyle = GOLD;
    ctx.fillText(info.badge, 480 - w + 14, 477);
  }
  return toTexture(canvas);
}

/** Short row header sign ("COURSES & WORKSHOPS"). */
export function rowSignTexture(label: string, count: string): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(512, 256);
  ctx.fillStyle = GOLD;
  ctx.fillRect(0, 0, 512, 256);
  ctx.fillStyle = INK;
  ctx.textAlign = "left";
  ctx.font = font(700, 30);
  ctx.fillText(count.toUpperCase(), 28, 60);
  let size = 72;
  let lines: string[] = [];
  for (; size >= 48; size -= 6) {
    ctx.font = font(800, size);
    lines = wrap(ctx, label.toUpperCase(), 456, 2);
    if (!lines.some((l) => l.endsWith("…"))) break;
  }
  lines.forEach((l, i) => ctx.fillText(l, 28, 140 + i * size * 0.95));
  return toTexture(canvas);
}

/** The A1 mark for the plaza monument. */
export function monumentTexture(): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(512, 1024);
  ctx.fillStyle = INK;
  ctx.fillRect(0, 0, 512, 1024);
  ctx.strokeStyle = GOLD;
  ctx.lineWidth = 8;
  ctx.strokeRect(28, 28, 456, 968);
  ctx.textAlign = "center";
  ctx.fillStyle = GOLD;
  ctx.font = font(900, 330);
  ctx.fillText("A1", 256, 520);
  ctx.fillRect(176, 580, 160, 6);
  ctx.fillStyle = "#ffffff";
  ctx.font = font(800, 78);
  ctx.fillText("ALPHA ONE", 256, 700);
  ctx.fillText("LABS", 256, 780);
  ctx.fillStyle = "#a3a3a3";
  ctx.font = font(700, 34);
  ctx.fillText("VIRTUAL CAMPUS", 256, 900);
  return toTexture(canvas);
}

/** A board with some marker sketches, so it reads as a whiteboard from afar. */
export function whiteboardTexture(): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(1024, 512);
  ctx.fillStyle = "#fbfbfa";
  ctx.fillRect(0, 0, 1024, 512);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.fillStyle = INK;
  ctx.font = font(800, 72);
  ctx.fillText("WHITEBOARD", 48, 100);
  ctx.fillStyle = GOLD;
  ctx.fillRect(48, 120, 220, 6);
  ctx.fillStyle = "#525252";
  ctx.font = font(700, 34);
  ctx.fillText("SKETCH · SOLVE · SHARE — PRESS E", 48, 172);

  // Circuit-ish diagram.
  ctx.strokeStyle = INK;
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(80, 300);
  ctx.lineTo(260, 300);
  ctx.lineTo(320, 240);
  ctx.lineTo(480, 240);
  ctx.moveTo(260, 300);
  ctx.lineTo(320, 360);
  ctx.lineTo(480, 360);
  ctx.stroke();
  ctx.strokeStyle = GOLD;
  ctx.lineWidth = 6;
  for (const [x, y] of [[80, 300], [480, 240], [480, 360]]) {
    ctx.beginPath();
    ctx.arc(x, y, 14, 0, Math.PI * 2);
    ctx.stroke();
  }
  // Equation and a graph.
  ctx.fillStyle = "#1d4ed8";
  ctx.font = "italic 600 54px Georgia, serif";
  ctx.fillText("f(x) = ax² + bx + c", 560, 280);
  ctx.strokeStyle = "#e11d2e";
  ctx.lineWidth = 5;
  ctx.beginPath();
  for (let i = 0; i <= 60; i++) {
    const x = 600 + i * 6;
    const t = (i - 30) / 30;
    const y = 460 - (1 - t * t) * 110;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.strokeStyle = INK;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(590, 470);
  ctx.lineTo(980, 470);
  ctx.moveTo(600, 480);
  ctx.lineTo(600, 330);
  ctx.stroke();
  return toTexture(canvas);
}
