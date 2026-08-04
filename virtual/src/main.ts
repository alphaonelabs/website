import * as THREE from "three";
import { logout, requireAuth } from "./auth";
import { activities } from "./data/activities";
import { Overlay } from "./ui/overlay";
import { FirstPersonControls } from "./world/controls";
import { createPortals, findNearestPortal, type Portal } from "./world/portals";
import { createScene } from "./world/scene";

if (!requireAuth()) {
  throw new Error("redirecting to login");
}

const canvas = document.querySelector<HTMLCanvasElement>("#app")!;
const { scene, camera, renderer } = createScene(canvas);
const controls = new FirstPersonControls(camera, canvas);
const portals: Portal[] = createPortals(scene, activities);
const overlay = new Overlay();

let activePortal: Portal | null = null;

overlay.onBlockerClick(() => controls.lock());

document.addEventListener("pointerlockchange", () => {
  if (controls.isLocked) {
    overlay.hideBlocker();
  } else if (!overlay.isPanelOpen()) {
    overlay.showBlocker();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.code === "KeyE" && activePortal && !overlay.isPanelOpen()) {
    controls.unlock();
    overlay.showPanel(activePortal.activity);
  } else if (event.code === "Escape" && overlay.isPanelOpen()) {
    overlay.hidePanel();
  }
});

overlay.onPanelClose(() => {
  overlay.hidePanel();
  controls.lock();
});

overlay.onLogout(() => logout());
overlay.showLogout();

const clock = new THREE.Clock();

function animate(): void {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();

  controls.update(delta);

  if (!overlay.isPanelOpen()) {
    const nearest = findNearestPortal(portals, camera.position);
    activePortal = nearest;
    if (nearest) {
      overlay.showPrompt(nearest.activity);
    } else {
      overlay.hidePrompt();
    }
  }

  renderer.render(scene, camera);
}

animate();
