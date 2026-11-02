export interface ActivityLink {
  label: string;
  url: string;
}

/** Anything the player can open a panel for: a campus zone or a real activity. */
export interface Destination {
  id: string;
  kind: "zone" | "activity";
  /** Small uppercase label shown above the title (e.g. "COURSE · LIVE"). */
  eyebrow: string;
  title: string;
  description: string;
  links: ActivityLink[];
}

/** Where the camera lands when teleporting, and which way it faces. */
export interface Arrival {
  x: number;
  z: number;
  yaw: number;
}

/** Axis-aligned box on the ground plane, used for collision and triggers. */
export interface Box2 {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}
