# UI standards

These standards apply to `apps/web`. They keep the interface consistent, accessible, and
responsive as the app grows.

## Design tokens

- Use the CSS variables in `apps/web/app/globals.css` for color, spacing, radii, shadows,
  and transitions. Do not hard-code brand colors.
- Dark tokens live on `:root`; light tokens override them on `:root[data-theme="light"]`.
  Tinted surfaces, overlays, status backgrounds, and glass use semantic tokens so both
  themes stay correct.
- Prefer `var(--transition-fast)` for hover/focus and `var(--transition-normal)` for layout.

## Theme

- Users can choose **system**, **light**, or **dark** from the header toggle. The preference
  is stored in `localStorage.theme`.
- A pre-paint script sets `data-theme` and `color-scheme` on `<html>` to avoid a flash;
  the toggle keeps them in sync and follows OS changes while in system mode.
- Never hard-code white/black surfaces in new components; use the token palette.
- Verify new UI in both themes, not only the default dark theme.

## Layout and breakpoints

| Name | Width | Behavior |
| --- | --- | --- |
| Mobile | `< 640px` | Single column, sidebar drawer, tables become cards, 16px page padding |
| Tablet | `640–1023px` | Two-column grids where useful, tables scroll horizontally |
| Desktop | `>= 1024px` | Persistent sidebar, full grids, 24px page padding |

- The sidebar is fixed at `var(--sidebar-width)` on desktop. Below `769px` it becomes a
  drawer opened from the header menu button. It closes on navigation, `Escape`, or a
  backdrop click, and reports `aria-expanded`/`aria-controls`.
- Main content uses `margin-left: var(--sidebar-width)` on desktop and full width on mobile.
- Tables use `data-label` on cells so the same markup collapses into cards at mobile size.

## Controls

- Reuse the primitives in `apps/web/components/ui`: `Button`, `Card`, `Modal`, `Select`,
  `Switch`.
- Booleans use `Switch` (`role="switch"`, `aria-checked`), never a raw checkbox. Always
  provide a meaningful `label`.
- Choice lists use `Select`, an accessible custom listbox (`role="combobox"` trigger,
  `role="listbox"` popup, arrow/Home/End/Enter/Escape keys). The popup is portaled so it
  is not clipped by scrolling containers.
- Text inputs keep a visible label. Use `type="password"` for secrets and never prefill
  masked values.
- Destructive actions require a confirm `Modal` that names the target and the consequence.
- Status is conveyed with text and color, not color alone.

## Accessibility

- Every control is keyboard reachable and has a visible `:focus-visible` outline.
- Mobile touch targets are at least 44px. Desktop controls target at least 40px.
- Icon-only buttons need an `aria-label`.
- Drawers and modals must be dismissible with `Escape` and restore background scrolling.
- Maintain readable contrast on the dark background; use the neutral text tokens instead
  of arbitrary grays.

## Verification

Before closing a UI change, check the main flow at **360px, 768px, and 1280px** in both
light and dark themes, then run:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```
