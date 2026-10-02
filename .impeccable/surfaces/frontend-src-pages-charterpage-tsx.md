---
version: 1
slug: "frontend-src-pages-charterpage-tsx"
primary_target: "frontend/src/pages/CharterPage.tsx"
related_targets: ["frontend/src/pages/FleetDashboard.tsx","frontend/src/styles/global.css"]
---

# Charter a Ship (`/`) and shared shell

Scope: `/` booking screen plus the app shell and tokens; `/fleet` takes the new look only, structure untouched. Mode: Operate.

Audience and job: a dispatcher at a desk in a bright office, often on the phone with a pilot, finds a free stretch across all five ships and books it. Constraints: server is the authority for availability, "today" and time; every time is CT; no backend change.

Unresolved: date in the URL, cancel dialog hierarchy, fleet list duplication (P2s, out of scope).

## Direction contract

THESIS: The category standard, chosen on purpose by the user (canon), at the craft level of Linear and the Stripe Dashboard. The screen owns one idea: the whole fleet's day is visible before a ship is chosen. It refuses the single-resource appointment picker with a wall of equal time tiles.

OWN-WORLD: White surfaces on a very light cool grey ground, hairline grey borders, near-black ink, one indigo accent for navigation, selection and the primary action. State colours with text alongside: indigo tint for booked, amber tint for refuel gap, grey for past, green for success, red for danger. Inter with tabular figures; 6px radii; soft low shadows only on overlays and the pinned mobile bar. No themed motif.

STORY: The dispatcher sees which ships are free and when, picks a ship, picks a start time grouped by hour, types the pilot name and books. Every unavailable time says why.

FIRST VIEWPORT: White top bar: product name left, two nav tabs, live spaceport clock right. Page title, then Date and Duration filters. Below, a bordered five-lane day view on a shared 6 AM to 10 PM scale, each lane a selectable row with ship name, open-start count, booking blocks, refuel gaps and a now marker. Under it, left: the chosen ship's start times in Morning, Afternoon and Evening columns; right: the "Your charter" panel with the departure time set large, pilot name and the primary Book button.

FORM: Canon (the standing exit), taken by the user on the direction round. Seed key e069e987. Signature interaction: selecting a start time paints its span on the ship's lane; on phones the charter panel pins to the bottom.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
