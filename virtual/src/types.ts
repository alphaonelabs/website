export interface ActivityLink {
  label: string;
  url: string;
}

export interface Activity {
  id: string;
  name: string;
  description: string;
  /** [x, y, z] position of the portal in the world. */
  position: [number, number, number];
  color: number;
  links: ActivityLink[];
}
