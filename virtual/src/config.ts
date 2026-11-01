const DEFAULT_LEARN_API_BASE = "https://learn.alphaonelabs.com";

function resolveLearnApiBase(): string {
  const raw = import.meta.env.VITE_LEARN_API_BASE;
  if (!raw) return DEFAULT_LEARN_API_BASE;

  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(`VITE_LEARN_API_BASE is not a valid URL: ${raw}`);
  }

  if (parsed.protocol !== "https:") {
    throw new Error(`VITE_LEARN_API_BASE must use https: got ${raw}`);
  }

  return raw;
}

export const LEARN_API_BASE: string = resolveLearnApiBase();
