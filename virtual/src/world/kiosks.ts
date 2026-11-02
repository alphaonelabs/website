import * as THREE from "three";
import {
  activityDestination,
  isLive,
  isWaitlist,
  typeLabel,
  type ActivityGroup,
  type CampusActivity,
} from "../data/activities";
import type { Arrival, Box2 } from "../types";
import { footprint, yawToward, type Interactable, type LazySign, type Row, type Slot } from "./campus";
import { kioskSignTexture, rowSignTexture } from "./text";
import { materials } from "./theme";

export interface KioskPlacement {
  activity: CampusActivity;
  slot: Slot;
}

interface HeaderPlacement {
  slot: Slot;
  label: string;
  count: string;
}

/** Packs groups into rows; each group starts on a fresh row and gets a header sign. */
export function layoutRows(groups: ActivityGroup[], rows: Row[]): { kiosks: KioskPlacement[]; headers: HeaderPlacement[] } {
  const kiosks: KioskPlacement[] = [];
  const headers: HeaderPlacement[] = [];
  let r = 0;
  for (const group of groups) {
    let i = 0;
    let part = 0;
    while (i < group.items.length && r < rows.length) {
      const row = rows[r++];
      const take = group.items.slice(i, i + row.slots.length);
      take.forEach((activity, k) => kiosks.push({ activity, slot: row.slots[k] }));
      headers.push({
        slot: row.header,
        label: part === 0 ? group.label : `${group.label} (cont.)`,
        count: `${group.items.length} ${group.items.length === 1 ? "activity" : "activities"}`,
      });
      i += take.length;
      part++;
    }
  }
  return { kiosks, headers };
}

export interface KioskBuild {
  interactables: Interactable[];
  colliders: Box2[];
  signs: LazySign[];
  arrivals: Map<string, Arrival>;
}

const BODY_W = 1.3;
const BODY_H = 2.5;
const BODY_D = 0.3;
const SIGN = 1.16;

function priceLabel(a: CampusActivity): string {
  if (isWaitlist(a)) return "WAITLIST";
  if (a.priceCents > 0) return `$${(a.priceCents / 100).toFixed(a.priceCents % 100 ? 2 : 0)}`;
  return "FREE";
}

/** Instanced kiosk bodies; only the sign faces are individual meshes. */
export function buildKiosks(scene: THREE.Scene, kiosks: KioskPlacement[], headers: HeaderPlacement[]): KioskBuild {
  const out: KioskBuild = { interactables: [], colliders: [], signs: [], arrivals: new Map() };
  const count = kiosks.length + headers.length;
  if (count === 0) return out;

  const body = new THREE.InstancedMesh(new THREE.BoxGeometry(BODY_W, BODY_H, BODY_D), materials.kiosk, count);
  const base = new THREE.InstancedMesh(new THREE.BoxGeometry(BODY_W + 0.3, 0.12, 0.7), materials.kiosk, count);
  const cap = new THREE.InstancedMesh(new THREE.BoxGeometry(BODY_W + 0.06, 0.08, BODY_D + 0.06), materials.trim, count);
  for (const m of [body, base, cap]) {
    m.castShadow = true;
    m.receiveShadow = true;
  }

  const signGeom = new THREE.PlaneGeometry(SIGN, SIGN);
  const headerGeom = new THREE.PlaneGeometry(BODY_W - 0.1, (BODY_W - 0.1) / 2);
  const mat = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const up = new THREE.Vector3(0, 1, 0);
  const one = new THREE.Vector3(1, 1, 1);
  const p = new THREE.Vector3();

  const place = (index: number, slot: Slot, heightScale: number): void => {
    q.setFromAxisAngle(up, slot.rot);
    const h = BODY_H * heightScale;
    mat.compose(p.set(slot.x, 0.12 + h / 2, slot.z), q, new THREE.Vector3(1, heightScale, 1));
    body.setMatrixAt(index, mat);
    mat.compose(p.set(slot.x, 0.06, slot.z), q, one);
    base.setMatrixAt(index, mat);
    mat.compose(p.set(slot.x, 0.12 + h + 0.04, slot.z), q, one);
    cap.setMatrixAt(index, mat);
  };

  kiosks.forEach(({ activity, slot }, i) => {
    place(i, slot, 1);
    const fx = Math.sin(slot.rot);
    const fz = Math.cos(slot.rot);
    const sign = new THREE.Mesh(signGeom, materials.signBlank);
    sign.position.set(slot.x + fx * (BODY_D / 2 + 0.01), 1.95, slot.z + fz * (BODY_D / 2 + 0.01));
    sign.rotation.y = slot.rot;
    scene.add(sign);

    const info = {
      eyebrow: `${typeLabel(activity.type)}${activity.format === "self_paced" ? " · self-paced" : ""}`.toUpperCase(),
      title: activity.title,
      footer: activity.hostName ? `By ${activity.hostName}`.slice(0, 26) : "Alpha One Labs",
      badge: priceLabel(activity),
      live: isLive(activity),
    };
    out.signs.push({ mesh: sign, x: slot.x, z: slot.z, make: () => kioskSignTexture(info) });
    out.colliders.push(footprint(slot.x, slot.z, BODY_W + 0.3, 0.7, slot.rot));
    out.interactables.push({ dest: activityDestination(activity), x: slot.x + fx * 1.3, z: slot.z + fz * 1.3, radius: 2.1 });
    const ax = slot.x + fx * 3.2;
    const az = slot.z + fz * 3.2;
    out.arrivals.set(activity.id, { x: ax, z: az, yaw: yawToward(ax, az, slot.x, slot.z) });
  });

  headers.forEach(({ slot, label, count: countText }, j) => {
    place(kiosks.length + j, slot, 0.86);
    const fx = Math.sin(slot.rot);
    const fz = Math.cos(slot.rot);
    const sign = new THREE.Mesh(headerGeom, materials.signBlank);
    sign.position.set(slot.x + fx * (BODY_D / 2 + 0.01), 1.75, slot.z + fz * (BODY_D / 2 + 0.01));
    sign.rotation.y = slot.rot;
    scene.add(sign);
    out.signs.push({ mesh: sign, x: slot.x, z: slot.z, make: () => rowSignTexture(label, countText), eager: true });
    out.colliders.push(footprint(slot.x, slot.z, BODY_W + 0.3, 0.7, slot.rot));
  });

  for (const m of [body, base, cap]) {
    m.instanceMatrix.needsUpdate = true;
    m.computeBoundingSphere();
    scene.add(m);
  }
  return out;
}
