# Locales

Message catalogs for the learn frontend, one JSON file per language
(`en.json`, `es.json`, ...). They are loaded by `public/js/i18n.js`.

## Conventions

- Keys are flat and prefixed by page or area, for example `login.submit` or
  `common.loading`.
- `en.json` is the source of truth. Other languages may be incomplete: a
  missing key falls back to English, then to the text already in the HTML.
- Placeholders use `{name}` style, for example `"Hello {name}"`.
- Values are plain text. They are applied with `textContent`, so HTML in a
  value is shown literally.

## Adding a string

1. Add the key and English text to `en.json`.
2. Tag the element, keeping the English text as the default:

   ```html
   <span data-i18n="login.welcome">Welcome back!</span>
   <input data-i18n-placeholder="login.username_placeholder" placeholder="username">
   ```

3. In JavaScript, use `i18n.t("login.welcome", "Welcome back!")`.

## Notes

- Elements that contain an icon should keep the icon outside the tagged
  element, because `textContent` replaces all child nodes.
- Scripts can wait for translation with
  `document.addEventListener("i18n:ready", ...)`.