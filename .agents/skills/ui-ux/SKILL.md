---
name: ui-ux
description: >-
  Design and build interfaces to a 2026 professional standard — token systems,
  type and spacing scales, WCAG 2.2 AA accessibility, Core Web Vitals budgets,
  motion, RTL/Persian support, and agentic-AI interaction patterns. Use this
  skill whenever the task touches an interface in any way — designing or
  building a web page, app screen, dashboard, landing page, form, table,
  component, or design system; reviewing or critiquing an existing UI;
  converting a design into code; or building the front end of an AI or agent
  product. Use it even when the user only says "make it look good", "build me a
  page", "design a screen", "clean up this layout", or asks why something feels
  off. Consult it BEFORE writing any frontend code a human will look at, not
  after.
---

# UI/UX Design — 2026 Standard

You are acting as the design lead on this work, not as a code generator that happens to emit CSS. A design lead is accountable for three things: that the interface does its job, that every person can use it, and that it does not look like it came out of a template. Everything below serves those three.

**How to use this document.** Part One is the process — read it end to end and work the five phases in order. Parts Two to Six are depth: consult the ones the task actually calls for rather than loading all of them for every job. Part Six is copy-paste.

Standards baseline, stated once: **WCAG 2.2 Level AA** is the accessibility target — it is the current W3C Recommendation and the version referenced by the European Accessibility Act, EN 301 549, Section 508, and ADA enforcement. WCAG 3.0 is still a Working Draft with an unfinished graded conformance model and is years from final; design in its direction, never claim conformance to it. Performance targets are **LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1** at the 75th percentile of real users.

## Contents

| Part | Covers | Read it when |
|---|---|---|
| **One — Process** | Five phases, the quality floor, anti-patterns, output format | Always. This is the skill. |
| **Two — Accessibility** | WCAG 2.2 AA per criterion, the six new 2.2 criteria, test procedure | Implementing or auditing accessibility, or when "is this accessible enough?" needs a specific answer |
| **Three — Agent & AI UX** | Nine interaction patterns for copilots and autonomous agents | The product involves model output, a chat surface, or an agent. Non-optional for agent products. |
| **Four — RTL & Persian** | Logical properties, numerals, Persian typography, mixed direction | Shipping in Persian, Arabic, Hebrew, or Urdu, or any mixed-direction content |
| **Five — Review rubric** | Seven-section audit with scoring and a report template | Before delivering anything, and whenever critiquing an existing interface |
| **Six — Design tokens** | A working starter stylesheet: OKLCH ramps, semantic layer, dark mode, RTL-ready base | Starting any build |

---

## PART ONE — PROCESS

You are acting as the design lead on this work, not as a code generator that happens to emit CSS. A design lead is accountable for three things: that the interface does its job, that every person can use it, and that it doesn't look like it came out of a template. Everything below serves those three.

Work through the five phases in order. Skipping straight to code is the single biggest cause of interfaces that are technically functional and practically unusable.

---

### Phase 1 — Frame the brief

Never design blind. Five questions must have answers before a single value is chosen. If the brief doesn't answer them, propose answers yourself in one short paragraph and state them as assumptions — don't stall the work waiting for a reply, but don't silently guess either.

1. **Who is the user, and in what state?** A person rushing on a phone at 2% battery needs a different interface from a person at a desk with two monitors. An analyst scanning 400 rows needs a different one from a first-time visitor. State matters more than demographics.
2. **What is the ONE job of this screen?** Name a single job. If you name three, the design will do none of them well. Everything else on the screen is subordinate to that one job and should look subordinate.
3. **What is the real content?** Design with real or realistic content. Never lorem ipsum, never "Card Title 1". Fake content hides the failures that matter: the 47-character product name, the user with no avatar, the empty table, the three-line error, the number that turns out to be negative.
4. **What are the hard constraints?** Platform, existing design system, brand, reading direction (LTR/RTL), locale and numeral system, offline behavior, slowest device that must work, regulatory requirements.
5. **What is the subject matter?** Distinctive design comes from the domain, not from a trend list. A tool for commodity traders and a booking app for a yoga studio should not be able to swap stylesheets. Pull the palette, density, typography and vocabulary from the subject's own world.

#### Enumerate the states before you design any of them

Every data-bearing surface has at least six states. Designing only the ideal one is the most common failure in generated UI, and it is immediately obvious to anyone reviewing the work:

| State | What it must do |
|---|---|
| Empty (first run) | Explain what will appear here and give one action to make it appear. Never just "No data." |
| Loading | Hold the exact layout the content will occupy. Skeletons that match real dimensions, not spinners that collapse the page. |
| Partial | Some fields missing, image failed, name truncated. The layout must not break. |
| Error | Say what went wrong, in the interface's voice, and what to do next. Never apologize, never say "Something went wrong." |
| Ideal | The state everyone designs. |
| Overloaded | 500 rows, a 90-character title, 12 tags. Decide now whether it truncates, wraps, scrolls, or paginates. |

Write these down. Then design them.

---

### Phase 2 — Build the token system before touching pixels

A value that appears twice in the codebase and can drift is a bug waiting to happen. Define tokens first; every later decision references them.

Use three layers, and never let a component reach past its layer:

```
primitive   --blue-600: oklch(55% 0.18 255)     raw values, no meaning
semantic    --color-action: var(--blue-600)      role and intent
component   --button-bg: var(--color-action)     local binding
```

**Color.** Author in OKLCH. It is perceptually uniform, so a lightness ramp actually *looks* like even steps (the same is not true of HSL, where a mid-blue and a mid-yellow at the same "lightness" differ wildly), and it reaches colors sRGB can't express on modern displays. Build one neutral ramp and one brand ramp of 11 steps (50–950), plus semantic status colors. Two accents maximum. Dark mode is a redefinition of the *semantic* layer, never an inversion filter and never a separate stylesheet.

**Spacing.** One base unit, 4px. The scale is `4 8 12 16 24 32 48 64 96`. Do not invent 13px, 22px, or 38px. Irregular spacing is the loudest signal that a design has no system behind it, and reviewers spot it before they consciously notice anything else.

**Type.** Base 16px. Pick a ratio and generate 6–8 steps from it: 1.200 for dense data UI, 1.250 for product UI, 1.333 for marketing. Line-height moves inversely with size — 1.5–1.6 for body, 1.1–1.25 for display. Cap measure at 65–75 characters (`max-width: 65ch`); longer lines cost readers their place on every return sweep. One or two families, and if two, make them unmistakably different from each other.

**Everything else.** Radius (3 steps), border width (2), shadow (3 — and all three must model the same single light source), motion duration and easing, z-index layers. Tokenize them all.

**Part Six** below is a working starter token file. Copy it and adapt the hues to the brief — don't ship it unchanged, since its defaults are deliberately neutral.

---

### Phase 3 — Structure before style

**Write the hierarchy in plain text first.** An ASCII wireframe or an indented outline takes thirty seconds and exposes structural problems that are expensive to find after the CSS is written.

**Semantic HTML is the accessibility layer.** Most of WCAG comes free if the markup is right, and almost none of it can be retrofitted with ARIA afterward:

- Landmarks: `<header> <nav> <main> <aside> <footer>`. Exactly one `<main>`, exactly one `<h1>`.
- Heading levels descend without skipping. Headings are structure, not a font-size shortcut.
- Native elements before custom ones: `<button>`, `<a href>`, `<dialog>`, `<details>`, `<select>`, `<input type>`. A native `<button>` brings keyboard handling, focus, role, and platform behavior that a styled `<div>` will never fully replicate.
- Every input has a real `<label>`. Placeholder text is not a label — it disappears exactly when the user needs it.
- ARIA only where no native element exists. Wrong ARIA is worse than none.

**Layout.** Grid for page structure, Flexbox for one-dimensional runs. Then, specific to 2026:

- **Container queries over media queries.** A component should respond to the space it is actually given, not to the viewport. `@container (min-width: 30rem)` means the same card works in a sidebar, a modal, and a full-width hero without variant classes.
- **Logical properties everywhere**: `margin-inline-start`, `padding-block`, `inset-inline-end`, `border-start-start-radius`. This is what makes RTL work with a single attribute instead of a parallel stylesheet. Never write `margin-left` in new code.
- **Intrinsic sizing** instead of breakpoint tables: `clamp()`, `min()`, `max()`, and `grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr))`. Reach for a breakpoint only when the layout genuinely needs to change shape, not when it needs to change size.
- `@layer reset, base, components, utilities` to control the cascade deliberately instead of fighting specificity later.
- `light-dark()`, `color-mix()`, `:has()`, `field-sizing`, `popover`, and the View Transitions API are all available — use them where they remove JavaScript.

---

### Phase 4 — The 2026 quality floor

These are not aspirations. An interface that misses any of them is not finished. Verify each one explicitly before you call the work done.

| Area | Requirement |
|---|---|
| Contrast | 4.5:1 body text, 3:1 large text (≥24px, or ≥18.7px bold), 3:1 for UI component boundaries, icons, and chart elements. Check every state, including hover, disabled, and text over images or translucent surfaces. |
| Keyboard | Every interactive element reachable and operable by keyboard alone. Logical tab order. No traps. Focus never hidden behind a sticky header or toolbar (WCAG 2.2 SC 2.4.11). |
| Focus | Visible indicator on every focusable element, minimum 2px, at least 3:1 against both the element and its surroundings. Never `outline: none` without a replacement. |
| Targets | 24×24 CSS px minimum (WCAG 2.2 SC 2.5.8). Use 44×44 for anything touch-primary — that is the platform expectation on both iOS and Android, and 24px is a legal floor, not a usable one. |
| Motion | Honor `prefers-reduced-motion: reduce`. Nothing flashes more than 3×/second. No motion carries meaning on its own. |
| Text | Layout survives 200% zoom and 400% text scaling without loss of content or horizontal scrolling. Never disable pinch-zoom. |
| Forms | Labels, inline validation on blur not on keystroke, errors tied to fields with `aria-describedby`, errors state the fix, correct `autocomplete` and `inputmode`, and nothing the user already entered is asked for twice (SC 3.3.7). |
| Auth | No cognitive test required to log in — paste into password fields must work, and one-time codes must be pasteable (SC 3.3.8). |
| Dragging | Anything draggable has a non-drag alternative: buttons, a menu, arrow keys (SC 2.5.7). |
| Performance | LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1, measured at the 75th percentile of real users, not in a lab. |
| Layout stability | Explicit `width`/`height` or `aspect-ratio` on every image, video, embed, and ad slot. Fonts with `font-display: swap` plus a metric-matched fallback. Never insert content above existing content after load. |
| Responsive | Works from 320px to ultra-wide. Nothing depends on hover alone. Nothing depends on a specific input device. |
| Dark mode | Works, via semantic tokens. Pure black backgrounds cause halation on OLED — use a very dark neutral. Reduce saturation of accent colors in dark mode or they will vibrate. |
| Direction | Works in RTL if the product ships in Arabic, Persian, Hebrew, or Urdu. |

Standards note for 2026: **WCAG 2.2 Level AA is the target to build and test against.** It is the current W3C Recommendation, and it is what the European Accessibility Act, EN 301 549, Section 508, and ADA enforcement reference. WCAG 3.0 is still a Working Draft with a graded conformance model that is years from finalization — design in its direction, but do not claim conformance to it.

Full per-criterion detail: **Part Two**.

---

### Phase 5 — Critique, then remove one thing

Before delivering, audit your own work against **Part Five**. Report honestly — a review that finds nothing wrong is a review that wasn't done.

Then do a subtraction pass. Spend your boldness in exactly one place: let one element be the memorable thing and keep everything around it quiet. Then find the one decoration that serves nothing and delete it. Almost every draft has one.

---

### Anti-patterns — how generated UI gives itself away

These appear regardless of subject matter, which is exactly why they read as machine output. Any of them can be right for a specific brief; none should be a default.

**Visual**
- The warm-cream background with a high-contrast serif and a terracotta accent near `#D97757`.
- Near-black background, one acid-green or vermilion accent.
- Every piece of content chopped into identical rounded cards with the same `rgba(0,0,0,.1)` shadow and the same border-radius regardless of hierarchy.
- Gradient washes used as decoration rather than to encode anything.
- Tinted near-blacks (`#0B0B0B`, `#111`) standing in for the neutral ramp.

**Typographic**
- One word in a headline set in italic, bold, or a different color.
- Tracked-out ALL-CAPS eyebrow labels above every heading.
- `01 / 02 / 03` numbered markers on content that isn't a sequence.
- Metadata joined with middle dots (`A · B · C`), monospace for small data labels, `→` appended to every link.

**Behavioral**
- Fade-and-slide-up entrance on every section, hover lift on every card.
- Loading spinners that collapse the layout instead of skeletons that hold it.
- Toasts for errors that require action — a toast that disappears is not an error message.
- Modals for anything that isn't blocking.
- Infinite scroll on content people need to find again.
- "Something went wrong."

**Structural**
- Only the ideal state exists.
- Placeholder text doing the job of a label.
- `<div onclick>` where a `<button>` belongs.
- Icon-only buttons with no accessible name.
- Color as the sole carrier of meaning (red/green status with no icon, shape, or text).

---

### Output format

When the deliverable is a design rather than code, structure it as:

```
## Brief
Who, the one job, the constraints, the subject. Assumptions marked as assumptions.

## Direction
Palette (4–6 named values), typefaces and their roles, layout concept, the one
principle that makes this specific rather than generic.

## Tokens
The token block, ready to paste.

## Structure
ASCII wireframe or outline, plus the state inventory.

## Notes
Accessibility decisions, RTL decisions, performance decisions, and what you
deliberately left out and why.
```

When the deliverable is code, ship the tokens as the top of the stylesheet, semantic markup, and a short note covering the same accessibility, RTL, and performance decisions. State any quality-floor item you could not meet and why — an honest gap is useful; a silent one is a defect.

---

## PART TWO — ACCESSIBILITY: WCAG 2.2 LEVEL AA

Target: **WCAG 2.2 Level AA**. It is the current W3C Recommendation, it has been adopted as an ISO/IEC standard, and it is the version referenced by the European Accessibility Act, EN 301 549, Section 508, and ADA litigation. WCAG 3.0 remains a Working Draft with an unfinished graded conformance model — treat it as direction of travel, not as a target to claim.

### Contents
1. What WCAG 2.2 added over 2.1
2. Perceivable
3. Operable
4. Understandable
5. Robust
6. Testing procedure
7. Things that pass automated checks and still fail users

---

### 1. What WCAG 2.2 added over 2.1

Nine new criteria. Six are A or AA and therefore in scope:

| SC | Level | Requirement |
|---|---|---|
| 2.4.11 Focus Not Obscured (Minimum) | AA | The focused element is never *entirely* hidden by sticky headers, footers, cookie banners, or chat widgets. Sticky bars are the usual culprit; `scroll-padding-block-start` on the scroll container fixes it. |
| 2.5.7 Dragging Movements | AA | Anything achieved by dragging has a single-pointer alternative: buttons, a "move to…" menu, arrow keys. Reorderable lists, sliders, kanban boards, map panning, signature fields. |
| 2.5.8 Target Size (Minimum) | AA | Targets are at least 24×24 CSS px, or spaced so a 24px circle centered on each doesn't overlap a neighbor. Exceptions for inline links in text. Use 44×44 for touch-primary UI anyway. |
| 3.2.6 Consistent Help | A | If help exists (contact link, chat, FAQ), it appears in the same relative place on every page that has it. |
| 3.3.7 Redundant Entry | A | Don't ask for the same information twice in one process. Auto-populate it or offer it for selection. Billing address that repeats shipping address is the classic case. |
| 3.3.8 Accessible Authentication (Minimum) | AA | No cognitive function test to log in. Password paste must work. One-time codes must be pasteable. No "type the 3rd and 7th character of your password", no puzzle CAPTCHAs without an alternative. Object-recognition and personal-content CAPTCHAs are permitted exceptions; transcription puzzles are not. |

Also removed: 4.1.1 Parsing is obsolete in 2.2. Validation errors no longer count against conformance on their own — but malformed markup still breaks assistive technology in practice, so keep the markup valid.

AAA additions (2.4.12 Focus Not Obscured Enhanced, 2.4.13 Focus Appearance, 3.3.9 Accessible Authentication Enhanced) are good practice but out of scope for AA.

---

### 2. Perceivable

**Text alternatives (1.1.1, A)**
- Informative images: alt text describing the information, not the picture. A chart's alt is its finding, not "bar chart".
- Decorative images: `alt=""`. Empty, not missing.
- Icon-only buttons: `aria-label` or visually hidden text. An unlabeled icon button is invisible to a screen reader.
- Complex images (charts, diagrams, infographics): short alt plus a longer description in the page, or a data table alternative.
- Never put meaningful text inside an image. It can't be translated, searched, scaled, or restyled.

**Media (1.2, A/AA)**
- Captions for all prerecorded video with audio. Auto-generated captions must be corrected — uncorrected machine captions typically fail.
- Audio description for video where visual information isn't in the audio track.
- Transcripts for audio-only content.

**Adaptable (1.3, A/AA)**
- 1.3.1 Info and Relationships: structure is in the markup, not just in the styling. Real `<table>` with `<th scope>` for tabular data. Real `<ul>` for lists. Real `<fieldset><legend>` for radio groups.
- 1.3.4 Orientation: never lock to portrait or landscape unless essential.
- 1.3.5 Identify Input Purpose: correct `autocomplete` tokens on fields collecting user information (`name`, `email`, `tel`, `street-address`, `postal-code`, `cc-number`, `one-time-code`).

**Distinguishable (1.4, A/AA)**
- 1.4.1 Use of Color: color is never the only channel. Status gets an icon or a word. Chart series get pattern, shape, or direct labels. Required fields get more than a red asterisk. Links inside body text get underlines — color alone against surrounding text fails.
- 1.4.3 Contrast (Minimum): **4.5:1** for normal text, **3:1** for large text (≥24px, or ≥18.66px bold). Measure the actual rendered colors, including text over gradients, images, video, and translucent/glass surfaces — pick the worst-case background pixel. Disabled controls are exempt but should still be legible.
- 1.4.4 Resize Text: usable at 200% zoom.
- 1.4.5 Images of Text: use real text.
- 1.4.10 Reflow: no horizontal scrolling at 320 CSS px width (equivalent to 400% zoom at 1280px). Exceptions for data tables, maps, and code.
- 1.4.11 Non-text Contrast: **3:1** for UI component boundaries (input borders, toggle states, focus rings, checkbox outlines) and for graphical objects needed to understand content (chart lines, icon glyphs carrying meaning).
- 1.4.12 Text Spacing: no content lost when a user forces line-height 1.5×, paragraph spacing 2×, letter-spacing 0.12em, word-spacing 0.16em. Fixed-height text containers are what break here.
- 1.4.13 Content on Hover or Focus: tooltips and popovers must be dismissible (Esc), hoverable (the pointer can move onto them), and persistent (they don't vanish on their own).

---

### 3. Operable

**Keyboard (2.1, A)**
- Everything operable by keyboard. Test by unplugging the mouse and completing the primary task.
- No keyboard traps. Modals trap focus deliberately — that's correct — but Esc must always release.
- Custom widgets need the expected key bindings: arrow keys inside a listbox/menu/tablist, Home/End, Esc to close, Space/Enter to activate.
- `tabindex` is `0` or `-1`. Positive values reorder the whole page and break it.

**Enough time (2.2, A)**
- Any time limit can be turned off, adjusted, or extended. Session timeouts warn first and offer an extension.
- Auto-updating, moving, or scrolling content that lasts more than 5 seconds has pause/stop/hide. This includes carousels and live tickers.

**Seizures (2.3, A)**
- Nothing flashes more than 3 times per second. Applies to video, animation, and loading effects.

**Navigable (2.4, A/AA)**
- Skip link to main content, first in tab order, visible on focus.
- Page titles are unique and front-load the distinguishing part: "Invoices — Acme" not "Acme — Invoices".
- Focus order matches visual order. CSS `order` and `grid-area` can desynchronize these — check.
- Link text makes sense alone. "Read more" ×8 on a page is a failure. If the visible text must stay short, extend it with visually hidden text.
- Two ways to find a page (nav + search, or nav + sitemap).
- Headings and labels describe what follows.
- Focus visible on every focusable element. Minimum 2px, ≥3:1 contrast against both the element and the adjacent background. `:focus-visible` gives keyboard users the ring without showing it on mouse click.

**Input modalities (2.5, A/AA)**
- Pointer gestures: anything requiring a multipoint or path-based gesture (pinch, two-finger, swipe-path) has a single-pointer alternative.
- Pointer cancellation: actions fire on `pointerup`, not `pointerdown`, so a user can slide off to abort.
- Label in Name: the accessible name contains the visible label text. A button reading "Send" must not have `aria-label="Submit form"` — voice-control users say what they see.
- Motion actuation: shake-to-undo and tilt controls have a UI alternative and can be disabled.
- Target size and dragging: see §1.

---

### 4. Understandable

**Readable (3.1, A/AA)**
- `<html lang="…">` on every page. `lang` on any inline passage in another language — this is what makes a screen reader switch pronunciation between Persian and English in a mixed sentence.
- Unusual terms, abbreviations, and jargon are defined on first use.

**Predictable (3.2, A/AA)**
- Focus alone never changes context. No auto-submit on select, no auto-advance between OTP fields that traps keyboard users.
- Navigation is in the same place across pages, and repeated components are identified consistently — the same icon means the same thing everywhere.
- Consistent Help: see §1.

**Input assistance (3.3, A/AA)**
- Errors are identified in text, not just color or an icon.
- Labels and instructions are present *before* the field, and format requirements are stated up front rather than only after failure.
- Error suggestions: say how to fix it. "Enter a date as DD/MM/YYYY" beats "Invalid date".
- Legal, financial, and data-deleting submissions are reversible, checked, or confirmed.
- Redundant Entry and Accessible Authentication: see §1.

---

### 5. Robust

- Name, Role, Value: every custom control exposes all three. If you build a toggle out of a `<div>`, it needs `role="switch"`, `aria-checked`, a name, and keyboard handling — at which point `<button>` would have been less work and more reliable.
- Status Messages (4.1.3, AA): things that appear without focus moving — "Saved", "3 results", "Upload failed" — must be announced. `role="status"` for polite, `role="alert"` for assertive. The live region must exist in the DOM *before* the message is inserted into it, or nothing is announced.

---

### 6. Testing procedure

Automated tools catch roughly 30–40% of real issues. The rest requires the manual passes.

1. **Automated**: axe DevTools, Lighthouse, or Pa11y. Fix everything it reports. This is the floor, not the ceiling.
2. **Keyboard**: unplug the mouse. Complete the primary task. Note every place you get stuck, lost, or can't see where you are.
3. **Zoom**: 400% browser zoom at 1280px width. Then 320px viewport. Nothing lost, no horizontal scroll.
4. **Contrast**: sample real rendered pixels for every text/background pair, in both themes, in every interaction state.
5. **Screen reader**: one full task with NVDA + Firefox or VoiceOver + Safari. Listening to your own interface for two minutes reveals more than any checklist.
6. **Text spacing**: apply the 1.4.12 bookmarklet values and look for clipped or overlapping text.
7. **Reduced motion**: enable the OS setting and confirm the interface still communicates what changed.

---

### 7. Passes the checker, fails the user

These are technically conformant and still bad. Catch them in review:

- Alt text that describes the file instead of the meaning: `alt="chart.png"`, `alt="image of a graph"`.
- Heading levels used for size, producing an outline that reads as nonsense.
- A skip link that exists but points at a container that isn't focusable.
- Focus rings that meet 3:1 against the button but disappear against the page behind it.
- `aria-label` on a container that overrides all the readable text inside it.
- Live regions that fire on every keystroke and flood the user with announcements.
- Translucent/glass surfaces that pass contrast over the design mockup's background and fail over real user content. Test the worst case, and provide an opaque fallback under `prefers-reduced-transparency`.
- Error summaries at the top of a form that don't move focus and aren't linked to the fields.
- Tooltips as the only place important information exists.

---

## PART THREE — AI AND AGENT INTERFACE PATTERNS

Read this part when the product involves model output, a copilot, a chat surface, or an autonomous agent.

### The core shift

Traditional UX assumes: the user acts, the system responds, the user evaluates, repeat. Every state change starts with a human.

Agents break that in three ways, and each one breaks a specific interface assumption:

1. **Actions outrun perception.** An agent may fire 40 tool calls in 90 seconds. No spinner, progress bar, or raw log stream communicates that at a speed a human can parse.
2. **Consequences are non-linear.** Sending an email, opening a PR, or writing to a database has effects that unfold over hours. Traditional UX assumes consequences are immediate and reversible.
3. **The human's role changes from actor to supervisor.** Users set goals, monitor, and decide when to intervene. That is a different cognitive mode and needs different affordances.

A chat box handles none of this. Chat is a fine *input* surface and a poor *oversight* surface: it makes the agent's work opaque, and it gives the user exactly two controls — submit, or abort everything.

**Design principle: the user should always feel like they're driving, even when the agent is doing the work.**

---

### Pattern 1 — Intent preview (plan before execution)

Before the agent acts, show what it intends to do and let the person accept, edit, or take over.

```
I'll do 3 things:
  1. Pull the Q3 numbers from the finance sheet
  2. Draft a summary email to the team
  3. Send it to 14 recipients          ← this one changes the world

[ Proceed ]  [ Edit plan ]  [ I'll handle it ]
```

Non-negotiable for any action that is irreversible, spends money, sends something to another person or system, or makes a change the user can't easily undo.

Without it, users feel ambushed and turn the feature off. Worth instrumenting: if plans are accepted unedited well over 85% of the time, the gate is probably in the right place; if overrides are frequent, the agent is misreading intent, not the UI's fault.

### Pattern 2 — Risk-tiered gates

Not every action deserves a confirmation. Confirmation fatigue turns approval dialogs into things people click through without reading, which is worse than no gate at all. Tier by consequence:

| Tier | Examples | Gate |
|---|---|---|
| Read-only | Search, fetch, summarize, analyze | None. Just show it happened. |
| Reversible write | Draft saved, label added, file created in a scratch space | None, plus a visible undo |
| External / irreversible | Send, publish, pay, delete, deploy, message a person | Explicit confirmation naming the specific consequence |
| Bulk | Any of the above × many | Confirmation showing the count and a sample of what's affected |

Let people move the line themselves with an autonomy setting (ask every time / ask for risky things / run freely in this project). Trust is earned incrementally and the interface should let it be granted incrementally.

### Pattern 3 — Legible progress, not a log stream

Show the shape of the work, not the raw trace. Three layers, progressively disclosed:

- **Now**: one line in plain language — "Reading the September invoices", not `tool_call: fs_read(path=…)`.
- **Done**: a compact list of completed steps, each expandable to its detail.
- **Full trace**: available, collapsed by default, for people who want to audit.

Stream partial output as it's produced rather than holding everything until the end. Perceived latency is mostly about whether something is visibly happening.

Every step gets a status: running, done, failed, skipped, waiting on you. "Waiting on you" must be visually loud — a stalled agent that looks busy is a trust-destroying experience.

### Pattern 4 — Interruption without abortion

Users must be able to steer mid-run, not just kill the run. Provide:

- **Pause** — stop before the next action, keep everything so far.
- **Redirect** — "actually, only the EU accounts" without restarting.
- **Skip this step** — move past one action, continue the rest.
- **Stop** — end it, and say clearly what was already done and what wasn't.

The last point matters most. An aborted run that leaves the user unsure what changed is worse than one that never started.

### Pattern 5 — Receipts and rollback

After the run, show what actually changed in the world — files written, messages sent, records updated — as a list of concrete, linked artifacts, not a prose summary. Where a change is reversible, put undo next to it. Where it isn't, say so before it happens, not after.

Keep an activity log that is readable by a person who wasn't watching. "What did this thing do while I was at lunch?" is the most common real question.

### Pattern 6 — Uncertainty and sourcing

- Distinguish what the model knows from what it retrieved. Cite the source next to the claim, not in a footnote block.
- Surface low confidence *where the user acts on it*, not in a general disclaimer. A blanket "AI can make mistakes" at the bottom of the screen changes no one's behavior.
- When the agent couldn't do something, say which part failed and what it did instead. Silent degradation is the worst failure mode: the output looks complete and isn't.
- Never present a guess with the same visual weight as a verified fact.

### Pattern 7 — Error recovery

Agent errors are different from form errors: the user often doesn't know what the agent was trying to do when it failed. So an agent error message states three things — what it was attempting, what went wrong, what the options are now.

```
Couldn't send the summary
The mail connection expired while sending. 9 of 14 went out;
5 didn't. The draft is saved.

[ Reconnect and send the remaining 5 ]  [ Show who got it ]  [ Stop here ]
```

Offer retry-with-modification, not just retry. A retry that will fail identically is a dead end.

### Pattern 8 — Generative and adaptive UI

When the agent produces interface rather than text, keep it inside the host design system. Agent-declared UI should be structured data mapping to your existing components, never arbitrary generated markup or executable code — that is both a security boundary and a consistency boundary.

Adaptive interfaces that rearrange themselves based on inferred intent need a stable anchor: the primary navigation and the primary action stay put. People build muscle memory against position, and an interface that moves under them feels broken even when it's being helpful.

### Pattern 9 — Notification discipline

Background agents produce a stream of events. Most are not worth interrupting for. Notify on: needs your decision, finished a long task, failed in a way that needs you. Batch everything else into the activity log. An agent that pings on every tool call gets muted, and a muted agent misses the notification that mattered.

---

### Anti-patterns

- **Chat as the only surface.** Fine for input, inadequate for oversight.
- **Spinner for a 90-second multi-step run.** Communicates nothing, and the user can't tell stuck from working.
- **Approval dialogs that don't name the consequence.** "Allow this action?" trains people to click yes.
- **Confidence theater.** Percentages the model can't actually calibrate are worse than an honest hedge.
- **Blanket disclaimers.** They discharge liability and change no behavior. Put the caveat on the claim.
- **Anthropomorphized uncertainty.** "I think…", "I'm worried that…" from a system that isn't thinking or worried muddies what the user should actually trust.
- **Irreversible actions with no preview.** The fastest way to get a feature disabled organization-wide.
- **Hiding tool access.** Users should be able to see what the agent *can* touch before it touches anything.
- **Fake streaming.** Animating text that already fully arrived. People notice, and it costs you trust on everything else.

---

### Minimum bar for any agent UI

Before shipping, confirm all seven:

1. The user can see what the agent plans to do before it does anything irreversible.
2. The user can tell, at a glance, whether it's working, waiting, or done.
3. The user can stop or redirect without losing completed work.
4. The user can see what actually changed afterward.
5. Failures name what was attempted and offer a next step.
6. Claims are sourced, and uncertainty appears where decisions get made.
7. Everything above is keyboard-accessible and screen-reader-announced — streaming output needs a live region, and a `role="status"` region must exist in the DOM before content is written into it.

---

## PART FOUR — RTL, PERSIAN, AND MIXED-DIRECTION INTERFACES

Read this part when the product ships in Persian, Arabic, Hebrew, or Urdu, or when content mixes directions — which, for Persian financial, technical, and news interfaces, is essentially always.

### The mental model

RTL is not a mirror filter applied at the end. It is a property of the document that the layout system reads. If the CSS is written with logical properties from the start, switching direction costs one attribute. If it's written with `margin-left`, it costs a parallel stylesheet and a permanent maintenance tax.

```html
<html lang="fa" dir="rtl">
```

That's the whole mechanism. Everything below is about making the rest of the code cooperate with it.

### Logical properties — the complete swap

Never write physical properties in new code:

| Don't | Do |
|---|---|
| `margin-left` / `margin-right` | `margin-inline-start` / `margin-inline-end` |
| `padding-top` / `padding-bottom` | `padding-block-start` / `padding-block-end` |
| `left` / `right` | `inset-inline-start` / `inset-inline-end` |
| `text-align: left` | `text-align: start` |
| `border-left` | `border-inline-start` |
| `border-radius: 8px 0 0 8px` | `border-start-start-radius` + `border-end-start-radius` |
| `width` / `height` | `inline-size` / `block-size` |
| `float: left` | `float: inline-start` |
| `translateX(10px)` | Direction-aware value, or flip in an `[dir="rtl"]` rule |

Flexbox and Grid follow `dir` automatically — `flex-direction: row` reverses, `justify-content: flex-start` moves to the right. That's correct behavior, not a bug. Grid `grid-auto-flow: column` also reverses.

### What flips and what doesn't

**Flips with direction:**
- Layout, alignment, reading order
- Navigation arrows, back/forward, breadcrumb chevrons, expand/collapse carets
- Progress bars, sliders, steppers (progress moves right→left)
- Icons that imply direction: reply, share, undo/redo, indent, send
- Drop shadows, if they model a light source that should stay consistent relative to the reading direction
- Carousels and the swipe direction that advances them

**Does NOT flip:**
- **Numbers.** `1,234.56` reads left-to-right in every direction. Do not reverse digits.
- **Times and durations**: `14:30`, `2:45`
- Latin text embedded in Persian: brand names, tickers (`XAUUSD`), code, URLs, email
- Clock icons, media play buttons (play always points in the playback direction, which is conventionally right), logos, checkmarks
- Charts with a time axis, if your convention is that time runs left→right — but pick one convention and hold it across the whole product
- Physical-world imagery

### Numerals — decide once, apply everywhere

Persian has two numeral systems in active use: Western Arabic (`0123456789`) and Eastern Arabic-Indic (`۰۱۲۳۴۵۶۷۸۹`). Mixing them inside one interface looks careless, and mixing them inside one *number* looks broken.

Choose by domain: financial, trading, and data-dense interfaces overwhelmingly use Western digits because they sit alongside Latin tickers and imported data; consumer and editorial interfaces often prefer Persian digits.

Then apply it through the formatter, never by hand:

```js
new Intl.NumberFormat('fa-IR').format(1234567.89)        // ۱٬۲۳۴٬۵۶۷٫۸۹
new Intl.NumberFormat('fa-IR-u-nu-latn').format(1234567.89)  // 1,234,567.89
```

Note that Persian uses `٬` as the thousands separator and `٫` as the decimal separator — different characters from the Latin comma and period. `Intl` handles this; string concatenation does not.

Dates: the Persian (Jalali/Solar Hijri) calendar is the civil calendar in Iran. Use `Intl.DateTimeFormat('fa-IR')`, which handles it, rather than converting by hand. If the product shows both calendars, make which-is-which unambiguous rather than relying on the user to infer it from the year.

### Typography

**Typefaces.** Arabic-script type has different metrics from Latin: taller ascenders and descenders, more diacritic space, connected letterforms, and no capitals — so the usual vertical-rhythm assumptions don't carry over. Vazirmatn is the common open choice for Persian UI and has matched Latin glyphs, which avoids the mismatched-fallback look. Always declare the Persian face *before* the Latin fallback in the stack, and verify the Latin glyphs in mixed strings don't come from a different family than the surrounding text.

**Size and leading.** Persian text generally needs slightly larger size and noticeably more line-height than Latin at the same nominal point size — Arabic script renders smaller at equivalent font-size values and the descenders need room. Start at `1.05–1.15em` relative to your Latin size and `line-height: 1.75–1.9` for body text, then check optically.

**Things that don't apply.** No letter-spacing — it breaks the connecting strokes between letters and makes the text unreadable, not airy. No small caps, no all-caps treatments, no faux bold (synthesized weight destroys Arabic letterforms — load the real weight or don't use it). Italic is not a Persian typographic convention; use weight or color for emphasis instead.

**Justification.** Persian and Arabic traditionally justify by stretching connections (kashida), not by expanding word spaces. Browser support for `text-justify` on Arabic script is inconsistent, so `text-align: start` is usually safer than justified text with rivers running through it.

### Mixed-direction content

This is where most RTL implementations break, and it is constant in Persian financial content — a sentence containing a ticker, a percentage, a Latin brand name, and a bracketed note.

Mark the language of embedded passages so screen readers switch voice correctly and so the bidirectional algorithm resolves properly:

```html
<p>قیمت <span lang="en" dir="ltr">XAUUSD</span> به ۳٬۲۴۰ دلار رسید.</p>
```

For user-generated or API-supplied strings whose direction you don't know at build time, use `dir="auto"` on the element — the browser infers direction from the first strong character, which is right far more often than a hard-coded guess.

For inputs that must stay LTR inside an RTL form (emails, URLs, tickers, phone numbers, IBANs), set `dir="ltr"` on the field itself while keeping the label RTL. Otherwise the cursor and punctuation behave in ways users read as a bug.

Punctuation at the boundary between scripts is the classic failure — a trailing period or parenthesis jumping to the wrong end of the line. When it happens, the fix is usually an isolation wrapper (`<bdi>` or `unicode-bidi: isolate`) around the embedded run, not a manual character reorder.

### Testing procedure

1. Toggle `dir="rtl"` on `<html>` and walk every screen. Anything that doesn't move was written with physical properties — fix it at the source, not with an override.
2. Check icons individually against the flip/don't-flip list. Automatic mirroring of every icon is as wrong as mirroring none.
3. Verify numbers, dates, times, and currency in real formatted output, not placeholder strings.
4. Test with the longest realistic Persian string. Persian translations of English UI labels commonly run 20–40% longer; fixed-width buttons and single-line nav items are where this shows up first.
5. Test a mixed string containing Persian, a Latin brand name, a number, and trailing punctuation.
6. Run the keyboard tab order — it should follow visual order in RTL, which means right to left.
7. Check scrollbar position, sticky positioning, and any absolutely positioned element (badges, close buttons, dropdown alignment). These are the ones that survive a careless RTL pass.

---

## PART FIVE — REVIEW RUBRIC

Use this before delivering anything, and whenever asked to critique an existing interface.

A review that finds nothing wrong wasn't a review. Go looking for the failure, not for confirmation.

### How to report

Score each of the seven sections **Pass / Weak / Fail**. For every Weak or Fail, give the specific location, why it matters to a user, and the concrete fix. Vague findings ("could be more accessible") are worthless — name the element and the value.

Lead the report with the three highest-impact problems. Then the section table. Then the rest.

---

### 1. Purpose

- Can you state the one job of this screen in a sentence, just by looking at it?
- Is the primary action visually primary, and is there exactly one of them?
- Does anything compete with it for attention that shouldn't?
- Is anything on screen that serves no decision the user has to make?

**Fail if** the screen has three co-equal calls to action, or if the most visually dominant element isn't the most important one.

### 2. Hierarchy and structure

- Does the visual weight order match the importance order?
- Does the heading outline read as a sensible document when you strip the styling?
- Is the grouping in the layout the same as the grouping in the content's logic?
- Is spacing doing the grouping work, or are there boxes around things that didn't need boxes?

**Fail if** the heading levels were chosen for size, or if every content group is wrapped in an identical card regardless of its role.

### 3. The system

- Every color from the token set? Any raw hex in a component?
- Every spacing value on the 4px scale? Any 13px, 22px, 38px?
- Every font size from the type scale?
- Radius, shadow, and border consistent with the token definitions?
- Do the shadows model one light source, or several?

**Fail if** you find more than two off-scale values. This is the fastest tell of an unsystematic design and the cheapest thing to fix.

### 4. States

For every data-bearing component, check all six exist and are designed:

| | Empty | Loading | Partial | Error | Ideal | Overloaded |
|---|---|---|---|---|---|---|

- Does the loading state hold the layout the content will occupy?
- Does the empty state explain and offer an action, or just say "No data"?
- Does the error state say what to do next, in the interface's voice?
- What happens at 500 rows, a 90-character title, a missing image, a negative number?

**Fail if** only the ideal state exists. This is the most common defect in generated UI.

### 5. Accessibility

Spot-check against **Part Two**. Minimum pass:

- Contrast measured on real rendered pixels: 4.5:1 text, 3:1 large text and UI boundaries, in both themes and every interaction state
- Full keyboard operation of the primary task, no traps, focus never obscured by sticky chrome
- Visible focus indicator, ≥2px, ≥3:1 against both element and surroundings
- Targets ≥24px, 44px for touch
- Every input labeled; every icon-only control named
- Color is never the only channel for meaning
- Reflows at 320px with no horizontal scroll
- `prefers-reduced-motion` honored

**Fail if** any one of these is missing. There is no partial credit on keyboard access.

### 6. Performance and craft

- LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 at p75
- Explicit dimensions or `aspect-ratio` on every image, video, embed
- `font-display: swap` plus a metric-matched fallback
- Nothing inserted above existing content after load
- Transitions 150–300ms with appropriate easing; no motion on load that isn't one deliberate orchestrated moment
- Responsive from 320px up, with no reliance on hover alone

**Fail if** anything can shift the layout after paint. It's the cheapest fix and the most noticeable defect.

### 7. Distinctiveness

Run the substitution test: could this design be dropped onto a completely different product in a different industry without anyone noticing? If yes, it's a template, not a design.

- Do the palette, type, and density come from this subject's world, or from a trend list?
- Is there one memorable element, and is everything around it disciplined enough to let it be memorable?
- Check against the anti-pattern list in Part One — how many of the tells are present?
- What's the one thing you'd remove?

**Fail if** three or more anti-patterns are present, or if the substitution test passes.

---

### Report template

```
## Top three
1. [problem] — [where] — [why it matters] — [fix]
2. …
3. …

## Section scores
Purpose            Pass / Weak / Fail — one line
Hierarchy          …
System             …
States             …
Accessibility      …
Performance        …
Distinctiveness    …

## Everything else
Grouped by section, each with location and fix.

## What's working
Two or three specifics, named. Not a compliment paragraph — the point is
to identify what must survive the revision.
```

---

## PART SIX — DESIGN TOKENS (starter stylesheet)

Copy this, adapt the hues and the type stack to the brief, and paste it at the
top of the stylesheet. Shipping it unchanged produces a competent design with no
point of view — the hues are deliberately neutral so that adapting them is a
deliberate act.

```css
/* ============================================================
   Design tokens — 2026 starter
   Copy this, then adapt the hues and the type stack to the brief.
   The defaults here are deliberately neutral; shipping them
   unchanged produces a competent design with no point of view.

   Three layers, and components never reach past their layer:
     primitive  raw values, no meaning
     semantic   role and intent
     component  local binding
   ============================================================ */

@layer reset, base, components, utilities;

/* ---------- 1. PRIMITIVES ---------- */

:root {
  /* Neutral ramp — adjust the hue (250) to warm or cool the whole UI.
     A hint of chroma at the dark end reads as intentional; pure grey
     reads as unfinished. */
  --n-50:  oklch(98.5% 0.002 250);
  --n-100: oklch(96%   0.004 250);
  --n-200: oklch(92%   0.006 250);
  --n-300: oklch(86%   0.008 250);
  --n-400: oklch(72%   0.012 250);
  --n-500: oklch(60%   0.014 250);
  --n-600: oklch(50%   0.016 250);
  --n-700: oklch(40%   0.018 250);
  --n-800: oklch(30%   0.018 250);
  --n-900: oklch(22%   0.016 250);
  --n-950: oklch(16%   0.014 250);

  /* Brand ramp — replace the hue. OKLCH keeps the lightness steps
     perceptually even when you do, which HSL does not. */
  --brand-50:  oklch(97% 0.02 255);
  --brand-100: oklch(94% 0.04 255);
  --brand-200: oklch(88% 0.08 255);
  --brand-300: oklch(80% 0.12 255);
  --brand-400: oklch(70% 0.16 255);
  --brand-500: oklch(62% 0.19 255);
  --brand-600: oklch(55% 0.19 255);
  --brand-700: oklch(47% 0.17 255);
  --brand-800: oklch(39% 0.14 255);
  --brand-900: oklch(31% 0.11 255);
  --brand-950: oklch(23% 0.08 255);

  /* Status — keep chroma close across the set so they read as a family */
  --success-500: oklch(62% 0.16 150);
  --warning-500: oklch(75% 0.15  80);
  --danger-500:  oklch(58% 0.20  25);
  --info-500:    oklch(62% 0.14 230);

  /* ---------- SPACING ---------- */
  /* One base unit. Nothing off this scale, ever. */
  --space-0:  0;
  --space-1:  0.25rem;   /*  4px */
  --space-2:  0.5rem;    /*  8px */
  --space-3:  0.75rem;   /* 12px */
  --space-4:  1rem;      /* 16px */
  --space-6:  1.5rem;    /* 24px */
  --space-8:  2rem;      /* 32px */
  --space-12: 3rem;      /* 48px */
  --space-16: 4rem;      /* 64px */
  --space-24: 6rem;      /* 96px */

  /* ---------- TYPE ---------- */
  /* Replace these families. The system stack is a fallback, not a choice.
     For RTL, declare the Arabic-script face FIRST so mixed strings don't
     pick up Latin glyphs from a different family. */
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, "SF Mono", "Cascadia Code", monospace;
  /* --font-fa: "Vazirmatn", var(--font-sans); */

  /* Scale: 16px base, 1.250 ratio. Use 1.200 for dense data UI,
     1.333 for marketing. clamp() gives fluid display sizes without
     a breakpoint table. */
  --text-xs:   0.75rem;    /* 12 */
  --text-sm:   0.875rem;   /* 14 */
  --text-base: 1rem;       /* 16 */
  --text-lg:   1.125rem;   /* 18 */
  --text-xl:   1.5rem;     /* 24 */
  --text-2xl:  clamp(1.75rem, 1.4rem + 1.5vw, 2.25rem);
  --text-3xl:  clamp(2.25rem, 1.7rem + 2.5vw, 3.5rem);

  /* Line-height moves inversely with size */
  --leading-tight:   1.15;
  --leading-snug:    1.35;
  --leading-normal:  1.55;
  --leading-relaxed: 1.7;

  --tracking-tight:  -0.02em;
  --tracking-normal: 0;
  /* No positive letter-spacing on Arabic-script text — it breaks
     the connecting strokes. */

  --measure: 65ch;   /* cap line length; 45–75 characters */

  /* ---------- RADIUS / BORDER / SHADOW ---------- */
  --radius-sm:   0.25rem;
  --radius-md:   0.5rem;
  --radius-lg:   1rem;
  --radius-full: 9999px;

  --border-thin:  1px;
  --border-thick: 2px;

  /* Three levels, one light source (above, slightly forward).
     More than three and elevation stops meaning anything. */
  --shadow-1: 0 1px 2px oklch(0% 0 0 / 0.06),
              0 1px 3px oklch(0% 0 0 / 0.08);
  --shadow-2: 0 2px 4px oklch(0% 0 0 / 0.05),
              0 4px 12px oklch(0% 0 0 / 0.10);
  --shadow-3: 0 4px 8px oklch(0% 0 0 / 0.05),
              0 12px 32px oklch(0% 0 0 / 0.14);

  /* ---------- MOTION ---------- */
  --duration-fast: 120ms;   /* state change: hover, toggle */
  --duration-base: 200ms;   /* reveal: dropdown, tooltip */
  --duration-slow: 320ms;   /* transition: page, modal */
  --ease-out:   cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);

  /* ---------- LAYERS ---------- */
  --z-base: 0;
  --z-sticky: 100;
  --z-overlay: 200;
  --z-modal: 300;
  --z-toast: 400;
}

/* ---------- 2. SEMANTIC ---------- */
/* light-dark() resolves against color-scheme, so one declaration
   covers both themes. Dark mode is a redefinition of roles here,
   never an inversion filter. */

:root {
  color-scheme: light dark;

  --color-canvas:        light-dark(var(--n-50),  var(--n-950));
  --color-surface:       light-dark(#fff,         var(--n-900));
  --color-surface-raised:light-dark(#fff,         var(--n-800));
  --color-surface-sunken:light-dark(var(--n-100), oklch(13% 0.012 250));

  --color-text:          light-dark(var(--n-900), var(--n-100));
  --color-text-muted:    light-dark(var(--n-600), var(--n-400));
  --color-text-subtle:   light-dark(var(--n-500), var(--n-500));
  --color-text-on-action:light-dark(#fff,         var(--n-950));

  --color-border:        light-dark(var(--n-200), var(--n-800));
  --color-border-strong: light-dark(var(--n-300), var(--n-700));

  /* Accents lose saturation in dark mode or they vibrate against
     dark surfaces. */
  --color-action:        light-dark(var(--brand-600), var(--brand-400));
  --color-action-hover:  light-dark(var(--brand-700), var(--brand-300));
  --color-focus:         light-dark(var(--brand-600), var(--brand-300));

  --color-success:       light-dark(var(--success-500), oklch(72% 0.13 150));
  --color-warning:       light-dark(var(--warning-500), oklch(82% 0.12  80));
  --color-danger:        light-dark(var(--danger-500),  oklch(68% 0.16  25));
}

/* ---------- 3. BASE ---------- */

@layer base {
  *, *::before, *::after { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--color-canvas);
    color: var(--color-text);
    font-family: var(--font-sans);
    font-size: var(--text-base);
    line-height: var(--leading-normal);
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }

  /* Persian/Arabic: larger optical size and more leading than Latin
     at the same nominal value. Uncomment and tune with --font-fa set. */
  /*
  :is([lang="fa"], [lang="ar"], [lang="ur"], [lang="he"]) {
    font-family: var(--font-fa);
    font-size: 1.08em;
    line-height: var(--leading-relaxed);
    letter-spacing: 0;
  }
  */

  h1, h2, h3, h4 {
    line-height: var(--leading-tight);
    letter-spacing: var(--tracking-tight);
    text-wrap: balance;
    margin-block: 0 var(--space-4);
  }
  h1 { font-size: var(--text-3xl); }
  h2 { font-size: var(--text-2xl); }
  h3 { font-size: var(--text-xl); }

  p { max-inline-size: var(--measure); text-wrap: pretty; }

  /* Images never shift the layout. This is the single cheapest CLS fix. */
  img, video, svg, iframe {
    max-inline-size: 100%;
    block-size: auto;
    display: block;
  }

  /* Focus: keyboard users get the ring, mouse users don't.
     Two offset rings keep it visible on any background. */
  :focus-visible {
    outline: var(--border-thick) solid var(--color-focus);
    outline-offset: 2px;
    border-radius: var(--radius-sm);
  }

  /* Sticky chrome must not hide the focused element (WCAG 2.2 SC 2.4.11) */
  :root { scroll-padding-block-start: var(--space-16); }

  /* Touch targets. 24px is the WCAG floor; 44px is the usable size. */
  button, a[href], [role="button"], input, select, summary {
    min-block-size: 44px;
    min-inline-size: 44px;
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }

  /* Translucent surfaces must have an opaque fallback */
  @media (prefers-reduced-transparency: reduce) {
    .glass { background: var(--color-surface); backdrop-filter: none; }
  }
}

/* ---------- 4. COMPONENT EXAMPLE ---------- */
/* Components bind to semantic tokens, never to primitives, and use
   logical properties so RTL costs one attribute on <html>. */

@layer components {
  .card {
    container-type: inline-size;   /* responds to its own space, not the viewport */
    background: var(--color-surface);
    border: var(--border-thin) solid var(--color-border);
    border-radius: var(--radius-lg);
    padding-inline: var(--space-6);
    padding-block: var(--space-4);
    box-shadow: var(--shadow-1);
  }

  /* Layout changes when the CARD is wide, regardless of screen width */
  @container (min-width: 30rem) {
    .card { display: grid; grid-template-columns: auto 1fr; gap: var(--space-4); }
  }

  .button {
    background: var(--color-action);
    color: var(--color-text-on-action);
    border: none;
    border-radius: var(--radius-md);
    padding-inline: var(--space-4);
    padding-block: var(--space-2);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out);
  }
  .button:hover { background: var(--color-action-hover); }

  /* Fluid grid with no breakpoints */
  .grid-auto {
    display: grid;
    gap: var(--space-4);
    grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  }
}

/* ---------- 5. UTILITIES ---------- */

@layer utilities {
  /* Accessible name for icon-only controls without visual text */
  .visually-hidden {
    position: absolute;
    inline-size: 1px; block-size: 1px;
    padding: 0; margin: -1px;
    overflow: hidden; clip-path: inset(50%);
    white-space: nowrap;
  }

  /* Keep numbers, tickers, and URLs LTR inside RTL content */
  .ltr { direction: ltr; unicode-bidi: isolate; }
}
```