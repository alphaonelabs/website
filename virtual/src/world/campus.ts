import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { learnUrl } from "../data/activities";
import type { Arrival, Box2, Destination } from "../types";
import { buildingSignTexture, monumentTexture, whiteboardTexture } from "./text";
import { materials } from "./theme";

/** Something the player can walk up to (E) or walk into (doorway trigger). */
export interface Interactable {
  dest: Destination;
  x: number;
  z: number;
  radius: number;
  /** Doorway volume; fires when the player enters it while moving inward. */
  trigger?: { box: Box2; inX: number; inZ: number };
}

export interface Zone {
  key: string;
  label: string;
  dest: Destination;
  arrival: Arrival;
}

/** A sign whose canvas texture is drawn on demand (fonts loaded, player nearby). */
export interface LazySign {
  mesh: THREE.Mesh | THREE.Mesh[];
  x: number;
  z: number;
  make: () => THREE.Texture;
  /** Building signs are drawn as soon as fonts are ready; kiosks only when close. */
  eager?: boolean;
}

export interface Slot {
  x: number;
  z: number;
  /** Rotation about Y; the kiosk's front faces (sin rot, cos rot). */
  rot: number;
}

export interface Row {
  header: Slot;
  slots: Slot[];
}

export interface Campus {
  zones: Zone[];
  interactables: Interactable[];
  colliders: Box2[];
  signs: LazySign[];
  hallRows: Row[];
  studyRows: Row[];
  spawn: Arrival;
}

const WALL_H = 3.2;
const WALL_T = 0.4;

/** Yaw that makes the camera at (px,pz) look at (tx,tz). */
export function yawToward(px: number, pz: number, tx: number, tz: number): number {
  return Math.atan2(px - tx, pz - tz);
}

function zoneDest(id: string, title: string, eyebrow: string, description: string, links: [string, string][]): Destination {
  return {
    id: `zone:${id}`,
    kind: "zone",
    eyebrow,
    title,
    description,
    links: links.map(([label, path]) => ({ label, url: learnUrl(path) })),
  };
}

const DEST = {
  plaza: zoneDest("plaza", "Alpha One Labs", "Central plaza", "Welcome to the virtual campus. Every building here mirrors a part of learn.alphaonelabs.com.", [
    ["About Alpha One Labs", "/about"],
    ["Browse all activities", "/activity"],
  ]),
  live: zoneDest("live", "Live Classroom", "Virtual classroom", "Drop into the lobby classroom: live video, chat, and a shared space with whoever is around right now.", [
    ["Join the lobby classroom", "/classroom_poc?autojoin=1&room=lobby"],
    ["Open the whiteboard", "/whiteboard"],
  ]),
  activities: zoneDest("activities", "Activities Hall", "Course catalog", "Every row in this hall is a real course, workshop or video lesson. Walk up to a kiosk to see it.", [
    ["Browse all activities", "/activity"],
  ]),
  study: zoneDest("study", "Study Groups", "Learn together", "Small peer groups that meet live. Walk up to a kiosk to join one or open its classroom.", [
    ["Browse study groups", "/activity?type=study_group"],
    ["Study group directory", "/study-groups"],
  ]),
  teach: zoneDest("teach", "Teach", "Share what you know", "Create a course, run a workshop, or host a study group on Alpha One Labs.", [
    ["Start teaching", "/teach"],
  ]),
  community: zoneDest("community", "Community", "Forum", "Ask questions, share projects and meet other learners and makers.", [
    ["Open the forum", "/forum"],
    ["Find a study group", "/study-groups"],
  ]),
  whiteboard: zoneDest("whiteboard", "Whiteboard", "Collaborate", "A shared whiteboard for sketching ideas and solving problems together.", [
    ["Open the whiteboard", "/whiteboard"],
    ["Join the lobby classroom", "/classroom_poc?autojoin=1&room=lobby"],
  ]),
};

/** Axis-aligned bounds of a w×d footprint centred at (x,z) and rotated by rot. */
export function footprint(x: number, z: number, w: number, d: number, rot: number): Box2 {
  const c = Math.abs(Math.cos(rot));
  const s = Math.abs(Math.sin(rot));
  const hw = (w * c + d * s) / 2;
  const hd = (w * s + d * c) / 2;
  return { minX: x - hw, maxX: x + hw, minZ: z - hd, maxZ: z + hd };
}

function withEdges(mesh: THREE.Mesh): THREE.Mesh {
  mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry), materials.edge));
  return mesh;
}

function box(w: number, h: number, d: number, mat: THREE.Material, x = 0, y = 0, z = 0): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function signPlane(w: number, h: number): THREE.Mesh {
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), materials.signBlank);
}

/**
 * Flat strip following a polyline, between lateral offsets a and b (meters,
 * left of travel direction positive). Corners are mitered so traces stay crisp.
 */
function strip(points: [number, number][], a: number, b: number, y: number): THREE.BufferGeometry {
  const offsetAt = (i: number, off: number): [number, number] => {
    const p = points[i];
    const prev = points[Math.max(0, i - 1)];
    const next = points[Math.min(points.length - 1, i + 1)];
    const n = (p0: [number, number], p1: [number, number]): [number, number] => {
      const dx = p1[0] - p0[0];
      const dz = p1[1] - p0[1];
      const len = Math.hypot(dx, dz) || 1;
      return [dz / len, -dx / len];
    };
    const n0 = i > 0 ? n(prev, p) : n(p, next);
    const n1 = i < points.length - 1 ? n(p, next) : n0;
    let mx = n0[0] + n1[0];
    let mz = n0[1] + n1[1];
    const ml = Math.hypot(mx, mz) || 1;
    mx /= ml;
    mz /= ml;
    const scale = off / Math.max(0.3, mx * n1[0] + mz * n1[1]);
    return [p[0] + mx * scale, p[1] + mz * scale];
  };
  const pos: number[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const a0 = offsetAt(i, a);
    const b0 = offsetAt(i, b);
    const a1 = offsetAt(i + 1, a);
    const b1 = offsetAt(i + 1, b);
    pos.push(a0[0], y, a0[1], b0[0], y, b0[1], a1[0], y, a1[1]);
    pos.push(b0[0], y, b0[1], b1[0], y, b1[1], a1[0], y, a1[1]);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  // Make every triangle face up regardless of winding.
  const arr = g.getAttribute("position").array as Float32Array;
  for (let t = 0; t < arr.length; t += 9) {
    const ux = arr[t + 3] - arr[t];
    const uz = arr[t + 5] - arr[t + 2];
    const vx = arr[t + 6] - arr[t];
    const vz = arr[t + 8] - arr[t + 2];
    if (uz * vx - ux * vz < 0) {
      for (let k = 0; k < 3; k++) {
        const tmp = arr[t + 3 + k];
        arr[t + 3 + k] = arr[t + 6 + k];
        arr[t + 6 + k] = tmp;
      }
    }
  }
  g.computeVertexNormals();
  return g;
}

function pad(x: number, z: number, y: number, r = 0.2): THREE.BufferGeometry {
  const g = new THREE.RingGeometry(r * 0.55, r, 20);
  g.rotateX(-Math.PI / 2);
  g.translate(x, y, z);
  return g;
}

interface BuildingSpec {
  key: keyof typeof DEST;
  x: number;
  z: number;
  w: number;
  d: number;
  h: number;
  rot: number;
  subtitle: string;
}

export function buildCampus(scene: THREE.Scene): Campus {
  const interactables: Interactable[] = [];
  const colliders: Box2[] = [];
  const signs: LazySign[] = [];
  const zones: Zone[] = [];
  const traceGeoms: THREE.BufferGeometry[] = [];
  const pathGeoms: THREE.BufferGeometry[] = [];

  // Ground and a faint engineering grid.
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), materials.ground);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  // ── Plaza with the A1 monument ─────────────────────────────────────────
  const plaza = new THREE.Mesh(new THREE.CircleGeometry(12, 72), materials.plaza);
  plaza.rotation.x = -Math.PI / 2;
  plaza.position.y = 0.012;
  plaza.receiveShadow = true;
  scene.add(plaza);
  for (const [r0, r1] of [[11.55, 11.65], [6.4, 6.46]]) {
    const ring = new THREE.RingGeometry(r0, r1, 96);
    ring.rotateX(-Math.PI / 2);
    ring.translate(0, 0.03, 0);
    traceGeoms.push(ring);
  }
  // Short radial traces with pads between the two rings.
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2 + Math.PI / 16;
    const c = Math.cos(a);
    const s = Math.sin(a);
    const mid = i % 2 ? 8.6 : 9.4;
    traceGeoms.push(strip([[c * 6.46, s * 6.46], [c * mid, s * mid]], -0.03, 0.03, 0.03));
    traceGeoms.push(pad(c * (mid + 0.15), s * (mid + 0.15), 0.03, 0.17));
  }

  const plinth = box(4.2, 0.5, 4.2, materials.kiosk, 0, 0.25, 0);
  scene.add(plinth);
  scene.add(box(4.4, 0.06, 4.4, materials.trim, 0, 0.53, 0));
  const slab = box(2.4, 4.8, 0.5, materials.kiosk, 0, 2.96, 0);
  scene.add(slab);
  scene.add(box(2.5, 0.1, 0.6, materials.trim, 0, 5.41, 0));
  const monumentFaces = [0, Math.PI].map((r) => {
    const p = signPlane(2.2, 4.4);
    p.position.set(Math.sin(r) * 0.26, 2.96, Math.cos(r) * 0.26);
    p.rotation.y = r;
    scene.add(p);
    return p;
  });
  signs.push({ mesh: monumentFaces, x: 0, z: 0, make: monumentTexture, eager: true });
  colliders.push(footprint(0, 0, 4.2, 4.2, 0));
  interactables.push({ dest: DEST.plaza, x: 0, z: 0, radius: 5 });
  const spawn: Arrival = { x: 0, z: 16, yaw: 0 };
  zones.push({ key: "plaza", label: "Plaza", dest: DEST.plaza, arrival: spawn });

  // ── Closed buildings (door on local +z) ────────────────────────────────
  const buildings: BuildingSpec[] = [
    { key: "live", x: 0, z: -33, w: 18, d: 12, h: 7.2, rot: 0, subtitle: "Join the lobby · live now" },
    { key: "teach", x: -27, z: 29, w: 13, d: 10, h: 6.4, rot: Math.PI, subtitle: "Share what you know" },
    { key: "community", x: 27, z: 29, w: 13, d: 10, h: 6.4, rot: Math.PI, subtitle: "Forum · meet makers" },
  ];
  for (const b of buildings) {
    const g = new THREE.Group();
    g.position.set(b.x, 0, b.z);
    g.rotation.y = b.rot;
    g.add(withEdges(box(b.w, b.h, b.d, materials.building, 0, b.h / 2, 0)));
    g.add(box(b.w + 0.3, 0.28, b.d + 0.3, materials.trim, 0, b.h + 0.14, 0));
    g.add(box(b.w + 0.12, 0.3, b.d + 0.12, materials.kiosk, 0, 0.15, 0));
    // Doorway: dark opening framed in gold.
    const front = b.d / 2;
    const door = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 3.8), materials.doorway);
    door.position.set(0, 1.9, front + 0.02);
    g.add(door);
    g.add(box(0.16, 4.0, 0.16, materials.trim, -1.78, 2.0, front + 0.06));
    g.add(box(0.16, 4.0, 0.16, materials.trim, 1.78, 2.0, front + 0.06));
    g.add(box(3.72, 0.16, 0.16, materials.trim, 0, 3.92, front + 0.06));
    // Window slits either side of the door.
    for (const side of [-1, 1]) {
      for (let i = 0; i < 2; i++) {
        const win = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 2.4), materials.doorway);
        win.position.set(side * (3.6 + i * 2), 2.2, front + 0.02);
        g.add(win);
      }
    }
    const sign = signPlane(8, 2);
    sign.position.set(0, Math.min(b.h - 1.3, 5.35), front + 0.03);
    g.add(sign);
    scene.add(g);

    const title = DEST[b.key].title;
    signs.push({ mesh: sign, x: b.x, z: b.z, make: () => buildingSignTexture(title, b.subtitle), eager: true });
    colliders.push(footprint(b.x, b.z, b.w + 0.2, b.d + 0.2, b.rot));

    const ox = Math.sin(b.rot);
    const oz = Math.cos(b.rot);
    const doorX = b.x + ox * front;
    const doorZ = b.z + oz * front;
    const trigger = footprint(doorX + ox * 0.9, doorZ + oz * 0.9, 3.4, 1.6, b.rot);
    interactables.push({
      dest: DEST[b.key],
      x: doorX + ox * 1.5,
      z: doorZ + oz * 1.5,
      radius: 5.5,
      trigger: { box: trigger, inX: -ox, inZ: -oz },
    });
    const ax = doorX + ox * 11;
    const az = doorZ + oz * 11;
    zones.push({ key: b.key, label: title, dest: DEST[b.key], arrival: { x: ax, z: az, yaw: yawToward(ax, az, doorX, doorZ) } });
  }

  // ── Open-air courtyards: Activities Hall (west) and Study Groups (east) ─
  const hallRows: Row[] = [];
  const studyRows: Row[] = [];

  const courtyard = (
    key: "activities" | "study",
    minX: number,
    maxX: number,
    minZ: number,
    maxZ: number,
    gateX: number,
    outward: 1 | -1,
    subtitle: string,
  ): void => {
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(maxX - minX, maxZ - minZ), materials.plaza);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set((minX + maxX) / 2, 0.012, (minZ + maxZ) / 2);
    floor.receiveShadow = true;
    scene.add(floor);

    const gap = 3.6;
    const wall = (x0: number, z0: number, x1: number, z1: number): void => {
      const w = Math.abs(x1 - x0) + WALL_T;
      const d = Math.abs(z1 - z0) + WALL_T;
      const cx = (x0 + x1) / 2;
      const cz = (z0 + z1) / 2;
      scene.add(withEdges(box(w, WALL_H, d, materials.building, cx, WALL_H / 2, cz)));
      scene.add(box(w + 0.04, 0.12, d + 0.04, materials.trim, cx, WALL_H + 0.06, cz));
      colliders.push(footprint(cx, cz, w, d, 0));
    };
    const backX = gateX === minX ? maxX : minX;
    wall(minX, minZ, maxX, minZ);
    wall(minX, maxZ, maxX, maxZ);
    wall(backX, minZ, backX, maxZ);
    wall(gateX, minZ, gateX, -gap);
    wall(gateX, gap, gateX, maxZ);

    // Gate: two pillars and a lintel carrying the sign on both faces.
    const rot = outward === 1 ? Math.PI / 2 : -Math.PI / 2;
    const gate = new THREE.Group();
    gate.position.set(gateX, 0, 0);
    gate.rotation.y = rot;
    for (const s of [-1, 1]) gate.add(withEdges(box(0.9, 6.2, 0.9, materials.kiosk, s * (gap + 0.45), 3.1, 0)));
    gate.add(box(2 * gap + 1.8, 1.9, 0.7, materials.kiosk, 0, 5.25, 0));
    gate.add(box(2 * gap + 2.0, 0.14, 0.8, materials.trim, 0, 6.27, 0));
    gate.add(box(2 * gap + 1.8, 0.1, 0.72, materials.trim, 0, 4.27, 0));
    const faces = [0, Math.PI].map((r) => {
      const p = signPlane(6.4, 1.6);
      p.position.set(0, 5.25, Math.cos(r) * 0.36);
      p.rotation.y = r;
      gate.add(p);
      return p;
    });
    scene.add(gate);
    const title = DEST[key].title;
    signs.push({ mesh: faces, x: gateX, z: 0, make: () => buildingSignTexture(title, subtitle), eager: true });
    for (const s of [-1, 1]) colliders.push(footprint(gateX, s * (gap + 0.45), 0.9, 0.9, 0));

    const trigger: Box2 = { minX: gateX - 0.9, maxX: gateX + 0.9, minZ: -gap, maxZ: gap };
    interactables.push({
      dest: DEST[key],
      x: gateX + outward * 1.5,
      z: 0,
      radius: 4.5,
      trigger: { box: trigger, inX: -outward, inZ: 0 },
    });
    const ax = gateX + outward * 11;
    zones.push({ key, label: title, dest: DEST[key], arrival: { x: ax, z: 0, yaw: yawToward(ax, 0, gateX, 0) } });

    // Gold traces down the central avenue.
    const inner = backX + outward * 2;
    for (const off of [-1.2, 1.2]) {
      traceGeoms.push(strip([[gateX, off], [inner, off]], -0.04, 0.04, 0.03));
      traceGeoms.push(pad(inner, off, 0.03));
    }
  };

  courtyard("activities", -64, -20, -20, 20, -20, 1, "Course catalog · live & self-paced");
  courtyard("study", 20, 44, -12, 12, 20, -1, "Learn together · live");

  // Activities Hall rows: two face the central avenue, four line the side streets.
  const hallXs = Array.from({ length: 8 }, (_, i) => -28 - i * 4);
  const hallRowDefs: [number, number][] = [
    [-4.6, 0],
    [4.6, Math.PI],
    [-9.2, Math.PI],
    [9.2, 0],
    [-18.6, 0],
    [18.6, Math.PI],
  ];
  for (const [z, rot] of hallRowDefs) {
    hallRows.push({ header: { x: -23.8, z, rot }, slots: hallXs.map((x) => ({ x, z, rot })) });
  }
  const studyXs = [27.5, 31.5, 35.5, 39.5];
  for (const [z, rot] of [[-4.6, 0], [4.6, Math.PI]] as [number, number][]) {
    studyRows.push({ header: { x: 23.8, z, rot }, slots: studyXs.map((x) => ({ x, z, rot })) });
  }

  // ── Whiteboard on the plaza's north-east edge ─────────────────────────
  {
    const wx = 14;
    const wz = -14;
    const rot = Math.atan2(-wx, -wz);
    const g = new THREE.Group();
    g.position.set(wx, 0, wz);
    g.rotation.y = rot;
    g.add(withEdges(box(6.6, 3.5, 0.18, materials.kiosk, 0, 2.55, 0)));
    for (const s of [-1, 1]) g.add(box(0.14, 1.0, 0.14, materials.kiosk, s * 2.8, 0.5, 0));
    g.add(box(6.6, 0.1, 0.4, materials.trim, 0, 0.84, 0.12));
    const board = signPlane(6.3, 3.15);
    board.position.set(0, 2.55, 0.1);
    g.add(board);
    scene.add(g);
    signs.push({ mesh: board, x: wx, z: wz, make: whiteboardTexture, eager: true });
    colliders.push(footprint(wx, wz, 6.6, 0.6, rot));
    const fx = Math.sin(rot);
    const fz = Math.cos(rot);
    interactables.push({ dest: DEST.whiteboard, x: wx + fx * 2, z: wz + fz * 2, radius: 4 });
    const ax = wx + fx * 6;
    const az = wz + fz * 6;
    zones.push({ key: "whiteboard", label: "Whiteboard", dest: DEST.whiteboard, arrival: { x: ax, z: az, yaw: yawToward(ax, az, wx, wz) } });
  }

  // ── Paths between buildings, edged with gold circuit traces ────────────
  const paths: [number, number][][] = [
    [[0, -11.6], [0, -27]],
    [[-11.6, 0], [-20, 0]],
    [[11.6, 0], [20, 0]],
    [[-8.3, 8.3], [-16, 16], [-24, 16], [-27, 19], [-27, 24]],
    [[8.3, 8.3], [16, 16], [24, 16], [27, 19], [27, 24]],
  ];
  for (const p of paths) {
    pathGeoms.push(strip(p, -1.7, 1.7, 0.02));
    for (const off of [-1.25, 1.25]) {
      traceGeoms.push(strip(p, off - 0.04, off + 0.04, 0.03));
    }
    // Pads at the ends of each trace.
    const [a, b] = [p[0], p[p.length - 1]];
    const dir = (q0: [number, number], q1: [number, number]): [number, number] => {
      const l = Math.hypot(q1[0] - q0[0], q1[1] - q0[1]);
      return [(q1[1] - q0[1]) / l, -(q1[0] - q0[0]) / l];
    };
    const nA = dir(p[0], p[1]);
    const nB = dir(p[p.length - 2], p[p.length - 1]);
    for (const off of [-1.25, 1.25]) {
      traceGeoms.push(pad(a[0] + nA[0] * off, a[1] + nA[1] * off, 0.031));
      traceGeoms.push(pad(b[0] + nB[0] * off, b[1] + nB[1] * off, 0.031));
    }
  }
  // A thin branch from the north path to the whiteboard.
  traceGeoms.push(strip([[1.25, -13], [6, -13], [9.5, -9.5]], -0.04, 0.04, 0.03));
  traceGeoms.push(pad(9.6, -9.4, 0.031));

  // Merge into one draw call each: same attribute set (position + normal), no index.
  const merge = (geoms: THREE.BufferGeometry[]): THREE.BufferGeometry =>
    mergeGeometries(
      geoms.map((g) => {
        const flat = g.index ? g.toNonIndexed() : g;
        flat.deleteAttribute("uv");
        return flat;
      }),
    );
  const pathMesh = new THREE.Mesh(merge(pathGeoms), materials.path);
  pathMesh.receiveShadow = true;
  scene.add(pathMesh);
  scene.add(new THREE.Mesh(merge(traceGeoms), materials.trace));

  // Keep the visitor on campus.
  const R = 90;
  colliders.push(
    { minX: -R - 1, maxX: R + 1, minZ: -R - 1, maxZ: -R },
    { minX: -R - 1, maxX: R + 1, minZ: R, maxZ: R + 1 },
    { minX: -R - 1, maxX: -R, minZ: -R, maxZ: R },
    { minX: R, maxX: R + 1, minZ: -R, maxZ: R },
  );

  const order = ["plaza", "live", "activities", "study", "teach", "community", "whiteboard"];
  zones.sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));

  return { zones, interactables, colliders, signs, hallRows, studyRows, spawn };
}
