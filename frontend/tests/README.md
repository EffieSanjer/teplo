# Tests

| Directory | Runner         | Command            | Contents                                                                                                            |
| --------- | -------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `unit/`   | Vitest + jsdom | `npm test`         | Component and helper tests. Subfolders mirror `src/` (`components/`, `pages/`, `shared/`, `integrations/`).         |
| `e2e/`    | Playwright     | `npm run test:e2e` | Browser scenarios against a running app. API calls are mocked, so no sessions or gifts are written to the database. |

Unit tests import code from `src/` via relative paths and are discovered by
`vite.config.ts` (`tests/unit/**/*.test.ts`). Playwright only looks at
`tests/e2e/*.spec.ts`, so it never picks up Vitest files. Shared helpers live in
`tests/e2e/support.ts`.

The e2e base URL defaults to `PUBLIC_BASE_URL` from the repository `.env`
(the nginx container rejects any other `Host`). Override it with
`PLAYWRIGHT_BASE_URL` when pointing at another running instance.
