import type { Activity } from "../types";

function el<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Missing #${id} element in index.html`);
  return found as T;
}

export class Overlay {
  private readonly blocker = el<HTMLDivElement>("blocker");
  private readonly enterButton = el<HTMLButtonElement>("enter-button");
  private readonly activityList = el<HTMLUListElement>("activity-list");
  private readonly crosshair = el<HTMLDivElement>("crosshair");
  private readonly prompt = el<HTMLDivElement>("prompt");
  private readonly panel = el<HTMLDivElement>("panel");
  private readonly panelCard = el<HTMLDivElement>("panel-card");
  private readonly panelTitle = el<HTMLHeadingElement>("panel-title");
  private readonly panelDescription = el<HTMLParagraphElement>("panel-description");
  private readonly panelLinks = el<HTMLDivElement>("panel-links");
  private readonly panelClose = el<HTMLButtonElement>("panel-close");
  private readonly logoutButton = el<HTMLButtonElement>("logout");
  private readonly hint = el<HTMLDivElement>("hint");
  private lastFocused: HTMLElement | null = null;

  onBlockerClick(handler: () => void): void {
    this.enterButton.addEventListener("click", handler);
  }

  renderActivityList(activities: Activity[]): void {
    this.activityList.replaceChildren(
      ...activities.map((activity) => {
        const item = document.createElement("li");

        const heading = document.createElement("h3");
        heading.textContent = activity.name;

        const description = document.createElement("p");
        description.textContent = activity.description;

        const links = document.createElement("div");
        links.className = "activity-links";
        links.append(
          ...activity.links.map((link) => {
            const a = document.createElement("a");
            a.href = link.url;
            a.textContent = link.label;
            a.target = "_blank";
            a.rel = "noopener";
            return a;
          }),
        );

        item.append(heading, description, links);
        return item;
      }),
    );
  }

  onPanelClose(handler: () => void): void {
    this.panelClose.addEventListener("click", handler);
  }

  onLogout(handler: () => void): void {
    this.logoutButton.addEventListener("click", handler);
  }

  showBlocker(): void {
    this.blocker.classList.remove("hidden");
    this.crosshair.classList.add("hidden");
    this.prompt.classList.add("hidden");
    this.hint.classList.add("hidden");
  }

  hideBlocker(): void {
    this.blocker.classList.add("hidden");
    this.crosshair.classList.remove("hidden");
    this.hint.classList.remove("hidden");
  }

  showLogout(): void {
    this.logoutButton.classList.remove("hidden");
  }

  showPrompt(activity: Activity): void {
    this.prompt.textContent = `Press E — ${activity.name}`;
    this.prompt.classList.remove("hidden");
  }

  hidePrompt(): void {
    this.prompt.classList.add("hidden");
  }

  showPanel(activity: Activity): void {
    this.panelTitle.textContent = activity.name;
    this.panelDescription.textContent = activity.description;
    this.panelLinks.replaceChildren(
      ...activity.links.map((link) => {
        const a = document.createElement("a");
        a.href = link.url;
        a.textContent = link.label;
        a.target = "_blank";
        a.rel = "noopener";
        return a;
      }),
    );
    this.panel.classList.remove("hidden");
    this.crosshair.classList.add("hidden");
    this.prompt.classList.add("hidden");
    this.hint.classList.add("hidden");

    this.lastFocused = document.activeElement as HTMLElement | null;
    document.addEventListener("keydown", this.onPanelKeydown);
    this.panelClose.focus();
  }

  hidePanel(): void {
    this.panel.classList.add("hidden");
    this.crosshair.classList.remove("hidden");

    document.removeEventListener("keydown", this.onPanelKeydown);
    this.lastFocused?.focus();
    this.lastFocused = null;
  }

  isPanelOpen(): boolean {
    return !this.panel.classList.contains("hidden");
  }

  private onPanelKeydown = (event: KeyboardEvent): void => {
    if (event.key !== "Tab") return;

    const focusable = Array.from(
      this.panelCard.querySelectorAll<HTMLElement>("a[href], button:not([disabled])"),
    );
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
