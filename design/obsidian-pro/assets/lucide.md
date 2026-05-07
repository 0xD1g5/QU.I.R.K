# Lucide icons

The Obsidian Pro system uses Lucide as its primary icon set.

## Loading

```html
<script src="https://unpkg.com/lucide@latest"></script>
<script>lucide.createIcons();</script>
```

Or as ES modules / React via `lucide-react` if you have a build step.

## Inline usage

```html
<i data-lucide="alert-triangle" width="16" height="16"></i>
```

After the page loads + `lucide.createIcons()` runs, the `<i>` is replaced with an SVG.

## Sizes

- 14px — inline with body text
- 16px — default UI
- 18px — nav rail
- 20px — hero / empty state

## Color

Always inherits `currentColor`. Default to `--fg2`; use `--ds-accent` only on active nav, primary CTAs, or severity-tinted chips (where the chip's color cascades).

## Stroke

Default Lucide stroke weight is 1.5px — leave it alone. Do not set `stroke-width="2"`.
