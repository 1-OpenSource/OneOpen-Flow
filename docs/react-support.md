# React support

React builds often change generated IDs, CSS module hashes, and MUI class names. Do not rely on generated CSS classes as primary locators.

## Recommendations

- Add `data-oneopen-id` on interactive elements
- Prefer role, accessible name, label, placeholder, and stable `data-*` attributes
- Use parent section / nearby text / table row context for disambiguation

## Wait modes

- Wait for React Render
- Wait for Element Stability
- Wait for Network Response
- Wait for Loading Indicator to Disappear
- Wait for Route Change

The engine accounts for client-side routing, hydration, Suspense, portals, virtualized lists, and async re-renders.
