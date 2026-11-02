import type { Box2 } from "../types";
import type { Interactable } from "./campus";

const inside = (b: Box2, x: number, z: number): boolean => x >= b.minX && x <= b.maxX && z >= b.minZ && z <= b.maxZ;

export class Interactions {
  private readonly items: Interactable[] = [];
  /** Triggers the player is standing in; they re-arm only after leaving. */
  private readonly latched = new Set<Interactable>();

  constructor(items: Interactable[] = []) {
    this.add(items);
  }

  add(items: Interactable[]): void {
    this.items.push(...items);
  }

  /** Closest interactable whose radius contains the point (relative distance). */
  nearest(x: number, z: number): Interactable | null {
    let best: Interactable | null = null;
    let bestScore = 1;
    for (const it of this.items) {
      const score = Math.hypot(it.x - x, it.z - z) / it.radius;
      if (score < bestScore) {
        best = it;
        bestScore = score;
      }
    }
    return best;
  }

  /** Returns a doorway the player just walked into (moving inward), if any. */
  checkTriggers(prevX: number, prevZ: number, x: number, z: number): Interactable | null {
    let fired: Interactable | null = null;
    for (const it of this.items) {
      const t = it.trigger;
      if (!t) continue;
      if (!inside(t.box, x, z)) {
        this.latched.delete(it);
        continue;
      }
      if (this.latched.has(it)) continue;
      this.latched.add(it);
      const inward = (x - prevX) * t.inX + (z - prevZ) * t.inZ;
      if (inward > 1e-4 && !fired) fired = it;
    }
    return fired;
  }

  /** After a teleport, treat any trigger we landed in as already used. */
  resetTriggers(x: number, z: number): void {
    this.latched.clear();
    for (const it of this.items) if (it.trigger && inside(it.trigger.box, x, z)) this.latched.add(it);
  }
}
