import type { Destination } from "../types";
import type { MoveKey } from "../world/controls";

function el<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Missing #${id} element in index.html`);
  return found as T;
}

function span(className: string, text: string): HTMLSpanElement {
  const s = document.createElement("span");
  s.className = className;
  s.textContent = text;
  return s;
}

export interface ZoneEntry {
  label: string;
  blurb: string;
  onPick: () => void;
}

export interface SearchEntry {
  title: string;
  meta: string;
  haystack: string;
  onPick: () => void;
}

const MAX_RESULTS = 12;

export class Overlay {
  private readonly blocker = el<HTMLDivElement>("blocker");
  private readonly enterButton = el<HTMLButtonElement>("enter-button");
  private readonly loadStatus = el<HTMLParagraphElement>("load-status");
  private readonly zoneList = el<HTMLUListElement>("zone-list");
  private readonly search = el<HTMLInputElement>("activity-search");
  private readonly results = el<HTMLUListElement>("search-results");
  private readonly crosshair = el<HTMLDivElement>("crosshair");
  private readonly prompt = el<HTMLButtonElement>("prompt");
  private readonly hint = el<HTMLDivElement>("hint");
  private readonly menuButton = el<HTMLButtonElement>("menu-button");
  private readonly touchControls = el<HTMLDivElement>("touch-controls");
  private readonly panel = el<HTMLDivElement>("panel");
  private readonly panelCard = el<HTMLDivElement>("panel-card");
  private readonly panelEyebrow = el<HTMLParagraphElement>("panel-eyebrow");
  private readonly panelTitle = el<HTMLHeadingElement>("panel-title");
  private readonly panelDescription = el<HTMLParagraphElement>("panel-description");
  private readonly panelLinks = el<HTMLDivElement>("panel-links");
  private readonly panelClose = el<HTMLButtonElement>("panel-close");
  private readonly logoutButton = el<HTMLButtonElement>("logout");
  private lastFocused: HTMLElement | null = null;
  private entries: SearchEntry[] = [];
  private promptKey = "";

  constructor() {
    this.search.addEventListener("input", () => this.renderResults());
    this.search.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        this.results.querySelector<HTMLButtonElement>("button")?.click();
      }
    });
  }

  onEnter(handler: () => void): void {
    this.enterButton.addEventListener("click", handler);
  }

  onMenu(handler: () => void): void {
    this.menuButton.addEventListener("click", handler);
  }

  onPromptClick(handler: () => void): void {
    this.prompt.addEventListener("click", handler);
  }

  onPanelClose(handler: () => void): void {
    this.panelClose.addEventListener("click", handler);
  }

  onLogout(handler: () => void): void {
    this.logoutButton.addEventListener("click", handler);
  }

  /** Press-and-hold on-screen movement buttons. */
  onTouchMove(handler: (key: MoveKey, pressed: boolean) => void): void {
    for (const button of this.touchControls.querySelectorAll<HTMLButtonElement>("button[data-move]")) {
      const key = button.dataset.move as MoveKey;
      const set = (pressed: boolean) => (event: Event): void => {
        event.preventDefault();
        button.classList.toggle("pressed", pressed);
        handler(key, pressed);
      };
      button.addEventListener("pointerdown", (e) => {
        set(true)(e);
        try {
          button.setPointerCapture((e as PointerEvent).pointerId);
        } catch {
          // Capture is best-effort; pointerup/cancel still release the button.
        }
      });
      for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) button.addEventListener(type, set(false));
      button.addEventListener("contextmenu", (e) => e.preventDefault());
      // Keyboard users: Space/Enter nudges like a short press.
      button.addEventListener("keydown", (e) => {
        if (e.key === " " || e.key === "Enter") set(true)(e);
      });
      button.addEventListener("keyup", (e) => {
        if (e.key === " " || e.key === "Enter") set(false)(e);
      });
    }
  }

  renderZones(zones: ZoneEntry[]): void {
    this.zoneList.replaceChildren(
      ...zones.map((zone) => {
        const li = document.createElement("li");
        const b = document.createElement("button");
        b.type = "button";
        b.setAttribute("aria-label", `Travel to ${zone.label}`);
        b.append(zone.label);
        const small = document.createElement("small");
        small.textContent = zone.blurb;
        b.append(small);
        b.addEventListener("click", zone.onPick);
        li.append(b);
        return li;
      }),
    );
  }

  setSearchEntries(entries: SearchEntry[]): void {
    this.entries = entries;
    this.renderResults();
  }

  setStatus(text: string): void {
    this.loadStatus.textContent = text;
  }

  private renderResults(): void {
    const q = this.search.value.trim().toLowerCase();
    const terms = q.split(/\s+/).filter(Boolean);
    const matches = this.entries.filter((e) => terms.every((t) => e.haystack.includes(t)));
    const items = matches.slice(0, MAX_RESULTS).map((entry) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("aria-label", `Go to ${entry.title} (${entry.meta})`);
      b.append(span("r-title", entry.title), span("r-meta", entry.meta));
      b.addEventListener("click", entry.onPick);
      li.append(b);
      return li;
    });
    if (items.length === 0 && this.entries.length > 0) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No activities on campus match that search.";
      items.push(li);
    } else if (matches.length > MAX_RESULTS) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = `${matches.length - MAX_RESULTS} more — keep typing to narrow it down.`;
      items.push(li);
    }
    this.results.replaceChildren(...items);
  }

  showBlocker(): void {
    this.blocker.classList.remove("hidden");
    this.crosshair.classList.add("hidden");
    this.hint.classList.add("hidden");
    this.hidePrompt();
    this.setFreeHud(false);
    this.enterButton.focus({ preventScroll: true });
  }

  hideBlocker(mode: "locked" | "free"): void {
    this.blocker.classList.add("hidden");
    this.crosshair.classList.toggle("hidden", mode !== "locked");
    this.hint.textContent =
      mode === "locked"
        ? "WASD move · E interact · Esc menu"
        : "Drag to look · WASD / arrows move · E interact · Esc menu";
    this.hint.classList.remove("hidden");
    this.setFreeHud(mode === "free");
  }

  private setFreeHud(on: boolean): void {
    this.menuButton.classList.toggle("hidden", !on);
    this.touchControls.classList.toggle("hidden", !on);
  }

  isBlockerOpen(): boolean {
    return !this.blocker.classList.contains("hidden");
  }

  showSignIn(handler: () => void): void {
    this.logoutButton.textContent = "Sign in";
    this.logoutButton.addEventListener("click", handler);
    this.logoutButton.classList.remove("hidden");
  }

  showLogout(): void {
    this.logoutButton.classList.remove("hidden");
  }

  showPrompt(dest: Destination): void {
    if (this.promptKey !== dest.id) {
      this.promptKey = dest.id;
      const key = span("key", "E");
      key.setAttribute("aria-hidden", "true");
      const body = span("body", "");
      body.append(span("p-eyebrow", dest.eyebrow), span("p-title", dest.title));
      if (dest.kind === "activity") body.append(span("p-desc", dest.description));
      this.prompt.replaceChildren(key, body);
      this.prompt.setAttribute("aria-label", `Open ${dest.title}`);
    }
    this.prompt.classList.remove("hidden");
  }

  hidePrompt(): void {
    this.prompt.classList.add("hidden");
  }

  showPanel(dest: Destination): void {
    this.panelEyebrow.textContent = dest.eyebrow;
    this.panelTitle.textContent = dest.title;
    this.panelDescription.textContent = dest.description;
    this.panelLinks.replaceChildren(
      ...dest.links.map((link, i) => {
        const a = document.createElement("a");
        a.href = link.url;
        a.textContent = link.label;
        a.target = "_blank";
        a.rel = "noopener";
        a.className = i === 0 ? "btn" : "btn btn-ghost";
        return a;
      }),
    );
    this.panel.classList.remove("hidden");
    this.crosshair.classList.add("hidden");
    this.hint.classList.add("hidden");
    this.hidePrompt();

    this.lastFocused = document.activeElement as HTMLElement | null;
    document.addEventListener("keydown", this.onPanelKeydown);
    (this.panelLinks.querySelector("a") ?? this.panelClose).focus();
  }

  hidePanel(): void {
    this.panel.classList.add("hidden");
    document.removeEventListener("keydown", this.onPanelKeydown);
    this.lastFocused?.focus({ preventScroll: true });
    this.lastFocused = null;
  }

  isPanelOpen(): boolean {
    return !this.panel.classList.contains("hidden");
  }

  private onPanelKeydown = (event: KeyboardEvent): void => {
    if (event.key !== "Tab") return;
    const focusable = Array.from(this.panelCard.querySelectorAll<HTMLElement>("a[href], button:not([disabled])"));
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
}
