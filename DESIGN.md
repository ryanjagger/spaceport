---
name: Spaceport Charter System
description: A bright, quiet booking desk for five charter ships, where colour only ever means a state.
colors:
  accent: "#4b4fd9"
  accent-hover: "#3d40bf"
  accent-soft: "#ecedfd"
  accent-fill: "#c5c8f6"
  accent-ink: "#3033a3"
  refuel: "#8a4708"
  refuel-soft: "#fdf1d8"
  refuel-fill: "#f3cd7c"
  danger: "#b42318"
  danger-hover: "#912018"
  danger-soft: "#feecea"
  ok: "#16703f"
  ok-soft: "#e5f5ec"
  ground: "#f6f7f9"
  surface: "#ffffff"
  ink: "#1a1f2c"
  muted: "#5c6577"
  line: "#e1e4ea"
  line-strong: "#858e9f"
  past-soft: "#eef0f3"
typography:
  display:
    fontFamily: "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  title:
    fontFamily: "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.005em"
  subtitle:
    fontFamily: "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.25
  body:
    fontFamily: "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "'tnum'"
  body-small:
    fontFamily: "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.5
  caption:
    fontFamily: "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  block: "4px"
  radius: "6px"
  radius-lg: "10px"
  pill: "999px"
spacing:
  hairline-gap: "6px"
  tight: "8px"
  snug: "12px"
  base: "16px"
  panel: "20px"
  section: "28px"
  columns: "32px"
  gutter: "clamp(16px, 4vw, 40px)"
components:
  button:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.radius}"
    padding: "0 16px"
    height: "40px"
  button-hover:
    backgroundColor: "{colors.ground}"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.radius}"
    padding: "0 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-primary-disabled:
    backgroundColor: "{colors.past-soft}"
    textColor: "{colors.muted}"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.surface}"
    rounded: "{rounded.radius}"
    padding: "0 16px"
    height: "40px"
  button-danger-hover:
    backgroundColor: "{colors.danger-hover}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.radius}"
    padding: "0 12px"
    height: "40px"
  nav-link:
    textColor: "{colors.muted}"
    padding: "0 12px"
    height: "44px"
  nav-link-active:
    textColor: "{colors.ink}"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.radius-lg}"
    padding: "20px"
  slot:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.radius}"
    padding: "5px 8px"
    height: "48px"
  slot-hover:
    backgroundColor: "{colors.accent-soft}"
  slot-selected:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
  slot-booked:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent-ink}"
  slot-refuel:
    backgroundColor: "{colors.refuel-soft}"
    textColor: "{colors.refuel}"
  slot-past:
    backgroundColor: "{colors.past-soft}"
    textColor: "{colors.muted}"
  lane-selected:
    backgroundColor: "{colors.accent-soft}"
  block-booked:
    backgroundColor: "{colors.accent-fill}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.block}"
    padding: "0 6px"
  block-refuel:
    backgroundColor: "{colors.refuel-fill}"
    rounded: "{rounded.block}"
  block-pick:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.block}"
    padding: "0 6px"
  notice-success:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.radius}"
    padding: "10px 14px"
  notice-error:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.radius}"
    padding: "10px 14px"
  pill-today:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  pill-cancelled:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    rounded: "{rounded.pill}"
    padding: "1px 8px"
---

# Design System: Spaceport Charter System

## Overview

**Creative North Star: "The Bright Desk"**

This is the category standard for an operations tool, chosen on purpose: white surfaces on a very light cool grey ground, hairline borders, near-black ink and a single indigo accent. The craft bar is Linear and the Stripe Dashboard. The setting it is built for is a dispatcher at a desk in a bright office, often on the phone with a pilot, so everything is legible at a glance and nothing asks for attention it has not earned. There is no themed motif; the ships' names are the only space in the room.

Density is moderate and steady. Body text is 15px, controls are 40px tall on a desk and 44px on a phone, and the whole fleet's day sits on one shared 6 AM to 10 PM scale. Colour is spent on meaning only: a tint says what a stretch of time is, and the same tint says the same thing on both screens. Every state colour is paired with words, so the screen still reads with the colour removed.

Motion is nearly absent. Hover states ease a background or border over 120ms; the loading skeleton shimmers; nothing enters, slides or bounces, and reduced-motion turns all of it off.

**Key Characteristics:**
- White cards on a cool grey ground, separated by 1px hairlines rather than shadow.
- One indigo accent, kept for the selection, the active nav tab and the primary button.
- State colours with a text label alongside: indigo tint booked, amber refuel, grey past, green success, red danger and now.
- Inter with tabular figures, so times line up in columns and never shift width.
- 6px radii on controls, 10px on containers, 4px on timeline blocks.
- Flat at rest; shadow only on things that float over the page.

## Colors

A neutral cool-grey field with one indigo voice and a small set of state colours that each mean exactly one thing.

### Primary
- **Dispatch Indigo** (`accent`): the selection ("Your pick" on a lane and the chosen start time), the active nav tab's underline, the primary button, focus rings, and native control accent and caret. Darkens to `accent-hover` under the pointer.
- **Indigo Tint** (`accent-fill`): booked. The fill of a booking block on a timeline, on both screens, and the text selection colour.
- **Indigo Wash** (`accent-soft`): the quiet form of the same family. Background of an unavailable start time that is booked, of the selected ship's lane, of an open start time on hover, and of the "today" pill.
- **Indigo Ink** (`accent-ink`): text on the two tints above (pilot names on blocks, "Booked" on a start time).

### Secondary
- **Refuel Amber** (`refuel-fill`, `refuel-soft`, `refuel`): refuel time. `refuel-fill` is the block after each booking on a timeline; `refuel-soft` is the background of a start time lost to refuelling; `refuel` is the dark amber text that sits on it.

### Tertiary
- **Signal Red** (`danger`, `danger-hover`, `danger-soft`): the now marker on the day lanes, the destructive button, the error notice border, and the "Cancelled" pill.
- **Confirm Green** (`ok`, `ok-soft`): the success notice's border and background, and nothing else.

### Neutral
- **Cool Ground** (`ground`): the page background, and the hover fill of a secondary button or a lane.
- **Surface White** (`surface`): the top bar, cards, panels, inputs, buttons, the dialog, and text on solid indigo or red.
- **Desk Ink** (`ink`): all primary text; an input's border on hover; the focus ring on a booking block, where indigo on indigo would vanish.
- **Slate Muted** (`muted`): secondary text, field labels, axis and hour labels, captions, inactive nav tabs, disabled text.
- **Hairline** (`line`): borders of cards and panels, row dividers, the hourly rules on a timeline track.
- **Control Edge** (`line-strong`): borders of things you type into or click (inputs, buttons, open start times) and the dashed edge of an empty state. It holds 3:1 against both ground and surface.
- **Past Grey** (`past-soft`): past. The background of a start time that has gone by, and of a disabled primary button.

### Named Rules
**The Tint Means Booked Rule.** Indigo tint is a booking on both screens. Solid indigo is never a booking; it is the one thing the user has chosen, the tab they are on, or the button that commits.

**The Colour Plus Words Rule.** No state is carried by colour alone. Every tinted start time prints its reason ("Booked", "Refuel time", "Past"), every timeline has a legend in text, and pills contain their word.

**The One Meaning Rule.** Each state colour has one job: amber is refuel, grey is past, green is success, red is now or destructive. A new state gets a new label first and a colour only if none of these already fits.

## Typography

**Display Font:** Inter Variable (with system-ui, -apple-system, Segoe UI, sans-serif)
**Body Font:** Inter Variable (same stack)

**Character:** One family doing every job, separated by weight (400, 500, 600) and a tight size ramp rather than by a second face. Tabular figures are on for the whole document, because nearly everything on screen is a time.

### Hierarchy
- **Display** (600, 1.75rem, 1.15, -0.02em): the departure time in the "Your charter" panel. The one value to check before booking, so the largest thing on the page. Used once per screen.
- **Headline** (600, 1.5rem, 1.25, -0.015em): the page title.
- **Title** (600, 1.0625rem, 1.25, -0.005em): section headings ("The fleet on Fri, Oct 2", "Start times for USS Wanderer", "Your charter", the dialog heading).
- **Subtitle** (600, 0.875rem, 1.25): ship names heading a group in the fleet list. The same size at weight 600 is the time on a start-time button.
- **Body** (400, 0.9375rem, 1.5): default text, control text, list entries. Weight 500 marks buttons, nav tabs, summary values and notices; weight 600 marks ship names and the live clock. Running prose is capped at 70ch.
- **Body small** (400, 0.875rem, 1.5): captions under a heading and hints in the charter panel, in muted.
- **Label** (500, 0.8125rem, 1.5): field labels above inputs, the "Departs" label, open-start counts, legends, the clock's "Spaceport time", all in muted and sentence case.
- **Caption** (400, 0.75rem): axis ticks, hour labels, the second line of a start time. At weight 600 it is the pilot name on a block and the text in a pill.

### Named Rules
**The Tabular Rule.** `font-variant-numeric: tabular-nums` is set on the body. Times align in columns and do not shift width when they change.

**The Three Weights Rule.** 400 reads, 500 acts, 600 names. Nothing is lighter than 400 or heavier than 600.

## Layout

A white top bar runs full width with the product name left, two nav tabs, and the live spaceport clock pushed right. Below it the page is a single centred column, 1180px at most, with a fluid side gutter (`gutter`) and 28px above and 64px below.

Inside the column, content stacks in sections separated by 20 to 32px. Related controls sit 10 to 16px apart; a label sits 6px above its input. The charter screen ends in two columns: a fluid main column and a 320px panel, 32px apart, with the panel sticky 16px from the top. Grids are fluid by content rather than by breakpoint where possible: filters and start-time periods use `auto-fit` columns (180 to 220px for filters, 226px minimum for periods, 260px minimum for fleet list groups).

Timelines share one model: a name column, then a track divided by one hairline rule per hour, sixteen across, with blocks positioned by percentage of the operating day. Start times are grouped Morning, Afternoon, Evening, each row an hour label followed by fixed :00 and :30 columns so the halves line up down the page.

Responsive behaviour:
- **At 860px and below** the charter columns stack, and the "Your charter" panel becomes a bar pinned to the bottom edge, full bleed, showing the pick on one line with the pilot field and Book button beside each other. Controls grow to 44px and input text to 16px so phones do not zoom.
- **At 760px and below** each ship's name sits above its own lane, every other axis tick is hidden, and tracks shorten from 48px to 36px. On the fleet dashboard the timeline is hidden and the grouped list is the view.
- **At 640px and below** the nav tabs wrap to their own row under the brand and clock, and the "Charter desk" descriptor is dropped.

Touch targets are at least 44px tall for nav tabs, list entries and toggles; start-time buttons are 48px.

## Elevation & Depth

Flat by default. Surfaces are told apart by tone (white on cool grey) and a 1px hairline, never by a resting shadow. Shadow is reserved for things that float over the page.

### Shadow Vocabulary
- **Overlay** (`box-shadow: 0 12px 32px -8px rgb(26 31 44 / 0.22), 0 2px 6px -2px rgb(26 31 44 / 0.12)`): the booking details dialog, over a backdrop of ink at 45%.
- **Pinned bar** (`box-shadow: 0 -10px 24px -14px rgb(26 31 44 / 0.3)`): the charter panel when it is pinned to the bottom of a phone, cast upward so content scrolls beneath it.

### Named Rules
**The Floats Only Rule.** If it sits in the page flow, it has a hairline and no shadow. If it floats over the page, it has a shadow.

## Shapes

Gently rounded and consistent. Controls (inputs, buttons, start times, notices) take 6px; containers (cards, panels, the dialog, empty states) take 10px; blocks on a timeline take 4px, and a refuel block is square on its left edge so it reads as attached to the booking before it. Pills (the "today" and "Cancelled" tags) are fully round. Legend swatches are small 2px-radius chips.

Borders are 1px. Containers use the hairline; interactive edges use the stronger control edge. A dashed control-edge border marks an empty or error state card. The active nav tab is a 2px indigo underline flush with the bottom of the top bar. The now marker is a 2px red vertical line the full height of a track.

Focus is a 2px indigo outline offset 2px. It moves inside the element where an outer ring would be clipped (nav tabs, lanes), and switches to ink on booking blocks.

## Components

### Buttons
Quiet and square-shouldered; the primary is the only solid thing on the page until something is selected.
- **Shape:** gently rounded (6px), 40px tall, 16px side padding, weight 500, single line. 44px tall at 860px and below.
- **Secondary (default):** white with a control-edge border and ink text. Hover fills with the ground grey over 120ms ease-out.
- **Primary:** solid indigo with white text and a matching border; hover darkens to `accent-hover`. One per view ("Book charter").
- **Danger:** solid red with white text; hover darkens. Appears only as the second step of a confirm ("Yes, cancel booking"); the first step is a secondary button.
- **Disabled:** secondary drops to a hairline border and muted text. Primary becomes past grey with muted text, so it still reads as the button it will become. Cursor is not-allowed.

### Inputs / Fields
- **Style:** white, control-edge border, 6px radius, 40px tall, 12px side padding. Native date, select and text inputs share it. The label sits 6px above in the label style.
- **Hover:** border darkens to ink.
- **Focus:** the global 2px indigo outline, offset 2px.
- **Narrow screens:** 44px tall with 16px text.

### Navigation
A white top bar with a hairline beneath. Tabs are body text at weight 500, muted, 44px tall with 12px side padding. Hover turns the text to ink; the active tab is ink with a 2px indigo underline. The brand is weight 600 with a muted descriptor beside it. The clock at the far right is a muted label followed by the time in ink at weight 600.

### Cards / Containers
- **Corner Style:** 10px.
- **Background:** white on the grey ground.
- **Shadow Strategy:** none at rest (see Elevation & Depth).
- **Border:** 1px hairline.
- **Internal Padding:** 20px for a panel, 24px for the dialog and empty states. The day lanes card has no padding; its rows run edge to edge with a 16px inset.

### Notices and state cards
- **Notice:** 6px radius, 10px by 14px padding, weight 500, a 1px border in the state colour over its soft tint: green for success, red for error. Ink text.
- **Empty, error and loading:** a white card with a dashed control-edge border, a weight 600 title, and actions as secondary buttons. Loading is a stack of 44px bars with a slow hairline-to-ground shimmer.

### Pills
Fully round, caption size at weight 600. "Today" is indigo ink on indigo wash; "Cancelled" is red on its soft tint.

### Day lanes (signature)
The whole fleet's day before a ship is chosen. A white card of five rows on one shared scale. Each row is a single radio target: a 16px radio, the ship name at weight 600, the count of open starts in muted, then a 48px track with hourly hairlines. Booked stretches are indigo-tint blocks carrying the pilot name in indigo ink; an amber block follows each for refuel time; the user's selection paints as a solid indigo block with its start time in white; a red line marks now. A block too narrow for its label (56px or less) hides it. Hover fills the row with ground grey; the selected row fills with indigo wash. A text legend closes the card.

The fleet dashboard uses the same model read-only on rows: taller 56px tracks, booking blocks that are buttons showing pilot name and times (times drop when the block is 120px or narrower), hover deepening the tint toward indigo.

### Start-time grid (signature)
Start times in Morning, Afternoon and Evening columns under muted, hairline-underlined period headings. Each is a 48px two-line button: the start time at weight 600, the end time beneath in caption. Open times are white with a control edge and go indigo wash with an indigo border on hover. The selected time is solid indigo with white text. Unavailable times lose their border, drop the time to weight 400, and print the reason at weight 500 on the matching tint: indigo wash for booked, soft amber for refuel, past grey for past.

### Charter panel (signature)
A 320px white card, sticky beside the grid. It leads with a muted "Departs" label over the departure time in the display style, then a two-column summary (muted term left, weight 500 value right-aligned) above a hairline, then the pilot field and the primary button at full width. On phones it becomes the pinned bottom bar described in Layout, and hides the field and button until a time is picked.

### Booking details dialog
A native dialog, at most 460px wide, 24px padding, 10px radius, hairline border and the overlay shadow. A two-column facts list sits under a hairline; actions wrap in a row with Close pushed to the far right. Cancelling is two steps, with the confirmation sentence above the danger button.

## Do's and Don'ts

### Do:
- **Do** keep solid indigo (`accent`) for the selection, the active nav tab and the primary button. Use the tints for booked.
- **Do** print the word next to every state colour: "Booked", "Refuel time", "Past", "Cancelled", and a text legend on every timeline.
- **Do** separate surfaces with a 1px hairline (`line`) and tone; give anything you can click or type into the stronger `line-strong` edge.
- **Do** use 6px radii on controls, 10px on containers and 4px on timeline blocks.
- **Do** keep tabular figures on, and label every time "CT".
- **Do** keep controls at 40px on a desk and 44px at 860px and below, with input text at 16px there.
- **Do** keep transitions to 120ms ease-out on background and border, and leave them covered by the reduced-motion rule.
- **Do** write labels in sentence case at weights 400, 500 or 600.

### Don't:
- **Don't** use solid indigo for a booking, or indigo tint for anything that is not booked or the selected row.
- **Don't** let colour carry a state on its own; a tint without its word is a defect.
- **Don't** give amber, grey, green or red a second meaning.
- **Don't** put a shadow on anything in the page flow; shadows belong to the dialog and the pinned mobile bar.
- **Don't** add a second accent hue or a second typeface.
- **Don't** add a themed space motif. The category standard was chosen deliberately.
- **Don't** hide the reason a time is unavailable behind a tooltip; it is visible text on the control.
