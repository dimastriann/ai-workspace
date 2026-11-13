# UI standards

These standards apply to `apps/web`. They keep the interface consistent, accessible, and
responsive as the app grows.

## Design tokens

- Use the CSS variables in `apps/web/app/globals.css` for color, spacing, radii, shadows,
  and transitions. Do not hard-code brand colors.
- Translucent overlays and tinted status backgrounds may use `rgba(...)` matching a token.
- Prefer `var(--transition-fast)` for hover/focus and `var(--transition-normal)` for layout.

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
- Choice lists use `Select` (a styled native select) with a `label` or an enclosing
  `<label>`. See `docs/ui.md` for the component contract.
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

Before closing a UI change, check the main flow at **360px, 768px, and 1280px** and run:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```
