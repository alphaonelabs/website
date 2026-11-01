import { LEARN_API_BASE } from "../config";
import type { Activity } from "../types";

export const activities: Activity[] = [
  {
    id: "virtual-classroom",
    name: "Virtual Classroom",
    description:
      "Join live virtual classrooms, whiteboards, and collaborative learning rooms.",
    position: [0, 0, -8],
    color: 0x14b8a6,
    links: [
      { label: "Enter Global Classroom", url: `${LEARN_API_BASE}/classroom_poc?autojoin=1&room=lobby` },
      { label: "Open Whiteboard", url: `${LEARN_API_BASE}/whiteboard` },
    ],
  },
];
