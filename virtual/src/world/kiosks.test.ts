import { describe, expect, it } from "vitest";
import type { ActivityGroup } from "../data/activities";
import type { CampusActivity } from "../data/activities";
import type { Row } from "./campus";
import { layoutRows } from "./kiosks";

function activity(id: string): CampusActivity {
  return {
    id,
    title: id,
    slug: id,
    status: "published",
    type: "course",
    format: "self_paced",
    description: "",
    priceCents: 0,
    hostName: "",
    featured: false,
    popularity: 0,
    createdAt: "",
  };
}

function row(id: string): Row {
  return {
    header: { x: 0, z: 0, rot: 0 },
    slots: [
      { x: Number(id) || 0, z: 0, rot: 0 },
      { x: (Number(id) || 0) + 1, z: 0, rot: 0 },
    ],
  };
}

describe("layoutRows", () => {
  it("places all group items into row slots", () => {
    const group: ActivityGroup = { label: "Courses", items: [activity("1"), activity("2")] };
    const result = layoutRows([group], [row("0")]);
    expect(result.kiosks.map(({ activity }) => activity.id)).toEqual(["1", "2"]);
    expect(result.headers).toEqual([{
      slot: row("0").header,
      label: "Courses",
      count: "2 activities",
    }]);
  });

  it("starts a new group on a fresh row", () => {
    const groups: ActivityGroup[] = [
      { label: "First", items: [activity("a")] },
      { label: "Second", items: [activity("b")] },
    ];
    const result = layoutRows(groups, [row("0"), row("1")]);
    expect(result.kiosks.map(({ activity }) => activity.id)).toEqual(["a", "b"]);
    expect(result.headers.map(({ label }) => label)).toEqual(["First", "Second"]);
  });

  it("adds continuation headers when a group spans rows", () => {
    const group: ActivityGroup = {
      label: "Courses",
      items: [activity("a"), activity("b"), activity("c")],
    };
    const result = layoutRows([group], [row("0"), row("1")]);
    expect(result.headers.map(({ label }) => label)).toEqual(["Courses", "Courses (cont.)"]);
    expect(result.kiosks).toHaveLength(3);
  });

  it("does not return more kiosks than available row slots", () => {
    const group: ActivityGroup = {
      label: "Courses",
      items: [activity("a"), activity("b"), activity("c")],
    };
    const result = layoutRows([group], [row("0")]);
    expect(result.kiosks).toHaveLength(2);
    expect(result.headers).toHaveLength(1);
  });
});
