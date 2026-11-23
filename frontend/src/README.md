# Frontend structure

| Directory       | Responsibility                                                                                                                                                  |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pages/`        | Route-level components: `WishlistPage`, `FriendsPage`.                                                                                                          |
| `components/`   | All Vue SFCs: wish cards/forms/details, certificate views, friend profile and shared UI (`Modal`, `MasonryGrid`, `WishImage`, `ThemeControl`, `StartupScreen`). |
| `shared/`       | Framework-independent logic: API client, theme, avatars, invitations, palettes, link parsing, diagnostics.                                                      |
| `integrations/` | Telegram Mini App integration.                                                                                                                                  |
| `styles/`       | Tailwind entry point, theme/config, layered styles and component-scoped CSS (see `styles/README.md`).                                                           |

Tests are kept outside `src/` in `tests/unit/` (see `tests/README.md`).

Rules of thumb:

- Components import each other from `components/`; pages import from `components/` and `shared/`.
- Only `shared/` and `integrations/` hold reusable non-visual logic.
- Add shared `@apply` classes to `styles/components/`, not to new global stylesheets.
- If a component moves, move its test in `tests/unit/` to the matching subfolder.
