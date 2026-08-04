import type { Activity } from "../types";

function el<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Missing #${id} element in index.html`);
  return found as T;
}

export class Overlay {
  private readonly blocker = el<HTMLDivElement>("blocker");
  private readonly crosshair = el<HTMLDivElement>("crosshair");
  private readonly prompt = el<HTMLDivElement>("prompt");
  private readonly panel = el<HTMLDivElement>("panel");
  private readonly panelTitle = el<HTMLHeadingElement>("panel-title");
  private readonly panelDescription = el<HTMLParagraphElement>("panel-description");
  private readonly panelLinks = el<HTMLDivElement>("panel-links");
  private readonly panelClose = el<HTMLButtonElement>("panel-close");
  private readonly logoutButton = el<HTMLButtonElement>("logout");
  private readonly hint = el<HTMLDivElement>("hint");

  onBlockerClick(handler: () => void): void {
    this.blocker.addEventListener("click", handler);
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
  }

  hidePanel(): void {
    this.panel.classList.add("hidden");
    this.crosshair.classList.remove("hidden");
  }

  isPanelOpen(): boolean {
    return !this.panel.classList.contains("hidden");
  }
}
