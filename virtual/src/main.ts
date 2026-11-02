import * as THREE from "three";
import { isAuthenticated, logout } from "./auth";
import {
  eyebrowFor,
  fetchActivities,
  isWaitlist,
  selectForCampus,
  type CampusActivity,
} from "./data/activities";
import type { Arrival, Destination } from "./types";
import { Overlay, type SearchEntry } from "./ui/overlay";
import { buildCampus, type Interactable, type LazySign } from "./world/campus";
import { FirstPersonControls } from "./world/controls";
import { Interactions } from "./world/interact";
import { buildKiosks, layoutRows } from "./world/kiosks";
import { createScene } from "./world/scene";
import { loadBrandFont, setMaxAnisotropy } from "./world/text";
import { applyTheme, detectTheme, watchTheme } from "./world/theme";

const canvas = document.querySelector<HTMLCanvasElement>("#app")!;
const { scene, camera, renderer, hemi, sun, grid } = createScene(canvas);
setMaxAnisotropy(renderer.capabilities.getMaxAnisotropy());

const themeTargets = { scene, hemi, sun, grid };
applyTheme(detectTheme(), themeTargets);
watchTheme((theme) => applyTheme(theme, themeTargets));

const campus = buildCampus(scene);
const controls = new FirstPersonControls(camera, canvas);
controls.colliders = campus.colliders;
controls.teleport(campus.spawn);
const interactions = new Interactions(campus.interactables);
const overlay = new Overlay();

// ── Lazy sign textures ──────────────────────────────────────────────────
const pendingSigns: LazySign[] = [...campus.signs];
let fontsReady = false;
void loadBrandFont().then(() => {
  fontsReady = true;
});

const SIGN_DRAW_DISTANCE = 34;
function drawSigns(): void {
  if (!fontsReady || pendingSigns.length === 0) return;
  const { x, z } = camera.position;
  const ready = pendingSigns
    .map((sign) => ({ sign, d: Math.hypot(sign.x - x, sign.z - z) }))
    .filter(({ sign, d }) => sign.eager || d < SIGN_DRAW_DISTANCE)
    .sort((a, b) => Number(Boolean(b.sign.eager)) - Number(Boolean(a.sign.eager)) || a.d - b.d)
    .slice(0, 3);
  for (const { sign } of ready) {
    const material = new THREE.MeshBasicMaterial({ map: sign.make() });
    for (const mesh of Array.isArray(sign.mesh) ? sign.mesh : [sign.mesh]) mesh.material = material;
    pendingSigns.splice(pendingSigns.indexOf(sign), 1);
  }
}

// ── Modes: menu (overlay), locked (pointer lock), free (drag / touch) ──────
type Mode = "menu" | "locked" | "free";
let mode: Mode = "menu";
let modeBeforePanel: Mode = "menu";
const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
let pointerLockUsable = !coarsePointer && "requestPointerLock" in canvas;

function setMode(next: Mode): void {
  mode = next;
  controls.freeMode = next === "free";
  if (next === "menu") overlay.showBlocker();
  else overlay.hideBlocker(next);
}

async function enterWorld(): Promise<void> {
  if (pointerLockUsable) {
    overlay.hideBlocker("locked");
    if (await controls.lock()) return; // pointerlockchange sets the mode
    // Automation, iframes without permission, some browsers: fall back for this session.
    pointerLockUsable = false;
  }
  setMode("free");
}

document.addEventListener("pointerlockchange", () => {
  if (controls.isLocked) {
    setMode("locked");
  } else if (mode === "locked" && !overlay.isPanelOpen()) {
    setMode("menu");
  }
});

function travel(arrival: Arrival): void {
  controls.teleport(arrival);
  interactions.resetTriggers(arrival.x, arrival.z);
  prevX = arrival.x;
  prevZ = arrival.z;
  void enterWorld();
}

function openPanel(dest: Destination): void {
  if (overlay.isPanelOpen()) return;
  modeBeforePanel = mode;
  overlay.showPanel(dest);
  controls.enabled = false;
  if (controls.isLocked) controls.unlock();
}

async function closePanel(): Promise<void> {
  overlay.hidePanel();
  controls.enabled = true;
  if (modeBeforePanel === "locked") {
    overlay.hideBlocker("locked");
    if (!(await controls.lock())) setMode("menu");
  } else {
    setMode(modeBeforePanel);
  }
}

overlay.onEnter(() => void enterWorld());
overlay.onMenu(() => setMode("menu"));
overlay.onPanelClose(() => void closePanel());
overlay.onTouchMove((key, pressed) => controls.setMove(key, pressed));
overlay.onPromptClick(() => {
  if (activeTarget) openPanel(activeTarget.dest);
});

document.addEventListener("keydown", (event) => {
  if (overlay.isPanelOpen()) {
    if (event.code === "Escape") {
      event.preventDefault();
      void closePanel();
    }
    return;
  }
  if (mode === "menu") return;
  if (event.code === "KeyE" && activeTarget) {
    event.preventDefault();
    openPanel(activeTarget.dest);
  } else if (event.code === "Escape" && mode === "free") {
    setMode("menu");
  }
});

overlay.renderZones(
  campus.zones.map((zone) => ({
    label: zone.label,
    blurb: zone.dest.eyebrow,
    onPick: () => travel(zone.arrival),
  })),
);

// Anyone can explore as a guest; signing in only matters for the learn activities.
if (isAuthenticated()) {
  overlay.onLogout(() => logout());
  overlay.showLogout();
} else {
  overlay.showSignIn(() => {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/login.html?next=${next}`;
  });
}

// ── Real activities from learn.alphaonelabs.com ──────────────────────────
void fetchActivities().then(({ activities, source }) => {
  const { hall, study } = selectForCampus(activities);
  const hallLayout = layoutRows(hall, campus.hallRows);
  const studyLayout = layoutRows(study.length ? [{ label: "Live study groups", items: study }] : [], campus.studyRows);
  const built = buildKiosks(scene, [...studyLayout.kiosks, ...hallLayout.kiosks], [...studyLayout.headers, ...hallLayout.headers]);

  interactions.add(built.interactables);
  controls.colliders.push(...built.colliders);
  pendingSigns.push(...built.signs);
  renderer.shadowMap.needsUpdate = true;

  const placed: CampusActivity[] = [...studyLayout.kiosks, ...hallLayout.kiosks].map((k) => k.activity);
  const entries: SearchEntry[] = placed.map((a) => {
    const where = a.type === "study_group" ? "Study Groups" : "Activities Hall";
    const meta = `${eyebrowFor(a)} · ${where}`;
    return {
      title: a.title,
      meta,
      haystack: `${a.title} ${meta} ${a.hostName} ${a.description}`.toLowerCase(),
      onPick: () => {
        const arrival = built.arrivals.get(a.id);
        if (arrival) travel(arrival);
      },
    };
  });
  overlay.setSearchEntries(entries);

  const waitlisted = placed.filter(isWaitlist).length;
  overlay.setStatus(
    source === "live"
      ? `${placed.length} of ${activities.length} activities from learn.alphaonelabs.com on campus · ${placed.length - waitlisted} open, ${waitlisted} waitlist`
      : `Couldn't reach learn.alphaonelabs.com — showing ${placed.length} built-in activities.`,
  );
});

// ── Main loop ────────────────────────────────────────────────────────────
let activeTarget: Interactable | null = null;
let prevX = camera.position.x;
let prevZ = camera.position.z;
const clock = new THREE.Clock();

function animate(): void {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();
  controls.update(delta);
  drawSigns();

  if (mode !== "menu" && !overlay.isPanelOpen()) {
    const { x, z } = camera.position;
    const entered = interactions.checkTriggers(prevX, prevZ, x, z);
    activeTarget = interactions.nearest(x, z);
    if (entered) {
      openPanel(entered.dest);
    } else if (activeTarget) {
      overlay.showPrompt(activeTarget.dest);
    } else {
      overlay.hidePrompt();
    }
  }
  prevX = camera.position.x;
  prevZ = camera.position.z;

  renderer.render(scene, camera);
}

animate();
