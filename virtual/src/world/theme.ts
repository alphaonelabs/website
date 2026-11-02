import * as THREE from "three";

export type ThemeName = "light" | "dark";

export const GOLD = 0xd4af37;
export const GOLD_DARK = 0xe1b746;

interface Palette {
  sky: number;
  ground: number;
  grid: number;
  plaza: number;
  path: number;
  building: number;
  edge: number;
  trim: number;
  trace: number;
  kiosk: number;
  doorway: number;
  hemiSky: number;
  hemiGround: number;
  hemi: number;
  sun: number;
  fogNear: number;
  fogFar: number;
}

const PALETTES: Record<ThemeName, Palette> = {
  light: {
    sky: 0xeeeeec,
    ground: 0xe4e4e1,
    grid: 0xd3d3cf,
    plaza: 0xf8f8f6,
    path: 0xcfcfca,
    building: 0xffffff,
    edge: 0x0a0a0a,
    trim: GOLD,
    trace: 0xc29f2c,
    kiosk: 0x111111,
    doorway: 0x111111,
    hemiSky: 0xffffff,
    hemiGround: 0xb9b9b4,
    hemi: 1.9,
    sun: 1.7,
    fogNear: 45,
    fogFar: 150,
  },
  dark: {
    sky: 0x0a0a0a,
    ground: 0x141414,
    grid: 0x1f1f1f,
    plaza: 0x1c1c1c,
    path: 0x222222,
    building: 0x232323,
    edge: 0x4a4a4a,
    trim: GOLD_DARK,
    trace: GOLD_DARK,
    kiosk: 0x050505,
    doorway: 0x000000,
    hemiSky: 0xd8d8e0,
    hemiGround: 0x101010,
    hemi: 1.0,
    sun: 1.2,
    fogNear: 35,
    fogFar: 130,
  },
};

/** Follows the site's theme switch: explicit attribute first, then the OS. */
export function detectTheme(): ThemeName {
  const attr = document.documentElement.getAttribute("data-a1-theme");
  if (attr === "light" || attr === "dark") return attr;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function watchTheme(onChange: (theme: ThemeName) => void): void {
  let current = detectTheme();
  const check = (): void => {
    const next = detectTheme();
    if (next !== current) {
      current = next;
      onChange(next);
    }
  };
  new MutationObserver(check).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-a1-theme"],
  });
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", check);
}

/** Shared materials so the whole campus re-themes by recoloring a handful of objects. */
export const materials = {
  ground: new THREE.MeshStandardMaterial({ roughness: 1 }),
  plaza: new THREE.MeshStandardMaterial({ roughness: 0.95 }),
  path: new THREE.MeshStandardMaterial({ roughness: 1 }),
  building: new THREE.MeshStandardMaterial({ roughness: 0.85 }),
  edge: new THREE.LineBasicMaterial(),
  trim: new THREE.MeshStandardMaterial({ roughness: 0.4, metalness: 0.55 }),
  trace: new THREE.MeshBasicMaterial({ polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }),
  kiosk: new THREE.MeshStandardMaterial({ roughness: 0.6 }),
  doorway: new THREE.MeshBasicMaterial(),
  signBlank: new THREE.MeshBasicMaterial({ color: 0x0a0a0a }),
};

export interface ThemeTargets {
  scene: THREE.Scene;
  hemi: THREE.HemisphereLight;
  sun: THREE.DirectionalLight;
  grid: THREE.LineSegments;
}

export function applyTheme(theme: ThemeName, t: ThemeTargets): void {
  const p = PALETTES[theme];
  const sky = new THREE.Color(p.sky);
  t.scene.background = sky;
  t.scene.fog = new THREE.Fog(sky, p.fogNear, p.fogFar);
  t.hemi.color.setHex(p.hemiSky);
  t.hemi.groundColor.setHex(p.hemiGround);
  t.hemi.intensity = p.hemi;
  t.sun.intensity = p.sun;
  (t.grid.material as THREE.LineBasicMaterial).color.setHex(p.grid);

  materials.ground.color.setHex(p.ground);
  materials.plaza.color.setHex(p.plaza);
  materials.path.color.setHex(p.path);
  materials.building.color.setHex(p.building);
  materials.edge.color.setHex(p.edge);
  materials.trim.color.setHex(p.trim);
  materials.trace.color.setHex(p.trace);
  materials.kiosk.color.setHex(p.kiosk);
  materials.doorway.color.setHex(p.doorway);
}
