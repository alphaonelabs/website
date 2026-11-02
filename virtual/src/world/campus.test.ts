import { describe, expect, it } from "vitest";
import { footprint } from "./campus";

describe("footprint", () => {
  it("returns the axis-aligned bounds without rotation", () => {
    expect(footprint(10, 20, 4, 2, 0)).toEqual({
      minX: 8,
      maxX: 12,
      minZ: 19,
      maxZ: 21,
    });
  });

  it("swaps width and depth bounds at a 90-degree rotation", () => {
    const box = footprint(0, 0, 4, 2, Math.PI / 2);
    expect(box.minX).toBeCloseTo(-1);
    expect(box.maxX).toBeCloseTo(1);
    expect(box.minZ).toBeCloseTo(-2);
    expect(box.maxZ).toBeCloseTo(2);
  });

  it("keeps the correct origin for a rotated footprint", () => {
    const box = footprint(6, -3, 4, 2, Math.PI / 2);
    expect(box.minX).toBeCloseTo(5);
    expect(box.maxX).toBeCloseTo(7);
    expect(box.minZ).toBeCloseTo(-5);
    expect(box.maxZ).toBeCloseTo(-1);
  });

  it("uses the same bounds for a 180-degree rotation as unrotated", () => {
    const box = footprint(5, 5, 6, 2, Math.PI);
    expect(box.minX).toBeCloseTo(2);
    expect(box.maxX).toBeCloseTo(8);
    expect(box.minZ).toBeCloseTo(4);
    expect(box.maxZ).toBeCloseTo(6);
  });
});
