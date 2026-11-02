import * as THREE from "three";
import type { Arrival, Box2 } from "../types";

const EYE_HEIGHT = 1.6;
const MOVE_SPEED = 6; // meters/second
const TURN_SPEED = 1.8; // radians/second for on-screen turn buttons
const RADIUS = 0.35;
const MAX_PITCH = Math.PI / 2 - 0.05;

export type MoveKey = "forward" | "backward" | "left" | "right" | "turnLeft" | "turnRight";

const isTyping = (target: EventTarget | null): boolean =>
  target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));

/**
 * First-person controls with two input modes:
 * - locked: pointer lock + mouse look (desktop)
 * - free: drag-to-look on the canvas plus keyboard / on-screen buttons
 *   (phones, or browsers that refuse pointer lock)
 */
export class FirstPersonControls {
  readonly camera: THREE.PerspectiveCamera;
  private readonly domElement: HTMLElement;
  private readonly euler = new THREE.Euler(0, 0, 0, "YXZ");
  private readonly move: Record<MoveKey, boolean> = {
    forward: false,
    backward: false,
    left: false,
    right: false,
    turnLeft: false,
    turnRight: false,
  };
  private drag: { id: number; x: number; y: number } | null = null;
  private readonly forward = new THREE.Vector3();
  private readonly right = new THREE.Vector3();

  isLocked = false;
  /** Drag-to-look mode; set by the app when pointer lock isn't used. */
  freeMode = false;
  /** False while a panel or the menu is open. */
  enabled = true;
  colliders: Box2[] = [];

  constructor(camera: THREE.PerspectiveCamera, domElement: HTMLElement) {
    this.camera = camera;
    this.domElement = domElement;
    this.euler.setFromQuaternion(camera.quaternion);

    document.addEventListener("pointerlockchange", this.onLockChange);
    document.addEventListener("mousemove", this.onMouseMove);
    document.addEventListener("keydown", this.onKeyDown);
    document.addEventListener("keyup", this.onKeyUp);
    window.addEventListener("blur", this.resetMoveState);
    domElement.addEventListener("pointerdown", this.onPointerDown);
    domElement.addEventListener("pointermove", this.onPointerMove);
    domElement.addEventListener("pointerup", this.onPointerUp);
    domElement.addEventListener("pointercancel", this.onPointerUp);
  }

  get active(): boolean {
    return this.enabled && (this.isLocked || this.freeMode);
  }

  /** Requests pointer lock; resolves false if the browser refuses. */
  lock(): Promise<boolean> {
    return new Promise((resolve) => {
      let settled = false;
      const done = (ok: boolean): void => {
        if (settled) return;
        settled = true;
        document.removeEventListener("pointerlockchange", onChange);
        document.removeEventListener("pointerlockerror", onError);
        resolve(ok);
      };
      const onChange = (): void => done(document.pointerLockElement === this.domElement);
      const onError = (): void => done(false);
      document.addEventListener("pointerlockchange", onChange);
      document.addEventListener("pointerlockerror", onError);
      try {
        const result = this.domElement.requestPointerLock() as unknown;
        if (result instanceof Promise) result.catch(() => done(false));
      } catch {
        done(false);
      }
      window.setTimeout(() => done(document.pointerLockElement === this.domElement), 1500);
    });
  }

  unlock(): void {
    if (document.pointerLockElement) document.exitPointerLock();
  }

  setMove(key: MoveKey, value: boolean): void {
    this.move[key] = value;
  }

  teleport(a: Arrival): void {
    this.camera.position.set(a.x, EYE_HEIGHT, a.z);
    this.euler.set(-0.06, a.yaw, 0, "YXZ");
    this.camera.quaternion.setFromEuler(this.euler);
    this.resetMoveState();
  }

  update(deltaSeconds: number): void {
    if (!this.active) return;
    const dt = Math.min(deltaSeconds, 0.1);

    const turn = Number(this.move.turnLeft) - Number(this.move.turnRight);
    if (turn !== 0) {
      this.euler.setFromQuaternion(this.camera.quaternion);
      this.euler.y += turn * TURN_SPEED * dt;
      this.camera.quaternion.setFromEuler(this.euler);
    }

    const forwardInput = Number(this.move.forward) - Number(this.move.backward);
    const rightInput = Number(this.move.right) - Number(this.move.left);
    if (forwardInput === 0 && rightInput === 0) return;

    this.camera.getWorldDirection(this.forward);
    this.forward.y = 0;
    this.forward.normalize();
    this.right.crossVectors(this.forward, this.camera.up);

    const step = (MOVE_SPEED * dt) / Math.hypot(forwardInput, rightInput);
    const pos = this.camera.position;
    pos.addScaledVector(this.forward, forwardInput * step);
    pos.addScaledVector(this.right, rightInput * step);
    pos.y = EYE_HEIGHT;
    this.collide();
  }

  /** Push the player's circle out of any overlapping box. */
  private collide(): void {
    const pos = this.camera.position;
    for (let pass = 0; pass < 2; pass++) {
      for (const b of this.colliders) {
        const cx = Math.max(b.minX, Math.min(pos.x, b.maxX));
        const cz = Math.max(b.minZ, Math.min(pos.z, b.maxZ));
        const dx = pos.x - cx;
        const dz = pos.z - cz;
        const d2 = dx * dx + dz * dz;
        if (d2 >= RADIUS * RADIUS) continue;
        if (d2 > 1e-8) {
          const d = Math.sqrt(d2);
          pos.x = cx + (dx / d) * RADIUS;
          pos.z = cz + (dz / d) * RADIUS;
        } else {
          // Centre is inside the box: exit through the nearest side.
          const exits = [pos.x - b.minX, b.maxX - pos.x, pos.z - b.minZ, b.maxZ - pos.z];
          const m = exits.indexOf(Math.min(...exits));
          if (m === 0) pos.x = b.minX - RADIUS;
          else if (m === 1) pos.x = b.maxX + RADIUS;
          else if (m === 2) pos.z = b.minZ - RADIUS;
          else pos.z = b.maxZ + RADIUS;
        }
      }
    }
  }

  private look(dx: number, dy: number, scale: number): void {
    this.euler.setFromQuaternion(this.camera.quaternion);
    this.euler.y -= dx * scale;
    this.euler.x -= dy * scale;
    this.euler.x = Math.max(-MAX_PITCH, Math.min(MAX_PITCH, this.euler.x));
    this.camera.quaternion.setFromEuler(this.euler);
  }

  private onLockChange = (): void => {
    this.isLocked = document.pointerLockElement === this.domElement;
    if (!this.isLocked) this.resetMoveState();
  };

  private resetMoveState = (): void => {
    for (const k of Object.keys(this.move) as MoveKey[]) this.move[k] = false;
  };

  private onMouseMove = (event: MouseEvent): void => {
    if (!this.isLocked || !this.enabled) return;
    this.look(event.movementX, event.movementY, 0.002);
  };

  private onPointerDown = (event: PointerEvent): void => {
    if (!this.freeMode || !this.enabled || this.isLocked) return;
    this.drag = { id: event.pointerId, x: event.clientX, y: event.clientY };
    try {
      this.domElement.setPointerCapture(event.pointerId);
    } catch {
      // Synthetic or already-released pointers can't be captured; dragging still works.
    }
  };

  private onPointerMove = (event: PointerEvent): void => {
    if (!this.drag || event.pointerId !== this.drag.id) return;
    const scale = event.pointerType === "touch" ? 0.006 : 0.004;
    this.look(event.clientX - this.drag.x, event.clientY - this.drag.y, scale);
    this.drag.x = event.clientX;
    this.drag.y = event.clientY;
  };

  private onPointerUp = (event: PointerEvent): void => {
    if (this.drag && event.pointerId === this.drag.id) this.drag = null;
  };

  private onKeyDown = (event: KeyboardEvent): void => {
    if (!this.active || isTyping(event.target)) return;
    this.setKey(event.code, true);
  };

  private onKeyUp = (event: KeyboardEvent): void => {
    this.setKey(event.code, false);
  };

  private setKey(code: string, value: boolean): void {
    switch (code) {
      case "KeyW":
      case "ArrowUp":
        this.move.forward = value;
        break;
      case "KeyS":
      case "ArrowDown":
        this.move.backward = value;
        break;
      case "KeyA":
      case "ArrowLeft":
        this.move.left = value;
        break;
      case "KeyD":
      case "ArrowRight":
        this.move.right = value;
        break;
    }
  }
}
