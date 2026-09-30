---
name: cultureQC
description: Two surfaces, two worlds — a dark exception-review console and a light scientific site that shows the pipeline's real output on dark microscopy stages
colors:
  # ── The Console World (demo/app.py) ──
  console-bg-primary: "#0f1117"
  console-bg-card: "#1a1d24"
  console-border: "#2a2d34"
  console-text-primary: "#f0f0f0"
  console-text-secondary: "#9ca3af"
  console-text-muted: "#6b7280"
  console-status-green: "#22c55e"
  console-status-amber: "#f59e0b"
  console-status-red: "#ef4444"
  console-accent: "#3b82f6"
  console-on-accent: "#ffffff"
  console-fill-inactive: "#4b5563"
  console-scrollbar-hover: "#363a44"
  # ── The Category Standard (site/src/App.jsx) ──
  # key site-X is the CSS custom property --X in site/src/styles.css
  # reading surface
  site-paper: "#f5f6f8"
  site-panel: "#ffffff"
  site-recess: "#fafbfc"
  site-ink: "#0d1117"
  site-ink-2: "#353e4a"
  site-ink-3: "#56616e"
  site-rule: "#e1e5ea"
  site-rule-2: "#c8cfd7"
  # microscopy stages
  site-stage: "#0a0c0f"
  site-stage-2: "#11151a"
  site-stage-3: "#1a1f26"
  site-stage-rule: "#29313b"
  site-stage-rule-2: "#3d4652"
  site-stage-ink: "#e9ecf0"
  site-stage-ink-2: "#a9b2bc"
  site-stage-ink-3: "#86919d"
  # what the models computed
  site-cell: "#2cc7da"
  site-cell-ink: "#04707f"
  site-anom: "#e357b9"
  # actions (print value on the reading surface, -l lifted value on a stage)
  site-passage: "#1d7f45"
  site-passage-l: "#5fd394"
  site-hold: "#9a5c00"
  site-hold-l: "#f3b44a"
  site-review: "#bb3226"
  site-review-l: "#ff8072"
  site-reimage: "#4f4fc4"
  site-reimage-l: "#a9aaf8"
typography:
  # ── The Console World ──
  console-display:
    fontFamily: "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"
    fontSize: "52px"
    fontWeight: 700
    lineHeight: 1
  console-title:
    fontFamily: "ui-sans-serif, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "21px"
    fontWeight: 600
    letterSpacing: "-0.01em"
  console-body:
    fontFamily: "ui-sans-serif, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  console-label:
    fontFamily: "ui-sans-serif, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "13px"
    fontWeight: 400
  console-label-large:
    fontFamily: "ui-sans-serif, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "16px"
    fontWeight: 600
  console-unit:
    fontFamily: "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"
    fontSize: "26px"
    fontWeight: 600
  console-mono:
    fontFamily: "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
  console-micro:
    fontFamily: "ui-sans-serif, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "12px"
    fontWeight: 400
  # ── The Category Standard ──
  site-display:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(30px, 2.9vw, 42px)"
    fontWeight: 620
    lineHeight: 1.02
    letterSpacing: "-0.035em"
  site-headline:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(27px, 2.9vw, 40px)"
    fontWeight: 610
    lineHeight: 1.08
    letterSpacing: "-0.03em"
  site-title:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "15.5px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.01em"
  site-body:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "'ss01', 'cv11'"
  site-body-small:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  site-caption:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
  site-label:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 550
  site-button:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 550
    lineHeight: 1
  site-action:
    fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 650
    lineHeight: 1
    letterSpacing: "0.06em"
  site-readout:
    fontFamily: "'Geist Mono Variable', ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "clamp(36px, 3.1vw, 44px)"
    fontWeight: 560
    lineHeight: 1
    letterSpacing: "-0.04em"
    fontFeature: "'tnum', 'zero'"
  site-data:
    fontFamily: "'Geist Mono Variable', ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "12.5px"
    fontWeight: 500
    lineHeight: 1.5
    fontFeature: "'tnum'"
  site-data-small:
    fontFamily: "'Geist Mono Variable', ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "11.5px"
    fontWeight: 500
    lineHeight: 1.35
    fontFeature: "'tnum'"
rounded:
  console-sm: "8px"
  console-md: "10px"
  console-lg: "12px"
  console-pill: "999px"
  site-stage: "10px"
  site-container: "8px"
  site-control: "6px"
  site-small: "4px"
  site-image: "3px"
  site-mark: "2px"
  site-pill: "999px"
spacing:
  console-sm: "10px"
  console-md: "16px"
  console-lg: "20px"
  site-wrap: "1320px"
  site-pad: "clamp(16px, 3.2vw, 40px)"
  site-sec-top: "clamp(64px, 7vw, 104px)"
  site-head-gap: "clamp(24px, 3vw, 36px)"
  site-gap: "16px"
  site-bar: "56px"
components:
  console-status-card:
    backgroundColor: "{colors.console-status-green} @ 8%"
    textColor: "{colors.console-status-green}"
    rounded: "{rounded.console-md}"
    padding: "16px"
  console-action-badge:
    backgroundColor: "{colors.console-status-green} @ 15%"
    textColor: "{colors.console-status-green}"
    rounded: "{rounded.console-pill}"
    padding: "10px 20px"
  console-analyze-button:
    backgroundColor: "{colors.console-accent}"
    textColor: "{colors.console-on-accent}"
    rounded: "{rounded.console-sm}"
    padding: "8px 20px"
    height: "40px"
    width: "min 116px"
  console-control-cluster:
    backgroundColor: "{colors.console-bg-card}"
    rounded: "{rounded.console-sm}"
    padding: "0"
  site-button-primary:
    backgroundColor: "{colors.site-ink}"
    textColor: "{colors.site-panel}"
    typography: "{typography.site-button}"
    rounded: "{rounded.site-control}"
    padding: "0 15px"
    height: "38px"
  site-button-primary-hover:
    backgroundColor: "#262d36"
  site-nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.site-ink-2}"
    rounded: "{rounded.site-small}"
    padding: "6px 10px"
  site-nav-link-current:
    backgroundColor: "#e4e8ed"
    textColor: "{colors.site-ink}"
  site-stage:
    backgroundColor: "{colors.site-stage}"
    textColor: "{colors.site-stage-ink}"
    rounded: "{rounded.site-stage}"
  site-layer-chip:
    backgroundColor: "transparent"
    textColor: "{colors.site-stage-ink-2}"
    rounded: "{rounded.site-pill}"
    padding: "0 10px"
    height: "28px"
  site-layer-chip-pressed:
    backgroundColor: "{colors.site-stage-3}"
    textColor: "{colors.site-stage-ink}"
  site-tab:
    backgroundColor: "transparent"
    textColor: "{colors.site-stage-ink-2}"
    rounded: "{rounded.site-small}"
    padding: "0 12px"
    height: "30px"
  site-tab-selected:
    backgroundColor: "{colors.site-stage-3}"
    textColor: "{colors.site-stage-ink}"
  site-action-badge:
    backgroundColor: "transparent"
    textColor: "{colors.site-hold-l}"
    typography: "{typography.site-action}"
    rounded: "{rounded.site-small}"
    padding: "0 12px 0 10px"
    height: "30px"
  site-panel-letter:
    backgroundColor: "transparent"
    textColor: "{colors.site-ink}"
    rounded: "{rounded.site-image}"
    padding: "3px 5px"
  site-figure:
    backgroundColor: "{colors.site-panel}"
    textColor: "{colors.site-ink}"
    rounded: "{rounded.site-container}"
    padding: "18px 20px 16px"
  site-chain-link:
    backgroundColor: "{colors.site-panel}"
    textColor: "{colors.site-ink}"
    padding: "14px"
  site-chain-link-broken:
    backgroundColor: "#fdf2f1"
  site-code:
    backgroundColor: "{colors.site-stage}"
    textColor: "{colors.site-stage-ink}"
    typography: "{typography.site-data}"
    rounded: "{rounded.site-container}"
    padding: "18px 20px"
---

# Design System: cultureQC

## Overview

**This file records two visual worlds. They do not blend. Find your surface in the routing table before you read anything else.**

| If you are editing… | The governing world | Its brief | Token prefix |
| --- | --- | --- | --- |
| `demo/app.py` (the exception-review console) | **The Instrument Console** | `.impeccable/surfaces/demo-app-py.md` | `console-*` |
| `site/src/App.jsx` (the v0.3 React site; also `site/src/components/*.jsx`, `site/src/styles.css`, `site/index.html`) | **The Category Standard** | `site/.impeccable/surfaces/site-src-app-jsx.md` | `site-*` (frontmatter key `site-X` is the custom property `--X` on `:root` in `site/src/styles.css`; there is no `--site-` prefix in the CSS) |

Every token in the frontmatter is namespaced by surface. Every canonical section below is split into `### The Console World` and `### The Category Standard`. A value, a rule or a component from one world is not evidence for the other; there is no shared palette, no shared type stack and no shared shape vocabulary. The two surfaces do not even share a colour vocabulary for status: the console paints the QC verdict green/amber/red, while the site has no QC-verdict colour at all — it colours by *who computed a layer* (cyan, magenta) and by *action* (passage, feed/hold, human review, re-image).

**Do not copy a rule across the boundary.** If a new surface appears, it gets its own world block and its own prefix; it does not inherit either of these two.

---

### The Console World (`demo/app.py`)

**Creative North Star: "The Instrument Console"**

cultureQC's console is styled as the on-screen readout of a piece of lab hardware, not a web form wrapped around a model. The reference class is the confluency imager's own console — Sartorius Incucyte, Molecular Devices CellXpress.ai, Leica Mateo — where the specimen image is the largest thing on the glass, verdict is read by color before anyone parses a word, and the instrument's own paper trail sits one click away, never in the way. The audience is someone deciding whether to trust this instrument with a production decision; the surface has to look like it already belongs in that rack, not like a prototype asking to be taken seriously.

Density is low and deliberate: three inputs total, five result elements, one screen, no scroll. The palette stays almost entirely neutral — near-black ground, charcoal cards, silver-gray text — so that the one place color appears (the QC verdict and the action it drives) reads as a signal, not decoration. Confirmed rejection: no Gradio-default purple/orange, no light mode, no dashboard chrome (KPI tiles, sidebars, nav rails) — this is one instrument, one reading.

The status card carries a full per-class probability breakdown and an evidence-region tally beneath the verdict row, so the "why" behind a flag is visible without opening the audit record. The image pane has its own material — a fine grid and vignette standing in for a flat card fill — so the letterboxed margins around non-square tiles read as a calibrated stage rather than dead space.

**Key Characteristics:**
- Image first: the specimen view is the largest element on screen at all times, ~62% of viewport width, fixed by grid track rather than flex growth.
- Verdict by color: status, action, and progress-bar fill all carry meaning through the same three-color status system before any label is read.
- Everything is a card except the rationale, which is deliberately plain text — the one place the UI drops its own chrome to let a sentence be read as a sentence.
- The audit trail is always present, never announced: one quiet disclosure row, full fidelity underneath, and a per-class evidence breakdown one level up, inside the status card itself.

### The Category Standard (`site/src/App.jsx`)

**Creative North Star: "The Category Standard, Played Straight"**

The v0.3 site is scientific instrument software documentation, not a metaphor. It sits in the reference class of the Allen Institute Cell Explorer, Zeiss ZEN / Leica LAS X, 10x Genomics / Benchling and Linear / Stripe docs: a cool light reading surface for prose, tables and figures, and dark neutral stages wherever microscopy is shown, because phase-contrast frames lose their contrast on a light ground. The product's own output leads: a real held-out frame, the layers the pipeline actually computed for it, the readings with their confidence, the action the rules took, and the sealed record re-hashed in the visitor's browser.

Colour is spent on meaning and nowhere else. Cyan is what the segmentation model computed; magenta is what the anomaly check computed; four action hues mean go, hold, stop-for-a-person and re-image, and each always travels with its word and its own icon. Everything else is neutral: near-white paper, white panels, slate ink, 1px hairlines. Type is two faces with two jobs — Geist Sans for every sentence and heading, Geist Mono with tabular figures for every measured number, hash, path and axis tick. Every figure is labelled like a paper's: a panel letter, n, its source file, and a true scale bar where the pixel size is known. No number is typed into a component; each is read from `site/src/data.json`, which `site/assets/build_data.py` generates from the repo's results.

Density is moderate and document-like: a 1320px measure, a sticky 56px bar, section heads with the headline left and the lede right, and generous section gaps. Motion is state change only — short colour transitions and a layer fade — with no entrance choreography.

**Key Characteristics:**
- Light reading surface, dark stages: microscopy, the timeline chart, JSON and code sit on near-black; everything a person reads as prose sits on paper.
- Cyan = segmentation model, magenta = anomaly check; the image's computed layers and their gauges use these two and nothing else.
- Action hues are always hue + icon + word; a verdict is always icon shape + word.
- Geist Sans for language, Geist Mono tabular for measurement.
- Every figure: panel letter, n, source file, true scale bar where known; every number from `data.json`.
- Flat, hairline-ruled, small radii.

## Colors

### The Console World

Almost entirely neutral, with color spent exclusively on QC status — never on branding, decoration, or emphasis unrelated to the verdict.

#### Primary
- **Signal Blue** (`#3b82f6`): the one always-interactive color — the Analyze button, focus rings, the wordmark's status dot (including its breathing pulse). Never used for QC status; keeping it out of the status vocabulary means it can't be mistaken for a verdict.

#### Neutral
- **Near-Black Ground** (`#0f1117`): page background. Deep enough that the status-tinted cards and the green cell-mask overlay both read clearly against it.
- **Charcoal Card** (`#1a1d24`): every card surface and the topbar control-cluster's fill; the audit JSON block is darker still at `#12141a`.
- **Graphite Border** (`#2a2d34`): all 1px card and control borders, including the control-cluster's outer border and its internal field divider, and the evidence-breakdown's two divider rules inside the status card.
- **Bone White** (`#f0f0f0`): primary text — headings, the confluency number.
- **Silver Gray** (`#9ca3af`): secondary text — card meta, rationale, labels, the chevron glyph on the cell-line field, and the label text of a non-predicted evidence row.
- **Slate Gray** (`#6b7280`): tertiary/muted text — footer (including the classifier-provenance disclosure), placeholder, collapsed-state chrome.
- **Ash Fill** (`#4b5563`): the system's one "inactive but present" fill — the confluency bar's below-target fill, and the bar fill of the three non-predicted rows in the evidence breakdown. Distinct from Slate Gray text: this is a fill color for a track/bar, not a text color, and is a shade darker so an inactive bar never competes with the muted labels sitting next to it.

#### Status (Green / Amber / Red)
- **Status Green** (`#22c55e`): `normal` QC flag, `passage` action, confluency-bar fill once actual ≥ target, and the predicted-class row's bar/label in the evidence breakdown when the flag is `normal`.
- **Status Amber** (`#f59e0b`): `detachment` and `image_quality` QC flags, `feed`/`hold` actions.
- **Status Red** (`#ef4444`): `contamination_suspected` QC flag, `human_review` action, the evidence bounding boxes drawn on the image overlay, and the evidence-region-count dot in the status card. Red is reserved for this one meaning system-wide.

#### Named Rules
**The Two-Axis Status Rule.** The status card's color (the QC verdict) and the action badge's color (the recommended action) are two independent axes that happen to share one three-color vocabulary, not one signal painted twice. They usually agree, but the rules engine (`culture/rules.py::decide()`) legitimately splits them in a specific, desired direction: a **green** (`normal`) verdict can pair with an **amber** (`feed`/`hold`) action when confluency simply hasn't reached target yet — "nothing's wrong, just not there yet" is a correct reading, not a defect, and the card and badge are allowed to disagree in exactly this way. The coupling that *does* hold as an invariant: a non-`normal` QC flag at or above the review-confidence threshold always forces `human_review`, so red on the status card and red on the action badge are shared whenever the flag reaches that threshold. Below threshold the two axes fully decouple in the shipped rules engine — a low-confidence non-`normal` flag can still draw red evidence boxes on the image while the action badge reads green or amber — but that decoupling is a byproduct of the confidence-threshold rule, not a pattern to design toward; new surfaces should assume verdict-color and action-color are independent unless proven coupled by the same threshold logic.

### The Category Standard

Neutral cool greys on two grounds, with colour reserved for two computed layers and four actions.

#### Primary — what the models computed
- **Segmentation Cyan** (`site-cell`): Cellpose-SAM's output on a stage — the cell-probability layer (screen-blended at 62%), the cutoff contour, the confluency gauge fill, the mean-of-3-fields line and markers on the timeline chart, and the timeline's cell-probability map. It also carries the interface's *selection* on a stage: the active example's top bar in the strip, the current visit, the `::selection` tint and the on-stage focus ring — the "active layer" the direction contract names — and, as a pale tint, the pressed chain tile on paper.
- **Deep Cyan** (`site-cell-ink`): the same role on the light surface, where the bright cyan would fail contrast — the Cellpose-SAM bar and the noise-model lines in the confluency figures, and the global focus ring.
- **Anomaly Magenta** (`site-anom`): DINOv2's output — the anomaly-patch heat layer and its centre-tile outline, the anomaly gauge fill, the "Flagged" word, the timeline's anomaly-flag diamonds and its fault-onset marker.

#### Secondary — actions
Each action has a print value for the paper and a lifted `-l` value for a stage, where the print value would disappear.
- **Passage Green** (`site-passage` / `site-passage-l`): passage.
- **Hold Amber** (`site-hold` / `site-hold-l`): feed and hold.
- **Review Red** (`site-review` / `site-review-l`): human review; also the review-rate bars (frames sent to a person) and the tamper switch's on state, because tampering is what forces review.
- **Re-image Indigo** (`site-reimage` / `site-reimage-l`): re-image, and the quality-gate failure that triggers it (outlined visit squares, hatched visit buttons).

#### Neutral
- **Paper** (`site-paper`): the page ground and the sticky bar (at 97%).
- **Panel** (`site-panel`) and **Recess** (`site-recess`, a literal in the stylesheet): figure, table and chain-tile fill; table heads and the "what v0.2 showed" column.
- **Ink / Ink 2 / Ink 3** (`site-ink`, `site-ink-2`, `site-ink-3`): headings and figures; prose and table body; captions, legends, sources and meta. Ink is also the primary button's fill.
- **Rule / Rule 2** (`site-rule`, `site-rule-2`): row and panel hairlines; structural rules (table head, quiet borders, scrollbar thumb, the threshold-baseline bar).
- **Stage ramp** (`site-stage` → `site-stage-2` → `site-stage-3`): stage ground, hover/frame-box fill, selected fill and gauge track. **Stage rule** (`site-stage-rule`, with `site-stage-rule-2` for a pressed chip, selected tab or panel-letter border) and **Stage ink 1–3** for text on a stage.

#### Named Rules
**The Who-Computed-It Rule.** Cyan is the segmentation model and magenta is the anomaly check. A layer, gauge, chart mark or word takes one of these only if that model produced it. Cyan also marks the interface's current selection and focus (the focus ring, `::selection`, the active example, the current visit, the pressed chain tile's tint), because the selected thing is always a view onto computed output; nothing else borrows either hue, and magenta never marks selection.

**The Action Hue Rule.** The four action hues mean go (passage), wait (feed/hold), stop for a person (human review) and take it again (re-image). They are never decoration and never an accent. Every action appears as hue + its own icon + its word — the icons are an arrow for passage, a drop for feed, a pause for hold, a person for human review and a cycle for re-image — and an action badge sits next to a plain-language gloss of what it means for the flask. The same go/stop/partial hues also colour the site's pass/fail verdicts (validation checks, the detectability matrix, chain verification), always through the verdict component's shape icon and word (see The Shape-and-Word Rule); they never colour anything that is neither an action nor a pass/fail result.

## Typography

### The Console World

**Display/Mono Font:** `ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace`
**Body Font:** `ui-sans-serif, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif`

**Character:** System stacks throughout, deliberately — this is instrument software, not a marketing surface, and a system sans plus a system mono reads as "this ships on any lab machine" rather than "this needed a font license." The mono face is reserved for the one number the reading is actually about (confluency %), the one block that must look like raw data (the audit JSON), and the small percentage figures in the evidence breakdown.

#### Hierarchy
- **Display** (700, 52px, mono, line-height 1): the confluency percentage. The single largest text element on screen after the image itself. Counts up from `0.0` on load.
- **Title** (600, 21px, sans, letter-spacing -0.01em): the QC status label ("Normal", "Contamination Suspected").
- **Label-large** (600, 16px, sans): the action badge text.
- **Body** (400, 14px, sans, line-height 1.55): the rationale sentence — the only unstyled prose on the screen.
- **Label** (400, 13px, sans): card secondary metadata (confidence pill, confluency target/method line, evidence-row labels), and the topbar's cell-line/target-% field text.
- **Mono-small** (400, 12px, mono): the audit JSON block and the evidence-row percentage figures.
- **Micro** (400, 12px, sans): footer (including the classifier-provenance line), view-toggle pill labels, the evidence-region-count line.

#### Named Rules
**The No-Label Rule.** Result readouts are never preceded by a form-style caption ("Status:", "Action:"). The card's color, icon, and type scale carry the meaning; a label would be redundant with what the eye already read. This governs *output*, not input: the target-% field's inline `%` suffix (drawn via `::after`, never a separate label) is the sanctioned exception — it disambiguates a bare number the user is editing, not a result the system is reporting.

**The Headline-vs-Row Copy Rule.** The status card's headline uses the full verdict phrase ("Contamination Suspected"); the evidence breakdown's row label for the same class uses the shorter form ("Contamination"). This isn't inconsistency — the headline has the full card width and reads as a sentence-level verdict, while the row label shares a fixed-width column with a bar and a percentage and would truncate or wrap under the longer phrase. Two label lengths for the same class are correct as long as each stays scoped to its own layout context; don't shorten the headline to match the row, and don't lengthen the row to match the headline.

### The Category Standard

**Sans Font:** `Geist Variable` (self-hosted via `@fontsource-variable/geist`), falling back to `ui-sans-serif`, `system-ui`
**Mono Font:** `Geist Mono Variable` (via `@fontsource-variable/geist-mono`), falling back to `ui-monospace`, SF Mono, Menlo

**Character:** One family in two cuts. The sans is the document: headings in tight, slightly heavy intermediate weights (610–650) with negative tracking, prose at 400 with the `ss01`/`cv11` stylistic sets. The mono is the instrument: every measured number, threshold, hash, repo path, record field name, axis tick and scale-bar label, always with tabular figures (`.num` adds slashed zero).

#### Hierarchy
- **Display** (`site-display`, `max-width: 15ch`, `text-wrap: balance`): the one `h1` in the headline row.
- **Headline** (`site-headline`, `max-width: 20ch`, balanced): every section head, set left of its lede.
- **Title** (`site-title`): figure titles; the stage rail's example name is the same role at 15px.
- **Body** (`site-body`): section ledes at `max-width: 60ch`; the hero paragraph is a step smaller (14.5px/1.5, 56ch).
- **Body small** (`site-body-small`): table cells and the scope note.
- **Caption** (`site-caption`, Ink 3): figure legends, source lines, the footer, stage notes (12.5px on a stage).
- **Label** (`site-label`): reading headers, table heads, chips, tabs, panel headings.
- **Button** (`site-button`) and **Action** (`site-action`, uppercase): the primary control; the action badge's word.
- **Readout** (`site-readout`, `%` as a `.42em` Stage-ink-2 suffix): the confluency reading on the stage.
- **Data** (`site-data`) and **Data small** (`site-data-small`): hashes, record fields, bar values, JSON; source tags, gauge legends, strip meta and chain digests.

#### Named Rules
**The Two Cuts Rule.** Geist Sans for language, Geist Mono tabular for measurement. A number that was measured, a hash, a path or a field name is mono with tabular figures; a sentence, heading or control label is sans. Numbers inside a sentence take the `.num` class so they align and read as data.

## Layout

### The Console World

Full-viewport split pane, no page scroll: a topbar (fixed height), a main row (grid, fills remaining height), and a one-line footer. The main row (`.main-row`) is a CSS grid — `grid-template-columns: 62fr 38fr`, `grid-template-rows: minmax(0, 1fr)`, 20px gap — not a flex row: the 62/38 image/results split is a fixed track ratio, so the image pane's size holds steady regardless of the audit record's expand/collapse state underneath it. The results pane is the only element permitted its own internal scroll; that scroll is load-bearing, not a rare-case safety net — it's how the audit record can expand to full height without ever resizing the image pane or the page.

Card rhythm in the results stack: 12px gap between cards, 16px internal card padding. Cards stagger into view 100ms apart on analysis complete (status+evidence → confluency → action → rationale → audit) — five stagger steps, not six. The evidence breakdown is internal structure of the status card, not a sixth card; it was built as a standalone sixth card first and folded into the status card specifically because a sixth card overflowed the fixed 1280×800 no-scroll budget and clipped the action badge.

Topbar controls are compact and un-labeled, right-aligned, sitting inline with the wordmark rather than in a form column. The cell-line dropdown and target-% field are grouped into a single bordered **control-cluster** unit with a 1px divider between them; the Analyze button sits outside the cluster as the one squared-off, fixed-size (min 116×40px) action that never stretches to fill the row. Three inputs (cell line, target %, Analyze) is the ceiling.

### The Category Standard

**The page.** One centred column at `site-wrap` with `site-pad` sides. A sticky 56px bar (paper at 97%, a rule beneath) carries the wordmark with its mono version tag, a horizontally scrolling section nav (current section filled `#e4e8ed`), and the one primary button, "Live console". Sections open at `site-sec-top` with no bottom padding; the footer closes at `clamp(72px, 8vw, 112px)`.

**The section head.** A two-column grid (`1fr 1fr`, 56px gap, bottom-aligned): headline left, lede and a Caption-set source line right. There is nothing above the headline.

**The first viewport.** A compact headline row (`0.9fr 1.1fr`: `h1` left, one paragraph right), then the specimen stage across the full width. The stage grid is the viewer (`1fr`) beside a readout rail (`clamp(300px, 29%, 380px)`); the viewer is a toolbar of layer chips over a frame sized from the image's own aspect ratio and capped to the viewport height (`100vh − 352px`, floor 300px). Under both runs the seven-example strip and a two-column stage note. Criterion carried from the contract: at 1280×720 the action and the record's re-hash line sit above the fold.

**Figures.** `site-gap` grids of two or three figure panels (`g2`, `g3`, `g-limits` at `1.35fr 1fr`). Tables live in a bordered, focusable, horizontally scrolling region.

**The timeline stage.** Flask tabs across the top; a map column (`0.9fr`: the visit's probability map with numbered field boxes, then a 3-up readout grid) beside the chart (`1.25fr`) with a visit button row under its x-axis; a foot with the forecast sentence and the key.

**Breakpoints** (max-width): **1080** — the stage and timeline go single-column (the viewer's right rule becomes a bottom rule), the strip goes to 4 columns, the chain to 4 separated tiles, the two-up record/integration/limits grids stack; **760** — the nav is hidden (the button stays), the headline row, section heads, figure grids, timeline foot and footer stack, the strip goes to 2 columns, the chain to 2, the readout grid to 2.

#### Named Rules
**The Measured Frame Rule.** A microscopy frame takes `aspect-ratio` from its own width and height and every overlay is drawn in that frame's pixel space (`viewBox` of the image, `preserveAspectRatio="none"`, non-scaling strokes), so a layer never drifts off the cells it was computed on. Never set a fixed height or a guessed ratio.

**The Lit Reading Rule.** Hovering or focusing a reading on the rail solos the layer it was measured on: the frame dims to 62% brightness and only that layer shows (confluency → contour, confidence → borderline band, anomaly → patches). A reading that cannot be pointed at on the image has no link and no hover state.

## Elevation & Depth

### The Console World

Flat by design. No drop shadows anywhere — depth is conveyed entirely through the 1px graphite border and background-fill contrast between the near-black ground and the charcoal cards. The one exception is the view-toggle pill floating over the image, which uses a translucent dark fill (`rgba(15,17,23,0.72)`) plus backdrop-blur to read as an overlay control rather than a shadowed chip. The image pane's background layers a fine `repeating-linear-gradient` grid (~3.5% white, 32px cells) and a soft radial vignette under the card fill, so letterboxed margins read as a calibrated stage rather than dead space.

**The Flat Ground Rule.** Nothing on this screen casts a shadow. Separation is fill and border only; a shadow here would read as decoration borrowed from a different, softer product. (The theme layer explicitly zeroes Gradio's default drop-shadow token; nothing overrides it back on.) The image pane's grid/vignette background is a tonal fill layer, not an exception — it has no origin, no direction, and casts nothing.

### The Category Standard

Flat. Separation is a 1px rule, a panel on paper, or a stage on paper; there is no card elevation, no glass and no backdrop blur. The direction contract said "no drop shadows"; the build carries exactly three small, bounded exceptions, all functional:

#### Shadow Vocabulary
- **Frame contact** (`box-shadow: 0 0 0 1px #000, 0 18px 40px -24px rgba(0,0,0,0.9)`): the microscopy frame on its stage only; a black keyline plus a contact shadow that is near-invisible on the near-black stage.
- **Switch knob** (`box-shadow: 0 1px 2px rgba(0,0,0,0.25)`): the thumb of the tamper switch.
- **Scale-bar legibility** (`box-shadow: 0 0 0 1px rgba(0,0,0,0.55)` on the bar, `text-shadow: 0 1px 2px rgba(0,0,0,0.9)` on its label): keeps the white scale bar readable over bright tissue.

#### Named Rules
**The Stage Rule.** Dark is reserved for things you look *at*: microscopy frames and their layers, the timeline chart, the record JSON and the code sample. It is never used to make a UI panel look important, and prose on a stage is Caption-sized context for the image, not body copy.

## Shapes

### The Console World

Four corner radii cover the whole system: **8px** for interactive controls (Analyze button, control-cluster, audit JSON block); **10px** for content cards (status, confluency, results container); **12px** for the image frame, the one deliberately larger radius on the largest single element; and **999px** (full pill) for status-carrying elements (action badge, confidence pill, confluency bar and fill, evidence-breakdown tracks, view-toggle). The evidence-region-count dot is the one deliberate square-ish exception (2px radius) — a tick mark tying back to the red rectangles on the image, not a status pill. The vocabulary reads by role: pills carry status, 8px marks something you act on, 10px is a content container, 12px is the image stage itself.

### The Category Standard

Rectangles with small, role-graded radii and 1px hairlines. Radius steps down with the size of the thing: the stage (`site-stage`, 10px), figure panels, tables, the chain, JSON and code (`site-container`, 8px), buttons (`site-control`, 6px), nav links, tabs, the action badge and readout sub-rows (`site-small`, 4px), the microscopy frame and panel letters (`site-image`, 3px), strip thumbnails, bar tracks and visit buttons (`site-mark`, 2px). Pills (`site-pill`) are for layer chips and the switch only. The chain is one joined strip — outer corners rounded, inner edges shared — until 1080px, where its tiles separate.

**Marks are authored and closed.** Every icon comes from one set in `ui.jsx`: 16px grid, 1.6px round-capped stroke on `currentColor`, `aria-hidden`. Verdict icons are shapes that still read with the colour removed — a circled tick (pass), a boxed cross (fail), a triangle with a bar (mixed), a dashed circle (none/untested), a circled i (info) — and the anomaly flag is a diamond with a bar (flagged) or an empty diamond (not flagged). Chart marks follow the same logic: filled cyan circles for measurements, outlined indigo squares for quality-gate failures, magenta diamonds for anomaly flags.

## Components

### The Console World

#### Buttons
- **Shape:** 8px radius, squared-off (non-pill) — reserved for the single primary action.
- **Primary (Analyze):** Signal Blue fill, white text, 600 weight, `8px 20px` padding. Fixed geometry: `flex: 0 0 auto`, min-width 116px, min-height 40px. On click, label is replaced by a CSS spinner rather than disabled-gray — the button stays legible as "working," not "broken."
- **Hover:** background steps to `#2563eb`.

#### Control Cluster (signature)
- The cell-line dropdown and target-% field share one bordered, 8px-radius, charcoal container as a single visual unit. A 1px graphite divider separates the two fields internally; each field is borderless and transparent inside the cluster.
- **Cell-line field:** native `<select>` with `appearance: none` and an authored SVG chevron (stroke `#9ca3af`, 14px) positioned via `background-image`.
- **Target field:** number input with native spin buttons suppressed and an inline `%` suffix drawn via `::after`.

#### Status Card (signature)
- 10px radius, 1px border tinted 28% of the status color, background at 8% opacity over the charcoal card.
- **Structure:** status row (authored SVG icon + status label + monospace confidence pill) → 1px divider → four-row evidence breakdown (label, 4px pill track, right-aligned mono percentage) → second divider → evidence-region line (small near-square dot + "N evidence region(s) marked on image").
- **Evidence-breakdown color rule:** only the row matching the current QC flag carries the full status color and 600-weight label; the other three are muted (`#4b5563` bar, secondary label) regardless of their own probability. The card reads one verdict, with the others as context.
- **Region line:** dot fills status-red when `evidence_region_count > 0`; otherwise a hollow graphite outline reading "No evidence regions marked on this image."

#### Action Badge
Full pill; status color at 15% opacity background, full-opacity status color text, 600 weight, no border.

#### Confluency Card
52px monospace number as the card's entire first line, no label. Counts up client-side from `0.0` after a 460ms delay over 600ms ease-out-cubic. 7px pill track; fill scales via `transform: scaleX()` (never `width`) — green at/above target, Ash Fill below. A 2px vertical marker shows target position; the numeric target lives in the meta row.

#### Audit Record (signature)
Native `<details>`/`<summary>`, no card background — a quiet metadata row. Chevron rotates 90° on open via CSS. Expanded: full hash-chained JSON in mono-small on the darkest surface (`#12141a`), capped at 220px with its own scroll. Exists so raw audit data is never on-screen by default but never more than one click away.

#### Image Viewer (signature)
12px radius frame, `object-fit: contain`, the grid/vignette stage background. Two-option pill radio overlay toggle on a translucent scrim, selected state in Signal Blue, with the native radio visually hidden but present. Cell-mask overlay is a flat green fill at 32% blend. Evidence boxes are 2px red stroke, no fill, with a soft red glow, drawn only when the QC flag is not `normal`. Any non-browser-renderable upload (TIFF) is re-encoded to a PNG preview while the original stays the analysed and hashed file. Loading state is a pulsing translucent scrim — note that Gradio's own pending-state handling often clears the underlying image, so "previous frame visible under the scrim" is not a guarantee.

#### Wordmark Status Dot
8px filled circle, Signal Blue, no halo. Permanent `opacity` breathe (0.55↔1, 2.4s) signalling "instrument is live," not tied to analysis state.

### The Category Standard

#### Buttons
- **Primary:** Ink fill, white text, `site-button`, 38px tall (34px in the bar), 6px radius, a 15px icon after the word; hover to `#262d36`. It is the only button style shipped; there is one per page.
- **Focus:** the global ring, 2px `site-cell-ink` at 2px offset (`site-cell` on a stage). Never removed.

#### Navigation
Section links in `site-label`-sized Ink 2 text, 4px radius, hover fill `#e9ecf0`, current section `#e4e8ed` via `aria-current`. Scrolls horizontally with a hidden scrollbar; hidden below 760px.

#### Specimen Stage (signature)
The stage's toolbar starts with panel letter A and a mono "Layers" label, then four layer chips: pill, stage-rule border, a 10px swatch that shows the layer's own mark (filled cyan, cyan outline, hatched, filled magenta), full opacity when pressed. The frame holds the phase-contrast image at `contrast(1.06)` and its layers, each fading in over .35s. The rail's readings each open with a label and a mono source tag (Cellpose-SAM, DINOv2, the rules version), then the value: the confluency readout with its target, a confidence gauge (6px track, cyan fill scaled by `transform`, a 2px threshold tick, mono legend), the anomaly score gauge in magenta against its threshold, the action badge with its gloss and reason, and the record's re-hash line.

#### Action Badge
Transparent, a 1.5px `currentColor` border, 4px radius, 30px tall, icon + uppercase word. It takes the lifted hue on a stage and the print hue on paper.

#### Verdict
Icon shape + word at 13px/600 in the verdict's hue (pass → passage, fail → review, mixed → hold, none/info/untested → Ink 3), with an optional Ink 3 note beneath when the source wording differs from the word shown. Used in the detectability matrix and the V1–V10 table. The chain's verified / hash mismatch / link broken states and the rail's re-hash line use the same shape + word pairing.

#### Figure Panel
White panel, 1px rule, 8px radius. A head with a bordered mono panel letter and a title; the plot or image; a Caption legend that states what is measured, n and the source file as a breakable mono path. Bar rows are label / 14px track / right-aligned mono value.

#### Example Strip
Seven equal buttons joined by 1px stage-rule gaps: a 52×39 thumbnail, a short name, and a mono line of confluency and action word. The pressed example takes `site-stage-3` and a 2px cyan top bar.

#### Timeline
Flask tabs (4px radius, selected on `site-stage-3` with the pressed border, a Stage-ink-3 "simulated" tag); the map with numbered white field boxes and a scale bar; a 3-up readout grid of mono values; the chart (mono axis ticks, grid lines, noise band, dashed fit and forecast); a row of visit buttons (current in cyan, hatched indigo for a quality-gate failure, a magenta diamond above a flagged visit, arrow-key navigable); a key that pairs every mark with its words.

#### Record Chain
Seven joined tiles: mono index, a two-line name, mono digest, mono confluency and action, and a verification state. The pressed tile tints cyan (`#f0f7f8`, border `#9fd3da`); a failing tile tints review (`#fdf2f1`, border `#eab0aa`) and names the change in review red. Beside it, a pill switch (review red when on) that changes one number, the record JSON on a stage with the changed value highlighted, and a field glossary as a ruled mono-key list.

#### Changes
A two-column ruled table: "what v0.2 showed" on the recess fill with a review-tinted strike-through (unless kept), "v0.3" beside it with a mono source line.

#### Named Rules
**The Figure Label Rule.** Every figure carries a panel letter, the n it was measured on and its source file; every microscopy frame whose pixel size is known carries a true scale bar (the `ScaleBar` computes its width from `um_per_px`), and a frame whose pixel size is unknown (the EVICAN examples) carries none rather than a guessed one.

**The Data-Only Number Rule.** No number is typed into a component. Readings, thresholds, n, results and forecast values are read from `site/src/data.json`, generated by `site/assets/build_data.py` from the repo's results and records, and CI regenerates and diffs it.

**The Shape-and-Word Rule.** A verdict, flag or action is never carried by colour alone: every one has its own icon shape and its word, so the page still reads in greyscale.

**The Re-Checked Record Rule.** The record chain is recomputed in the visitor's browser on load, and the page says so in words ("Re-hashed in your browser: matches") beside the digest. The pending state says it is re-hashing; it never shows a placeholder verdict.

## Do's and Don'ts

### The Console World

#### Do:
- **Do** keep color meaning consistent system-wide: green/amber/red always mean the same three things (status card, action badge, evidence-breakdown predicted row, evidence boxes, confluency-bar fill).
- **Do** use `transform`/`opacity` for all CSS-animated motion — never animate `width`, `height`, or `padding`. The confluency count-up is the one sanctioned exception to "CSS-only": it mutates `textContent` because a numeric readout, not a shape, is what's ticking.
- **Do** keep the audit record one click away, never zero clicks (always visible) or more than one click (buried in a settings surface).
- **Do** author status icons, and any control affordance, as inline/authored SVG; never substitute emoji or a raw system glyph.
- **Do** disclose the classifier's training provenance in the permanent footer, plainly and always-visible — not as a dismissible banner or modal.
- **Do** re-encode any non-browser-renderable upload format (TIFF and similar) to a browser-safe preview before display; the original file remains what's analyzed and hashed.
- **Do** use the shorter row-label form for a QC class inside a fixed-width breakdown column, while keeping the full verdict phrase on the status-card headline (see The Headline-vs-Row Copy Rule).

#### Don't:
- **Don't** introduce a fourth status color or reuse Signal Blue for a QC status — blue is reserved for "interactive," never "verdict."
- **Don't** add card-style borders/backgrounds to the rationale text or the audit-record summary row; both are intentionally chrome-free relative to the three result cards.
- **Don't** add drop shadows anywhere; depth in this system is fill, border, and (in the image pane only) a neutral tonal texture layer — never a cast shadow.
- **Don't** let the page itself scroll; if new content is needed, it goes in the results-pane's own internal scroll region or it doesn't ship.
- **Don't** label result data with form-style captions ("Status:", "Confidence:") — the existing type scale and color already carry that meaning.
- **Don't** let a primary action stretch to fill its row — the Analyze button's fixed min-width/min-height is deliberate.
- **Don't** treat the image-loading scrim's "previous frame visible underneath" as a guarantee when building on this pattern elsewhere.
- **Don't** assume a non-`normal` QC flag and its action badge always share a status color (see The Two-Axis Status Rule).

### The Category Standard

#### Do:
- **Do** use cyan only for what the segmentation model computed (and the current selection or focus), and magenta only for what the anomaly check computed (The Who-Computed-It Rule).
- **Do** show every action as hue + its own icon + its word, with a gloss of what it means for the flask (The Action Hue Rule).
- **Do** give every verdict and flag an icon shape and a word (The Shape-and-Word Rule).
- **Do** put microscopy, charts over image-derived data, JSON and code on a stage; put prose on paper (The Stage Rule).
- **Do** set every measured number, hash, path and field name in Geist Mono with tabular figures (The Two Cuts Rule).
- **Do** give every figure a panel letter, its n and its source file, and a true scale bar when the pixel size is known (The Figure Label Rule).
- **Do** read every number from `data.json` (The Data-Only Number Rule).
- **Do** size a frame from the image's own aspect ratio and draw overlays in its pixel space (The Measured Frame Rule).
- **Do** link a reading to the layer it was measured on by hover and focus (The Lit Reading Rule).
- **Do** keep a horizontally scrolling table a focusable region with an `aria-label`.

#### Don't:
- **Don't** use an action hue for decoration, emphasis or branding, or show one without its icon and word.
- **Don't** use cyan or magenta for anything their model did not compute.
- **Don't** add a drop shadow, glass or backdrop blur; the only shadows are the frame contact, the switch knob and the scale-bar keyline.
- **Don't** draw a scale bar for a frame with no known pixel size.
- **Don't** type a number into a component.
- **Don't** put an eyebrow or kicker above a headline; the section head is headline left, lede right.
- **Don't** use an icon font, a glyph character or an emoji as an icon; draw it in the shared `ui.jsx` set.
- **Don't** set prose in mono or measurements in the sans.

---

## Cross-surface notes

Two product defects found while building the earlier landing page. They belong to the pipeline and the console, not to either design system, and neither is a visual-design decision:

1. `demo/analysis.py::_scale_bboxes` over-scales Grad-CAM boxes for non-256px images (written up in the root `README.md`). The box comes from a centred 256×256 crop, so only the origin should be offset, not the box scaled.
2. `culture/rationale.py::_bbox_quadrant` emits a spurious quadrant for a full-frame evidence box, because it reads the box's centre.

The v0.3 site draws no Grad-CAM boxes (it shows DINOv2 anomaly patches over the anomaly check's own centre tile), so neither defect reaches it. The fix belongs in `culture/` and `demo/`.
