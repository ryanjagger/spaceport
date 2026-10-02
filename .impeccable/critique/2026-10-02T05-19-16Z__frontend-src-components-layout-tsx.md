---
target: "top bar: logo text and menu"
total_score: 19
max_score: 28
na_heuristics: 5,9,10
p0_count: 0
p1_count: 2
target_identity: "file:/Users/ryan/projects/spaceport/frontend/src/components/Layout.tsx"
target_fingerprint: "sha256:3ee7bb057e8d1198076952157c11e701e8f25b18102a068f73cc1d3bf9e83eaa"
target_path: /Users/ryan/projects/spaceport/frontend/src/components/Layout.tsx
timestamp: 2026-10-02T05-19-16Z
slug: frontend-src-components-layout-tsx
---
Method: dual-agent (A: header-a · B: header-b)

Target: the top bar in `frontend/src/components/Layout.tsx` (brand text, two tabs, spaceport clock), inspected live on both routes from 320px to 1440px wide.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | The clock is simply absent while loading or if the time request fails. |
| 2 | Match System / Real World | 2 | Three names for one product; "CT" is never expanded. |
| 3 | User Control and Freedom | 3 | Both screens are one click away; the brand is not a home link. |
| 4 | Consistency and Standards | 2 | The bar's content starts at x=40 while the page column starts at x=170. |
| 5 | Error Prevention | n/a | The bar takes no input. |
| 6 | Recognition Rather Than Recall | 4 | Two text tabs, always visible, nothing hidden. |
| 7 | Flexibility and Efficiency | 2 | No skip link and no shortcut to switch screens. |
| 8 | Aesthetic and Minimalist Design | 3 | Clean; each tab label repeats as the page heading 70px below. |
| 9 | Error Recovery | n/a | The bar shows no errors. |
| 10 | Help and Documentation | n/a | Two destinations need no help. |
| **Total** | | **19/28** | **Acceptable (68%)** |

## Design Specificity Verdict

**LLM assessment.** This is any SaaS top bar with one exception: the clock. Brand text, two underlined tabs and a hairline are the category default, chosen on purpose. "Spaceport time 12:16 AM CT" is the only element that belongs to this product. The bar's weakness is imprecision: the naming disagrees with itself, the bar doesn't share the page's left edge, and it breaks at tablet and small-phone widths.

**Deterministic scan.** The CLI detector found 0 issues in `Layout.tsx`. The in-page detector flagged nothing in the header on either route. It reported one `repeating-stripes-gradient` on `/`, a false positive: it is the hourly gridlines in the booking lanes, outside the header.

Measurements confirm the bar is mechanically sound at 1440, 820 and 390px: no horizontal overflow, and tabs are at least 44px tall on a phone. The tab text sits 1px higher than the brand and clock text, caused by the tabs' 2px underline.

**Visual overlays.** On `/` the detector drew only a page-level banner across the top of the [Human] tab, with no per-element outlines. `/fleet` had nothing to draw.

## Overall Impression

The bar does its job and the clock is a good idea well executed. What it lacks is precision, and the first thing to settle is what the product is called. A logo would lock in whichever name sits beside it.

## What's Working

1. **The clock is server time, labelled and tabular.** It showed the correct Central time, with the value in ink at weight 600 and the label muted.
2. **The tabs are well built.** They fill the bar's height, the indigo underline sits flush on the hairline, the active tab carries `aria-current`, and the inset focus ring is fully visible by keyboard.
3. **Nothing is hidden.** Two text-labelled destinations, three groups, no menus.

## Priority Issues

**[P1] The bar breaks at tablet and small-phone widths**
- **Why it matters**: between about 641 and 814px the clock wraps to its own row, the header grows from 51 to 90px, and the active tab's underline is stranded mid-header. Below about 386px it becomes three rows and 134px.
- **Fix**: drop the "Charter desk" descriptor at about 860px instead of 640 (`Layout.module.css:77-80`), and hide the "Spaceport time" label below about 420px while keeping the time itself and a screen-reader label.
- **Suggested command**: `/impeccable adapt`

**[P1] The product has three names, and none is the one in PRODUCT.md**
- **Why it matters**: the bar says "Pacific Spaceport / Charter desk", the tab title says "Charter a ship · Pacific Spaceport", `index.html` says "Pacific Spaceport · Charter desk", and PRODUCT.md says "Spaceport Charter System". "Charter desk" also sits 28px from the "Charter a ship" tab in the same muted colour, so it reads like a third tab that does nothing.
- **Fix**: pick one name and use it everywhere. Then separate the descriptor from the tabs with a hairline divider or a smaller size.
- **Suggested command**: `/impeccable clarify`

**[P2] The bar and the page don't share a left edge**
- **Why it matters**: at 1440px the brand starts at x=40 and the clock ends at x=1400, while all page content sits in the 1180px column from x=170 to 1270.
- **Fix**: wrap the header's content in an inner element with the same `max-width: 1180px` as the main column, keeping the border and background full width.
- **Suggested command**: `/impeccable layout`

**[P2] The clock isn't marked up as a time and fails silently**
- **Why it matters**: it is a paragraph, not a `<time>` element, and it is absent while loading and on error, so the bar's right side is empty and shifts when it arrives.
- **Fix**: use `<time dateTime>`, reserve its width, and show "Spaceport time unavailable" in muted text on error (`Layout.tsx:35-38`).
- **Suggested command**: `/impeccable harden`

## The logo

Recommendation: don't ship the pasted rocket mark, and don't trace it. Add a favicon first, and only add a mark to the bar if it is one the user owns.

- **Provenance blocks it.** It was pasted as an image of unknown origin and licence. A redraw of someone else's mark inherits the same problem.
- **It contradicts the system as drawn.** Gradients, translucent overlap and fading exhaust on a black ground, against a flat, hairline, one-accent, light-ground system. At 20 to 28px the detail is lost.
- **It would be a second rocket.** The Book charter button already has Phosphor's `RocketLaunch`.
- **The real identity gap is the browser tab.** `index.html` declares no favicon.
- **A good version:** one solid silhouette in a single tone, no gradients or transparency, drawn on a 24px grid and tested at 16px; shipped first as an SVG favicon, then at 20px before the name inside a home link.

## Persona Red Flags

**Alex (power user)**: no keyboard shortcut to flip between Charter and Fleet. The clock refreshes once a minute with no sign of when it was last heard.

**Sam (accessibility-dependent)**: no skip link. The clock reads as three fragments and "CT" is never expanded. The labelled nav, `aria-current` and focus rings all pass.

**Casey (mobile)**: at 390px the bar is two rows and 95px, which works. At 375px and below it is three rows and 134px. The bar isn't sticky, so the tabs and clock are gone once Casey scrolls.

## Minor Observations

- "Spaceport time" renders at weight 400; `DESIGN.md`'s label style is 500.
- "Charter desk" is the same size as the brand name.
- `index.html` shows a different title for a moment before the app sets the per-route one.
- The tab text sits 1px above the brand and clock text.

## Questions to Consider

- If the clock is the only thing in the bar that is this product's, should it be the identity, with no mark at all?
- With two destinations, does the bar need tabs, or would a switch beside the page heading let the bar shrink to name and clock?
- Is wanting a rocket a sign that "no themed space motif" was the wrong commitment?
