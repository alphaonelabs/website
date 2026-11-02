#!/usr/bin/env python3
"""Check CSS custom properties against design-system/tokens.json."""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CSS_PATH = ROOT / "brand.css"
TOKENS_PATH = ROOT / "tokens.json"

COLOR_MAP = {
    "black": "black",
    "ink": "ink",
    "white": "white",
    "gold": "primary",
    "gold-hover": "primary-hover",
    "gold-dark": "primary-on-dark",
    "gold-ink": "primary-ink",
    "gold-deep": "gold-deep",
    "red": "red",
    "gray-50": "gray-50",
    "gray-100": "gray-100",
    "gray-200": "gray-200",
    "gray-300": "gray-300",
    "gray-400": "gray-400",
    "gray-500": "gray-500",
    "gray-600": "gray-600",
    "gray-700": "gray-700",
    "gray-800": "gray-800",
    "gray-900": "gray-900",
}

THEME_MAP = {
    "bg": "a1-bg",
    "surface-raised": "a1-surface-raised",
    "border": "a1-border",
    "border-strong": "a1-border-strong",
    "text": "a1-text",
    "text-muted": "a1-text-muted",
    "accent": "a1-accent",
    "accent-fill": "a1-accent-fill",
    "on-accent": "a1-on-accent",
}


def declarations(block: str) -> dict[str, str]:
    return {
        name: value.strip()
        for name, value in re.findall(
            r"--([a-zA-Z0-9-]+)\s*:\s*([^;]+);", block
        )
    }


def first_block(css: str, selector: str) -> dict[str, str]:
    match = re.search(
        rf"{re.escape(selector)}\s*\{{([^{{}}]*)\}}",
        css,
        flags=re.DOTALL,
    )
    return declarations(match.group(1)) if match else {}


def resolve(value: str, variables: dict[str, str]) -> str:
    seen = set()
    while "var(--" in value and value not in seen:
        seen.add(value)
        names = re.findall(r"var\(--([a-zA-Z0-9-]+)\)", value)
        if not names:
            break
        for name in names:
            value = value.replace(
                f"var(--{name})",
                variables.get(name, f"var(--{name})"),
            )
    return value.strip().lower()


def normalize(value: str) -> str:
    return value.strip().lower()


def main() -> int:
    css = CSS_PATH.read_text(encoding="utf-8")
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    root = first_block(css, ":root")
    light = root
    dark_match = re.search(
        r'\[data-a1-theme="dark"\]\s*\{([^{}]*)\}',
        css,
        flags=re.DOTALL,
    )
    dark = {**root, **declarations(dark_match.group(1))} if dark_match else root

    mismatches = []

    for css_suffix, token_key in COLOR_MAP.items():
        css_name = f"a1-{css_suffix}"
        css_value = root.get(css_name)
        json_value = tokens.get("color", {}).get(token_key)
        if css_value is None:
            mismatches.append(f"Missing CSS token --{css_name}")
        elif json_value is None:
            mismatches.append(f"Missing tokens.json color.{token_key}")
        else:
            css_color = resolve(css_value, root)
            if not re.fullmatch(r"#[0-9a-f]{6}", css_color):
                mismatches.append(f"CSS --{css_name} is not a hex color: {css_value}")
            elif normalize(css_color) != normalize(json_value):
                mismatches.append(
                    f"Color mismatch: --{css_name}={css_color}, "
                    f"color.{token_key}={normalize(json_value)}"
                )

    for theme_name, variables in (("light", light), ("dark", dark)):
        token_theme = tokens.get("theme", {}).get(theme_name, {})
        for token_key, css_name in THEME_MAP.items():
            css_value = variables.get(css_name)
            json_value = token_theme.get(token_key)
            if css_value is None:
                mismatches.append(
                    f"Missing CSS token --{css_name} in {theme_name} theme"
                )
            elif json_value is None:
                mismatches.append(
                    f"Missing tokens.json theme.{theme_name}.{token_key}"
                )
            else:
                css_color = resolve(css_value, variables)
                if not re.fullmatch(r"#[0-9a-f]{6}", css_color):
                    mismatches.append(
                        f"CSS --{css_name} is not a resolved hex color: {css_value}"
                    )
                elif normalize(css_color) != normalize(json_value):
                    mismatches.append(
                        f"Theme mismatch ({theme_name}): --{css_name}={css_color}, "
                        f"theme.{theme_name}.{token_key}={normalize(json_value)}"
                    )

    if mismatches:
        print("Design system token mismatches:")
        for mismatch in mismatches:
            print(f"- {mismatch}")
        return 1

    print("Design system tokens are in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
