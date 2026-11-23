# Interface styles

Tailwind CSS 4 is connected through `@tailwindcss/vite`. The only stylesheet
imported by the app is `src/styles/index.css`; it acts as an aggregate entry
point and contains no rules of its own.

| File                        | Responsibility                                                                                                            |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `theme.css`                 | Tailwind CSS-first configuration: `@theme` tokens and the `dark` variant. This is the `tailwind.config` equivalent in v4. |
| `base.css`                  | `@layer base`: theme variables and element defaults.                                                                      |
| `components/controls.css`   | Shared buttons, states, empty states and loading placeholders.                                                            |
| `components/collection.css` | Wishlist collection headings, grid and archive.                                                                           |
| `components/friends.css`    | Friends directory, invitations and circle layout.                                                                         |
| `components/forms.css`      | Wish editor, photo upload and price controls.                                                                             |
| `components/feedback.css`   | Transient notifications.                                                                                                  |
| `components/auth.css`       | Login and welcome-screen cards.                                                                                           |
| `transitions.css`           | Dialog backdrop, Vue transition classes and reduced-motion rules.                                                         |
| `welcome.css`               | Entry page layout.                                                                                                        |
| `scoped/`                   | Component-scoped styles referenced directly from SFCs.                                                                    |

Keep theme values in `theme.css` and shared `@apply` classes in `components/`.
Layout and responsive rules belong in Vue templates as utility classes. Plain
CSS is limited to theme variables, dialog backdrops and Vue transition
lifecycle selectors. Do not reintroduce the old cascading stylesheets: their
high-specificity selectors conflict with component layout and avatar
dimensions.

ItemDetail.vue measures dimensions only when the viewport or content changes.
Gesture animation paints one compositor transform per frame without reactive
updates or layout reads in the animation loop.
