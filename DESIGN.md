# PackagePro — Liquid Redesign

> Visual system and feature blueprint for the PS-04 rebuild. Every choice below
> is traceable to a real table in `PackagePro/data/PS-04.db` so the design can be
> implemented without inventing data.

---

## 1. Design thesis — "The Liquid Itinerary"

The old metaphor was a **control tower** — fixed instruments, hard edges, a wall of
readouts. It matched the trust thesis but read as cold and, critically, it fought the
product: a *dynamic* package is something that **flows and reshapes**. Static panels
cannot show that.

The new metaphor is **liquid**. Packages pour into shape, components swap like fluid
exchanging places, the budget behaves like a container filling, and prices move with
visible flow. Fluidity becomes the *evidence* of dynamism: when you swap a component
you don't just see a new number — you watch the price change.

The trust thesis survives intact, and gets stronger for it. A hard cap is more
dramatic against something that visibly wants to overflow. Transparency reads as
generosity when the mechanism is beautiful, not when it's a warning sticker.

**One sentence for the judges:** *the package is liquid — it takes the shape of the
traveler, and the budget is the vessel.*

---

## 2. Foundations

### 2.1 Color — deep water with iridescence

Flat navy is replaced by a **deep, drifting abyss** — a near-black with a violet-blue
undercast — over which an **aurora mesh gradient** drifts slowly. Panels are
glassmorphic, not painted. Iridescence is reserved for live/flowing things.

```css
:root {
  /* Base — not a flat fill; layered radial gradients that drift (see 2.4) */
  --abyss:        #070A13;
  --abyss-2:      #0B1020;
  --surface:      rgba(255, 255, 255, 0.045);
  --surface-2:    rgba(255, 255, 255, 0.075);
  --surface-3:    rgba(255, 255, 255, 0.11);
  --hairline:     rgba(255, 255, 255, 0.08);
  --hairline-2:   rgba(255, 255, 255, 0.15);

  /* Text */
  --ink:          #F2F5FA;
  --ink-2:        #A9B2C6;
  --ink-3:        #6E7891;

  /* Aurora — iridescent, gradient-only, for anything "flowing" */
  --aurora-1:     #5EEAD4;   /* teal */
  --aurora-2:     #8B7CFF;   /* violet */
  --aurora-3:     #E8A33D;   /* amber — continuity with the old "live" signal */

  /* Semantic — unchanged, they already worked */
  --go:           #5FBF8F;
  --stop:         #E2665C;
}
```

**Restraint rule (kept from the old system):** amber/iridescence marks *something is
live*. Do not add a second bright accent. The aurora is a *gradient*, not three new
spot colors — the eye reads it as one shifting surface.

### 2.2 Typography — grotesque body, soft-serif display, mono ledger

Three roles, three voices. The display face gains the **soft optical axis** so headings
physically round as they grow — a typographic liquid cue.

| Role | Family | Use |
|---|---|---|
| Display | `"Fraunces"` variable (`opsz`, `SOFT`) | Section titles, package names, hero numbers. Sparingly. |
| UI | `"Geist"` / `"Inter"` fallback | All interface text, labels, prose |
| Ledger | `"Geist Mono"` / `"IBM Plex Mono"` fallback | **Every price, delta, ID, percentage, trace line — no exceptions** |

```css
--font-display: "Fraunces", Georgia, serif;
--font-ui:      "Geist", "Inter", system-ui, sans-serif;
--font-mono:    "Geist Mono", "IBM Plex Mono", ui-monospace, monospace;
```

Type scale (1.25 major third, fluid via `clamp()`):

```
display-xl  clamp(2.5rem, 5vw, 4rem)    Fraunces opsz 144 SOFT 50
display     clamp(1.75rem, 3vw, 2.25rem)
h1          1.5rem
h2          1.25rem
body        0.9375rem   (15px)
small       0.8125rem
micro       0.6875rem  mono, uppercase, +0.08em tracking — for eyebrows
```

**Numerals:** `font-variant-numeric: tabular-nums` on all money/ledger text so digits
don't dance during live repricing.

### 2.3 Spacing & shape — soft geometry

8px base scale. Corners get large and soft; the radius increases with surface depth —
the deeper the glass, the rounder it feels.

```
radius: 10 / 14 / 20 / 28 / 999 (pill)
shadow: 0 1px 2px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.06)   (refraction edge)
shadow-lg: 0 30px 70px -25px rgba(0,0,0,.75), inset 0 1px 0 rgba(255,255,255,.09)
```

Every glass panel carries an **inset top hairline** — a fake refracted light edge. This
is the single trick that makes dark glass look expensive instead of flat.

### 2.4 The drifting background (perf-budgeted)

Aurora is one low-cost effect, not a pile:

- Two large radial gradients in a fixed `::before`, animated with a 40s
  `transform: translate3d` drift — **GPU-composited, zero layout cost**.
- A faint SVG `feTurbulence` grain overlay at ~3% opacity to kill gradient banding.
- `prefers-reduced-motion` pins the drift instantly (see 2.6).

Never put aurora behind body text at high saturation — it lives at the margins and
behind glass.

### 2.5 Motion — spring physics, not easing curves

Fluidity is a **physics** decision. Linear/cubic easing feels mechanical; springs
overshoot and settle, which is what makes motion read as *liquid*.

```js
// Motion tokens — reuse everywhere, do not hand-tune per component
export const springs = {
  snap:   { type: "spring", stiffness: 420, damping: 32 },  // toggles, chips
  liquid: { type: "spring", stiffness: 170, damping: 22, mass: 0.9 },  // cards, panels
  pour:   { type: "spring", stiffness: 120, damping: 18, mass: 1.1 },  // big state changes
  gauge:  { type: "spring", stiffness: 90,  damping: 15 },  // budget fill
};
```

| Technique | Where | Effect |
|---|---|---|
| Spring layout | `layout` on cards, list reorders | elements flow around each other instead of jumping |
| Shared-element | selected package card → detail view | the card *expands* into the next screen |
| FLIP on swap | component list after a swap | the swapped item glides into place, siblings part around it |
| Path morph | budget gauge (SVG) | the liquid surface wobbles and settles |
| Staggered entrance | grids of cards | a pour, not a flash |

**Rule:** motion explains a change. Never animate a value the user isn't meant to
notice — the aurora drifts, prices tick, the budget wobbles. Decorative motion only.

### 2.6 Accessibility & reduced motion

`prefers-reduced-motion: reduce` → all springs snap to final state, drift stops, FLIP
becomes an instant reorder. The product stays fully usable. Contrast ratios held at
WCAG AA: `--ink` on `--abyss` is 15:1; `--ink-3` is used only for non-essential
micro-labels at AA-large.

Focus rings are a 2px iridescent outline — visible on glass where a plain outline
disappears.

---

## 3. The signature interaction — live reprice as theatre

This is the core PS-04 requirement and the single most demo-worthy moment. It must be
*watchable*, not just correct.

**Sequence on a component swap:**

1. The picked alternative **glides** into the slot (FLIP); the outgoing item fades
   through the surface.
2. A delta chip — `+₹1,375` or `−₹642` — **pours** out of the swapped line and flows up
   the ledger column toward the total.
3. The total **counts** to its new value. Animated as a string interpolation between
   two `Decimal` values — never a float, never a `requestAnimationFrame` on a binary
   double. The digit roll is what sells it.
4. The budget gauge's liquid surface **rises or falls**, sloshing once and settling
   (spring on the SVG path).
5. If the swap would breach the cap: the surface **hits the rim**, ripples, and the
   glass flushes `--stop` at low alpha — the negotiation gate opens *from the physics*,
   not from a modal appearing.

**Why this wins:** judges can *see the requirement working*. "Dynamic packages with
live repricing" stops being a bullet point and becomes something they remember.

---

## 4. Screens, redesigned

Flow is restructured around the PS-04 domain — **packages, not flights** — in four
pours.

```
Intake → Package → Customize → Confirm
```

### Screen 1 — Intake (the vessel)
Soft full-bleed glass over aurora. One question at a time in large Fraunces, answers as
liquid pill chips that settle into place. Destination, dates, party, budget cap, and
**preferred language** (`user_preferences.preferred_languages`, BCP-47). The budget cap
is set here and is *the* vessel — visualized from this screen onward.

### Screen 2 — Package gallery
Cards of `tour_packages` floating on glass, filtered by theme/tier/duration/language
(`languages_offered`). Each card carries a live price that has *already* been repriced
with its included components (base + Σ non-optional deltas), shown in mono with the
"includes" total under the base — honesty baked into the card, not a footnote.

### Screen 3 — Customize (the hero screen)
Split liquid layout:

- **Left:** the package as a vertical **day river** — `day_index` as columns,
  `package_components` as stones in a `slot` sequence (morning→overnight). Swappable
  components shimmer subtly; click opens the **swap drawer**, a bottom sheet of
  same-`swap_group` alternatives with delta chips and a confidence badge.
- **Right, sticky:** the **budget vessel** (gauge + ledger) and the guide matcher.

### Screen 4 — Guide & availability
`tour_guides` filtered by BCP-47 `languages`, `specialisation`, `day_rate`; availability
rendered as a **30-day heatmap strip** from `guide_availability`
(`is_available`, `slots_available`, `price_multiplier`). Peak multipliers tint warm.
"No guide free that day" is a designed state, not an error — it surfaces adjacent days.

### Screen 5 — Confirm
Cart as a settled pool: final itinerary, total vs cap, and the **audit trail** as a
mono readout. The confirm button is the only solid `--go` fill in the product — it is
the one action that commits, and visually nothing else is allowed to compete.

---

## 5. Multilingual — shown, not declared

| Where | How |
|---|---|
| UI chrome | full `en` / `hi` / `ta` strings, language pill in header |
| Package content | `tour_packages.name`/`description` rendered in the selected tag where the data carries it, else graceful fallback |
| Guide matching | `tour_guides.languages` BCP-47 filter is *the* demo lever — pick Tamil, watch the set change |
| Scripts & RTL | `languages.script`, `languages.rtl` drive `font-family` swap (Deva/Taml faces) and `dir` flip |

Language preference is not a settings page — it is a filter that visibly reshapes the
gallery. That makes it demonstrable in 20 seconds.

---

## 6. New features — each grounded in real columns

Every item names the exact data it runs on and the edge it buys.

### F1. Price-factor explainer
**Data:** `price_history.demand_index`, `occupancy_pct`, `lead_time_factor`,
`seasonality_factor`, `event_factor`, `competitor_factor`, `explanation`, `bound_clamped`.
**What:** clicking any repriced line opens a **factor waterfall** — the baseline, each
factor's contribution, and where `bound_clamped` clipped it.
**Edge:** "why does this cost this" is the exact question every travel AI dodges. Showing
the decomposition, on data the organizers shipped, reads as a moat rather than a claim.

### F2. Guide availability heatmap
**Data:** `guide_availability` (3,600 rows; `is_available`, `slots_available`,
`price_multiplier`).
**Edge:** most teams will render guides as a list and *assume* availability. Making
"is this guide free on the 12th" a real, scannable surface turns the PS-04-added guide
dimension into visible engineering, and makes peak pricing legible.

### F3. Party-language concord
**Data:** `user_preferences.preferred_languages`, `guide_language`, `tour_guides.languages`.
**What:** for multi-traveler trips, surface guides who cover **the union** of the party's
languages, ranked by coverage and rating.
**Edge:** a group-booking wedge nobody else will build in 24h, and it exercises BCP-47
correctly rather than as a label.

### F4. Carbon ledger
**Data:** `itinerary_items.carbon_kg`, `transfers.carbon_kg`.
**What:** a second vessel — a carbon budget alongside the money one; swaps that cut
carbon are badged.
**Edge:** ESG is a procurement criterion for corporate/family group travel. Two ledgers,
one interaction model, ~an afternoon of work on data already present.

### F5. Cold-start honest personalization
**Data:** `users.segment` (`heavy` / `light` / `cold_start`), `user_preferences.*`.
**What:** for `cold_start` users the system uses **declared** preferences only and *says
so* — no fake history, no implied profile. The UI labels its own evidence.
**Edge:** trust is the thesis. An AI that admits what it doesn't know beats one that
hallucinates confidence, and the dataset was explicitly segmented to let us prove it.

### F6. Accessibility-aware filtering
**Data:** `user_preferences.accessibility_needs`, `transfers.accessible`,
`tour_guides.specialisation = 'accessibility'`, `hotel_room_types` occupancy.
**What:** one toggle filters step-free transfers and accessibility-specialist guides.
**Edge:** genuinely underserved, trivially queryable, and immediately legible to any
judge — and it costs almost no build time.

### F7. Seeded demo director
**What:** a hidden `?demo` mode that pre-seeds a known-good scenario (the Jaipur heritage
package, tight budget, a swap that triggers negotiation) and a **recorded offline run**
baked into the build.
**Edge:** venue Wi-Fi ends more demos than bad code. A deterministic, reheatable demo
path is the difference between showing the feature and apologizing for it.

---

## 7. Practical solutions (the unglamorous wins)

| Problem | Solution |
|---|---|
| Float money drift (the old `BudgetGuard` used `float`) | A `Money` value object: `Decimal` amount + ISO-4217, one boundary, used end to end. The animation layer interpolates strings, never `number`. |
| Schema drift (old code queried nonexistent `city_name`) | Generate the data layer from `schema.sqlite.sql` at build time; conformance check (`validate_conformance.py`) runs in CI, not at the demo. |
| `price_delta` signed-negative trap | Reprice helper is one function: `base + Σ(kept deltas)`, unit-tested against known packages. |
| Multilingual script/RTL breakage | `languages` table drives `dir` and font stack; tested in all three locales. |
| LLM outage mid-demo | Deterministic cheapest-first fallback, surfaced in the trace as "LLM unavailable — degrading" — the failure becomes a *feature* of the reliability story. |
| Judge can't tell it's real data | Every panel shows row counts / IDs in mono micro-labels (`pkg_2d89ae17 · 7 components`) so real data is self-evident. |

---

## 8. Implementation notes

- **Frontend:** React 18 + Vite (kept). `framer-motion` for springs/layout/FLIP.
  `decimal.js` on the client so money never becomes a double in transit either.
- **Backend:** FastAPI (kept), plain composable phase functions — no phantom LangGraph.
  `Money` at the API boundary; every response carries currency alongside amount.
- **Fonts:** self-host Fraunces + Geist (variable, subset) — no render-blocking CDN.
- **Perf budget:** aurora = 1 compositing layer; springs on `transform`/`opacity` only;
  no per-frame layout. Target 60fps during the swap sequence on a demo laptop.

---

## 9. What the judges see in 90 seconds

1. A package card **expands** into its components — the package is liquid. *(memory)*
2. A swap: the price **counts**, the budget vessel **sloshes**, the delta chip **pours**. *(the requirement, visible)*
3. The vessel **hits its rim** → negotiation gate opens from the physics. *(the trust thesis)*
4. A Tamil-speaking guide, free on the 14th, with the multiplier that made him cost more. *(real data, multilingual)*
5. The price-factor waterfall answering *"why"*. *(explainability moat)*

Everything above runs on rows that already exist. Nothing here requires an API key to
demo — which is what makes it safe.
