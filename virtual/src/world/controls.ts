import * as THREE from "three";

const EYE_HEIGHT = 1.6;
const MOVE_SPEED = 5; // meters/second
const HALF_PI = Math.PI / 2;

export class FirstPersonControls {
  readonly camera: THREE.PerspectiveCamera;
  private readonly domElement: HTMLElement;
  private readonly euler = new THREE.Euler(0, 0, 0, "YXZ");
  private readonly move = { forward: false, backward: false, left: false, right: false };
  isLocked = false;

  constructor(camera: THREE.PerspectiveCamera, domElement: HTMLElement) {
    this.camera = camera;
    this.domElement = domElement;

    document.addEventListener("pointerlockchange", this.onLockChange);
    document.addEventListener("mousemove", this.onMouseMove);
    document.addEventListener("keydown", this.onKeyDown);
    document.addEventListener("keyup", this.onKeyUp);
    window.addEventListener("blur", this.resetMoveState);
  }

  lock(): void {
    this.domElement.requestPointerLock();
  }

  unlock(): void {
    document.exitPointerLock();
  }

  update(deltaSeconds: number): void {
    if (!this.isLocked) return;

    const forwardInput = Number(this.move.forward) - Number(this.move.backward);
    const rightInput = Number(this.move.right) - Number(this.move.left);
    if (forwardInput === 0 && rightInput === 0) return;

    const forward = new THREE.Vector3();
    this.camera.getWorldDirection(forward);
    forward.y = 0;
    forward.normalize();

    const right = new THREE.Vector3().crossVectors(forward, this.camera.up);

    const inputLength = Math.hypot(forwardInput, rightInput);
    const step = (MOVE_SPEED * deltaSeconds) / inputLength;
    this.camera.position.addScaledVector(forward, forwardInput * step);
    this.camera.position.addScaledVector(right, rightInput * step);
    this.camera.position.y = EYE_HEIGHT;
  }

  dispose(): void {
    document.removeEventListener("pointerlockchange", this.onLockChange);
    document.removeEventListener("mousemove", this.onMouseMove);
    document.removeEventListener("keydown", this.onKeyDown);
    document.removeEventListener("keyup", this.onKeyUp);
    window.removeEventListener("blur", this.resetMoveState);
  }

  private onLockChange = (): void => {
    this.isLocked = document.pointerLockElement === this.domElement;
    if (!this.isLocked) this.resetMoveState();
  };

  private resetMoveState = (): void => {
    this.move.forward = false;
    this.move.backward = false;
    this.move.left = false;
    this.move.right = false;
  };

  private onMouseMove = (event: MouseEvent): void => {
    if (!this.isLocked) return;

    this.euler.setFromQuaternion(this.camera.quaternion);
    this.euler.y -= event.movementX * 0.002;
    this.euler.x -= event.movementY * 0.002;
    this.euler.x = Math.max(-HALF_PI, Math.min(HALF_PI, this.euler.x));
    this.camera.quaternion.setFromEuler(this.euler);
  };

  private onKeyDown = (event: KeyboardEvent): void => {
    if (!this.isLocked) return;
    this.setMoveState(event.code, true);
  };

  private onKeyUp = (event: KeyboardEvent): void => {
    this.setMoveState(event.code, false);
  };

  private setMoveState(code: string, value: boolean): void {
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
