# Design

Source: the look of native.no/no (values only: no name, logo, copy or pictures), extracted 2026-11-05 with designlang 13.3.2 plus computed styles in Chrome; checked by eye at 1440 px. Dark only: the source has no light theme.

## Colour
| Role | Dark (only theme) |
|---|---|
| ground | #0F1420 (night navy) |
| ground-deep | #0A0E18 (sky top, footer) |
| surface | #1A2133 |
| surface-glass | rgba(30, 38, 58, 0.92) |
| ink | #F4F1E6 (cream) |
| ink-soft | #E8E4D2 (body text) |
| muted | #B3B9C8 |
| dim (inactive headings) | rgba(244, 241, 230, 0.32) |
| accent | #E9B638 (gold) |
| accent-ink | #0F1420 |
| border | rgba(195, 210, 240, 0.16) |
| focus | #E9B638 |
| good | #7FC79A |
| warning | #E9B638 |
| bad | #E5735C |

Primary button: cream fill (#F4F1E6) with navy text. Gold is for emphasis (italic headline words, link underlines, one live highlight).

## Type
- Display: **EB Garamond** 500 (Google Fonts), italic 500 for the emphasised line. The source uses a self-hosted Garamond subset; EB Garamond is its own fallback.
- Text: **Inter** 400/500/600 (Google Fonts).
- Scale: display 88 px / 1.0 / -0.02em (clamp to 48 on phones) · h2 52 px / 1.05 · h3 30 px / 1.05 / -0.015em · lead 20 px / 1.5 · body 16 px / 1.5 · small 14 px / 1.5.

## Spacing, radius, motion
- Spacing: 4, 8, 12, 16, 24, 32, 48, 64, 96, 112 (section rhythm), container 1200 px, gutter 24 px (16 on phones).
- Radius: 12 px (buttons, inputs), 20 px (cards), full (chips).
- Motion: 200 ms, 450 ms, 800 ms; ease-out cubic-bezier(0.22, 1, 0.36, 1), spring cubic-bezier(0.34, 1.56, 0.64, 1).

## Decisions
- Dropped from extraction: LinkedIn blue #0A66C2 and orange #D0770A (third-party widgets), the 11 radius values (kept 3), odd spacings (55, 126, 166, 206, 252 are layout widths), gradients beyond one night-sky field.
- The painted landscape hero is replaced by a sky and fjord silhouette drawn in SVG, so no source imagery is used.
