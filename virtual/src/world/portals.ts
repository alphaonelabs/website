import * as THREE from "three";
import type { Activity } from "../types";

export interface Portal {
  activity: Activity;
  mesh: THREE.Object3D;
}

const INTERACT_DISTANCE = 3.5;

function createLabelSprite(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 128;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "rgba(10, 10, 10, 0.75)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.font = "bold 48px sans-serif";
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, depthTest: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(4, 1, 1);
  sprite.position.y = 2.6;
  return sprite;
}

export function createPortals(scene: THREE.Scene, activities: Activity[]): Portal[] {
  return activities.map((activity) => {
    const group = new THREE.Group();
    group.position.set(...activity.position);

    const kiosk = new THREE.Mesh(
      new THREE.CylinderGeometry(1, 1.2, 2, 8),
      new THREE.MeshStandardMaterial({
        color: activity.color,
        emissive: activity.color,
        emissiveIntensity: 0.3,
      }),
    );
    kiosk.position.y = 1;
    group.add(kiosk);
    group.add(createLabelSprite(activity.name));

    scene.add(group);
    return { activity, mesh: group };
  });
}

export function findNearestPortal(
  portals: Portal[],
  position: THREE.Vector3,
): Portal | null {
  let nearest: Portal | null = null;
  let nearestDistance = INTERACT_DISTANCE;

  for (const portal of portals) {
    const distance = position.distanceTo(portal.mesh.position);
    if (distance < nearestDistance) {
      nearest = portal;
      nearestDistance = distance;
    }
  }

  return nearest;
}
