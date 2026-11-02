import { describe, expect, it } from "vitest";
import {
  normalize,
  roomFor,
  selectForCampus,
  slugFor,
  type CampusActivity,
} from "./activities";

function activity(overrides: Partial<CampusActivity> = {}): CampusActivity {
  return {
    id: "activity-1",
    title: "Activity",
    slug: "",
    status: "published",
    type: "course",
    format: "self_paced",
    description: "Description",
    priceCents: 0,
    hostName: "",
    featured: false,
    popularity: 0,
    createdAt: "2026-01-01",
    ...overrides,
  };
}

describe("activity normalization and slugs", () => {
  it("normalizes API fields and combines popularity", () => {
    expect(normalize({
      id: 42,
      title: "  Intro to TypeScript  ",
      slug: "intro-typescript",
      status: "published",
      type: "course",
      format: "live",
      description: "# Learn **TypeScript**\n\nBuild [apps](https://example.com).",
      price_cents: 1250,
      host_name: "Ada",
      is_featured: true,
      interest_count: 7,
      participant_count: 3,
      created_at: "2026-10-01",
    })).toEqual({
      id: "42",
      title: "Intro to TypeScript",
      slug: "intro-typescript",
      status: "published",
      type: "course",
      format: "live",
      description: "Learn TypeScript Build apps.",
      priceCents: 1250,
      hostName: "Ada",
      featured: true,
      popularity: 10,
      createdAt: "2026-10-01",
    });
  });

  it("applies defaults for missing optional API fields", () => {
    expect(normalize({ id: "1", title: "Course" })).toMatchObject({
      status: "published",
      type: "course",
      format: "self_paced",
      description: "",
      featured: false,
      popularity: 0,
    });
  });

  it("rejects activities without an id or title", () => {
    expect(normalize({ id: "", title: "Course" })).toBeNull();
    expect(normalize({ id: "1", title: "  " })).toBeNull();
  });

  it("creates lowercase classroom slugs", () => {
    expect(slugFor("  Hello, Virtual World!  ")).toBe("hello-virtual-world");
  });

  it("falls back to lobby for an empty slug", () => {
    expect(slugFor("***")).toBe("lobby");
    expect(roomFor(activity({ id: "***", slug: "" }))).toBe("lobby");
  });
});

describe("selectForCampus", () => {
  it("sorts live items ahead of self-paced items", () => {
    const selfPaced = activity({ id: "slow", format: "self_paced", popularity: 100 });
    const live = activity({ id: "live", format: "live", popularity: 1 });
    const selected = selectForCampus([selfPaced, live]);
    expect(selected.hall[0].items[0].id).toBe("live");
  });

  it("puts published courses before waitlist activities", () => {
    const published = activity({ id: "published", status: "published", popularity: 1 });
    const waitlist = activity({ id: "waitlist", status: "waitlist", popularity: 100 });
    const selected = selectForCampus([waitlist, published]);
    expect(selected.hall.map((group) => ({
      label: group.label,
      ids: group.items.map((item) => item.id),
    }))).toEqual([
      { label: "Courses & workshops", ids: ["published"] },
      { label: "Waitlist · coming soon", ids: ["waitlist"] },
    ]);
  });

  it("respects the hall cap across all groups", () => {
    const all = [
      ...Array.from({ length: 3 }, (_, i) => activity({ id: `course-${i}`, type: "course" })),
      ...Array.from({ length: 3 }, (_, i) => activity({ id: `video-${i}`, type: "video" })),
      ...Array.from({ length: 3 }, (_, i) => activity({ id: `wait-${i}`, type: "event", status: "waitlist" })),
    ];
    const selected = selectForCampus(all, 5);
    const total = selected.hall.reduce((sum, group) => sum + group.items.length, 0);
    expect(total).toBe(5);
    expect(selected.hall.flatMap((group) => group.items).filter((item) => item.status === "waitlist")).toHaveLength(0);
  });

  it("caps study groups at the requested limit", () => {
    const groups = Array.from({ length: 12 }, (_, i) =>
      activity({ id: `study-${i}`, type: "study_group" }),
    );
    expect(selectForCampus(groups).study).toHaveLength(8);
    expect(selectForCampus(groups, 40, 3).study).toHaveLength(3);
  });

  it("shows published study groups before waitlist study groups", () => {
    const waitlist = activity({ id: "wait-study", type: "study_group", status: "waitlist", popularity: 100 });
    const published = activity({ id: "live-study", type: "study_group", status: "published", popularity: 1 });
    const selected = selectForCampus([waitlist, published]);
    expect(selected.study.map((item) => item.id)).toEqual(["live-study", "wait-study"]);
  });

  it("does not include draft or unknown-status items", () => {
    const selected = selectForCampus([
      activity({ id: "draft", status: "draft" }),
      activity({ id: "unknown", status: "archived" }),
      activity({ id: "live", status: "published" }),
    ]);
    expect(selected.hall.flatMap((group) => group.items).map((item) => item.id)).toEqual(["live"]);
  });
});
