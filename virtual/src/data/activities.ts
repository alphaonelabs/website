import { LEARN_API_BASE } from "../config";
import type { Destination } from "../types";

const SITE = LEARN_API_BASE.replace(/\/+$/, "");

export function learnUrl(path: string): string {
  return `${SITE}${path}`;
}

/** An activity from learn.alphaonelabs.com, trimmed to what the campus needs. */
export interface CampusActivity {
  id: string;
  title: string;
  slug: string;
  status: string;
  type: string;
  format: string;
  description: string;
  priceCents: number;
  hostName: string;
  featured: boolean;
  popularity: number;
  createdAt: string;
}

interface ApiActivity {
  id?: unknown;
  title?: unknown;
  slug?: unknown;
  status?: unknown;
  type?: unknown;
  format?: unknown;
  description?: unknown;
  price_cents?: unknown;
  host_name?: unknown;
  is_featured?: unknown;
  interest_count?: unknown;
  participant_count?: unknown;
  created_at?: unknown;
}

const str = (v: unknown): string => (typeof v === "string" ? v : typeof v === "number" ? String(v) : "");
const num = (v: unknown): number => (typeof v === "number" && Number.isFinite(v) ? v : 0);

/** Strip markdown noise and clamp to a short, single-paragraph blurb. */
function cleanDescription(raw: string, max = 220): string {
  const text = raw
    .replace(/[#*_`>|]+/g, " ")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max).replace(/\s+\S*$/, "")}…`;
}

function normalize(raw: ApiActivity): CampusActivity | null {
  const id = str(raw.id);
  const title = str(raw.title).trim();
  if (!id || !title) return null;
  return {
    id,
    title,
    slug: str(raw.slug),
    status: str(raw.status) || "published",
    type: str(raw.type) || "course",
    format: str(raw.format) || "self_paced",
    description: cleanDescription(str(raw.description)),
    priceCents: num(raw.price_cents),
    hostName: str(raw.host_name),
    featured: raw.is_featured === true,
    popularity: num(raw.interest_count) + num(raw.participant_count),
    createdAt: str(raw.created_at),
  };
}

/** Small built-in list (real activities) used when the API is unreachable. */
const FALLBACK: CampusActivity[] = [
  ["legacy-study-group-2", "10X Students Study Group", "study_group", "live", "Become the 10x version of yourself."],
  ["fb16ea50-ff87-4508-976b-0ac902d29965", "Why Is Redis So Fast? Understanding High-Throughput Caching", "study_group", "live", "A beginner-friendly session explaining why Redis can handle extremely high throughput."],
  ["3184049b-e326-4084-9afb-8c03ac837827", "Why Are WebSockets Faster Than HTTP? Real-Time Communication", "study_group", "live", "A beginner-friendly session explaining why WebSockets are faster for real-time apps."],
  ["61a9540a-de52-49f6-95e4-3486f2f25a60", "How Message Queues Make Apps Faster: RabbitMQ vs Direct API", "study_group", "live", "A beginner-friendly workshop explaining how message queues improve performance."],
  ["legacy-course-12", "OSL - Advent of Code Study Group", "course", "live", "A study group focused on sharpening problem-solving skills with Advent of Code."],
  ["legacy-course-10", "Crash Test Coding 101 - build a website in 1 hour", "course", "live", "Learn how to build a website super fast, in about one hour."],
  ["legacy-course-9", "Poetry Circle", "course", "live", "Write original poems and respond to others' poems in a supportive circle."],
  ["legacy-course-2", "The Art of Music: From Theory to Production", "course", "live", "From the foundations of music theory to production."],
  ["legacy-course-3", "PMA: Physics, Math, Alchemy", "course", "self_paced", "The interplay of science, logic, and the mysteries of transformation."],
].map(([id, title, type, format, description]) => ({
  id,
  title,
  slug: id,
  status: "published",
  type,
  format,
  description,
  priceCents: 0,
  hostName: "",
  featured: false,
  popularity: 0,
  createdAt: "",
}));

export interface ActivityFeed {
  activities: CampusActivity[];
  source: "live" | "fallback";
}

export async function fetchActivities(timeoutMs = 8000): Promise<ActivityFeed> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(learnUrl("/api/activities"), {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = (await res.json()) as { activities?: unknown };
    if (!Array.isArray(body.activities)) throw new Error("Unexpected response shape");
    const activities = (body.activities as ApiActivity[])
      .map(normalize)
      .filter((a): a is CampusActivity => a !== null);
    if (activities.length === 0) throw new Error("No activities");
    return { activities, source: "live" };
  } catch (err) {
    console.warn("[virtual] Falling back to built-in activities:", err);
    return { activities: FALLBACK, source: "fallback" };
  } finally {
    window.clearTimeout(timer);
  }
}

export const isLive = (a: CampusActivity): boolean => a.format === "live";
export const isStudyGroup = (a: CampusActivity): boolean => a.type === "study_group";
export const isWaitlist = (a: CampusActivity): boolean => a.status === "waitlist";

const TYPE_LABEL: Record<string, string> = {
  course: "Course",
  study_group: "Study group",
  workshop: "Workshop",
  video: "Video",
  event: "Event",
};

export function typeLabel(type: string): string {
  return TYPE_LABEL[type] ?? type.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function eyebrowFor(a: CampusActivity): string {
  const parts = [typeLabel(a.type)];
  if (isLive(a)) parts.push("Live");
  else if (a.format === "self_paced") parts.push("Self-paced");
  if (isWaitlist(a)) parts.push("Waitlist");
  return parts.join(" · ").toUpperCase();
}

/** Classroom room names are short slugs; one room per live activity. */
export function roomFor(a: CampusActivity): string {
  const base = (a.slug || a.id).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return base.slice(0, 40).replace(/-+$/, "") || "lobby";
}

export function activityDestination(a: CampusActivity): Destination {
  const links = [{ label: "Open activity", url: learnUrl(`/activity/${encodeURIComponent(a.id)}`) }];
  if (isLive(a) || isStudyGroup(a)) {
    links.push({
      label: "Join live classroom",
      url: learnUrl(`/classroom_poc?autojoin=1&room=${encodeURIComponent(roomFor(a))}`),
    });
  }
  const host = a.hostName ? `Hosted by ${a.hostName}. ` : "";
  return {
    id: `activity:${a.id}`,
    kind: "activity",
    eyebrow: eyebrowFor(a),
    title: a.title,
    description: `${host}${a.description || "Open the activity page for details."}`,
    links,
  };
}

export interface ActivityGroup {
  label: string;
  items: CampusActivity[];
}

const TYPE_ORDER = ["course", "workshop", "event", "video"];
const typeRank = (t: string): number => {
  const i = TYPE_ORDER.indexOf(t);
  return i === -1 ? TYPE_ORDER.length : i;
};

/**
 * Split activities into what each building shows. Published activities come
 * first (live ones leading), then the most-wanted waitlist items, capped so
 * the world stays light.
 */
export function selectForCampus(
  all: CampusActivity[],
  hallCap = 40,
  studyCap = 8,
): { hall: ActivityGroup[]; study: CampusActivity[] } {
  const visible = all.filter((a) => a.status === "published" || a.status === "waitlist");
  const byPriority = (a: CampusActivity, b: CampusActivity): number =>
    Number(isLive(b)) - Number(isLive(a)) ||
    Number(b.featured) - Number(a.featured) ||
    b.popularity - a.popularity ||
    b.createdAt.localeCompare(a.createdAt);

  const study = visible
    .filter(isStudyGroup)
    .sort((a, b) => Number(isWaitlist(a)) - Number(isWaitlist(b)) || byPriority(a, b))
    .slice(0, studyCap);

  const rest = visible.filter((a) => !isStudyGroup(a));
  const published = rest.filter((a) => !isWaitlist(a));
  const courses = published
    .filter((a) => a.type !== "video")
    .sort((a, b) => byPriority(a, b) || typeRank(a.type) - typeRank(b.type));
  const videos = published.filter((a) => a.type === "video").sort(byPriority);
  const waitlist = rest.filter(isWaitlist).sort(byPriority);

  const groups: ActivityGroup[] = [];
  let budget = hallCap;
  for (const [label, items] of [
    ["Courses & workshops", courses],
    ["Video lessons", videos],
    ["Waitlist · coming soon", waitlist],
  ] as const) {
    if (budget <= 0 || items.length === 0) continue;
    const take = items.slice(0, budget);
    budget -= take.length;
    groups.push({ label, items: take });
  }
  return { hall: groups, study };
}
