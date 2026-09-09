---
name: cultureQC
description: Two surfaces, two worlds — a dark exception-review console and a landing page built as the culture line's own travel document
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
  # ── The Travel Document (site/src/App.jsx) ──
  # the booklet cover
  doc-cover-900: "#3F1019"
  doc-cover-800: "#571825"
  doc-cover-700: "#6B1F2D"
  doc-cover-600: "#83323F"
  # security paper
  doc-paper: "#F3EEE2"
  doc-paper-2: "#EDE6D6"
  doc-paper-3: "#E4DBC7"
  doc-paper-4: "#D6CBB2"
  doc-rose: "#F3DCE0"
  doc-leaf-green: "#DFE9D8"
  # ink
  doc-ink: "#1E1912"
  doc-ink-2: "#554B3E"
  doc-ink-3: "#6E6456"
  # document chrome
  doc-gold: "#C7A24D"
  doc-gold-2: "#A5842F"
  doc-gold-3: "#6A5426"
  doc-gold-lift: "#D9BC7A"
  # stamp inks — chrome only, never a verdict
  doc-stamp-navy: "#1E2A56"
  doc-stamp-purple: "#5C3F91"
  doc-stamp-green: "#3F6B45"
  # the verdict trio — the product reading an image, and nothing else
  doc-v-green: "#2E6B3E"
  doc-v-amber: "#8A5406"
  doc-v-red: "#B4231A"
  # the same trio lifted for the ink ground of a plate
  doc-v-green-lifted: "#6FBF80"
  doc-v-red-lifted: "#F0705E"
  doc-evidence: "#E8503A"
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
  # ── The Travel Document ──
  doc-poster:
    fontFamily: "'Bodoni Moda', Didot, 'Bodoni 72', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(72px, 10vw, 150px)"
    fontWeight: 600
    lineHeight: 0.92
    letterSpacing: "-0.03em"
    fontFeature: "tabular-nums"
  doc-figure:
    fontFamily: "'Bodoni Moda', Didot, 'Bodoni 72', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(40px, 4vw, 58px)"
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: "-0.02em"
    fontFeature: "tabular-nums"
  doc-headline-major:
    fontFamily: "'Bodoni Moda', Didot, 'Bodoni 72', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(32px, 4.6vw, 64px)"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "-0.012em"
  doc-headline:
    fontFamily: "'Bodoni Moda', Didot, 'Bodoni 72', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(27px, 3.4vw, 46px)"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "-0.012em"
  doc-hook:
    fontFamily: "'Bodoni Moda', Didot, 'Bodoni 72', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(27px, 3.1vw, 45px)"
    fontWeight: 600
    lineHeight: 1.06
    letterSpacing: "-0.014em"
  doc-readout:
    fontFamily: "'Bodoni Moda', Didot, 'Bodoni 72', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(23px, 2.4vw, 33px)"
    fontWeight: 600
    lineHeight: 1.04
    letterSpacing: "-0.015em"
    fontFeature: "tabular-nums"
  doc-title:
    fontFamily: "'Bodoni Moda', Didot, 'Bodoni 72', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(19px, 1.9vw, 26px)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.012em"
  doc-verdict-name:
    fontFamily: "'Bodoni Moda', Didot, 'Bodoni 72', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(17px, 1.6vw, 21px)"
    fontWeight: 700
    lineHeight: 1.12
    letterSpacing: "-0.008em"
  doc-lede:
    fontFamily: "Archivo, 'Archivo Expanded', system-ui, sans-serif"
    fontSize: "clamp(15.5px, 1.35vw, 18px)"
    fontWeight: 400
    lineHeight: 1.62
    fontVariation: "'wdth' 100"
  doc-body:
    fontFamily: "Archivo, 'Archivo Expanded', system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.62
    fontVariation: "'wdth' 100"
  doc-note:
    fontFamily: "Archivo, 'Archivo Expanded', system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.5
  doc-action:
    fontFamily: "Archivo, 'Archivo Expanded', system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 700
    letterSpacing: "0.09em"
    fontVariation: "'wdth' 86"
  doc-stamp:
    fontFamily: "Archivo, 'Archivo Expanded', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "0.11em"
    fontVariation: "'wdth' 80"
  doc-machine-label:
    fontFamily: "'B612 Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 400
    letterSpacing: "0.13em"
  doc-machine-data:
    fontFamily: "'B612 Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.55
    letterSpacing: "0.06em"
rounded:
  console-sm: "8px"
  console-md: "10px"
  console-lg: "12px"
  console-pill: "999px"
  doc-page: "3px"
spacing:
  console-sm: "10px"
  console-md: "16px"
  console-lg: "20px"
  doc-cover-w: "178px"
  doc-pad: "clamp(18px, 3.2vw, 52px)"
  doc-sec-top: "clamp(48px, 5.6vw, 92px)"
  doc-sec-bottom: "clamp(44px, 5vw, 80px)"
  doc-head-gap: "clamp(24px, 3.2vw, 42px)"
  doc-gutter: "clamp(16px, 3vw, 44px)"
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
  doc-cta:
    backgroundColor: "{colors.doc-cover-700}"
    textColor: "{colors.doc-paper}"
    typography: "{typography.doc-action}"
    rounded: "{rounded.doc-page}"
    padding: "12px 22px"
  doc-cta-disabled:
    backgroundColor: "transparent"
    textColor: "{colors.doc-ink-3}"
  doc-cta2:
    backgroundColor: "transparent"
    textColor: "{colors.doc-stamp-navy}"
    typography: "{typography.doc-machine-label}"
    rounded: "{rounded.doc-page}"
    padding: "12px 18px"
  doc-cta2-hover:
    backgroundColor: "{colors.doc-stamp-navy}"
    textColor: "{colors.doc-paper}"
  doc-toggle:
    backgroundColor: "transparent"
    textColor: "{colors.doc-ink-3}"
    typography: "{typography.doc-machine-label}"
    padding: "7px 12px"
  doc-toggle-checked:
    backgroundColor: "{colors.doc-gold}"
    textColor: "{colors.doc-ink}"
  doc-step:
    backgroundColor: "transparent"
    textColor: "{colors.doc-ink-3}"
    typography: "{typography.doc-machine-label}"
    padding: "8px 4px 9px"
  doc-step-current:
    backgroundColor: "{colors.doc-stamp-navy}"
    textColor: "{colors.doc-paper}"
  doc-tab:
    backgroundColor: "transparent"
    textColor: "{colors.doc-gold-lift}"
    typography: "{typography.doc-machine-label}"
    padding: "11px 10px 11px 16px"
  doc-tab-selected:
    backgroundColor: "{colors.doc-cover-800}"
    textColor: "{colors.doc-paper}"
  doc-cachet:
    backgroundColor: "{colors.doc-paper} @ 84%"
    textColor: "{colors.doc-v-red}"
    typography: "{typography.doc-stamp}"
    padding: "9px 16px 8px"
  doc-badge:
    backgroundColor: "currentColor @ 9%"
    textColor: "{colors.doc-v-amber}"
    typography: "{typography.doc-stamp}"
    padding: "9px 17px"
  doc-field-value:
    backgroundColor: "{colors.doc-gold}"
    textColor: "{colors.doc-ink}"
    typography: "{typography.doc-machine-data}"
    padding: "2px 7px"
  doc-endpoint-input:
    backgroundColor: "{colors.doc-paper}"
    textColor: "{colors.doc-ink-2}"
    typography: "{typography.doc-machine-label}"
    padding: "8px 10px"
  doc-mini-button:
    backgroundColor: "transparent"
    textColor: "{colors.doc-stamp-navy}"
    typography: "{typography.doc-machine-label}"
    padding: "8px 12px"
---

# Design System: cultureQC

## Overview

**This file records two visual worlds. They do not blend. Find your surface in the routing table before you read anything else.**

| If you are editing… | The governing world | Its brief | Token prefix |
| --- | --- | --- | --- |
| `demo/app.py` (the exception-review console) | **The Instrument Console** | `.impeccable/surfaces/demo-app-py.md` | `console-*` |
| `site/src/App.jsx` (the React landing page; also `site/src/styles.css`, `site/index.html`) | **The Travel Document** | `site/.impeccable/surfaces/site-src-app-jsx.md` | `doc-*` |

Every token in the frontmatter is namespaced by surface. Every canonical section below is split into `### The Console World` and `### The Travel Document`. A value, a rule or a component from one world is not evidence for the other; there is no shared palette, no shared type stack, and no shared shape vocabulary. The only thing they share is the product's three-way verdict semantics — green/amber/red — and even that is *quoted* by the landing page in its own inks rather than copied from the console (see **The Colour Quarantine Rule**).

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

### The Travel Document (`site/src/App.jsx`)

**Creative North Star: "The Travel Document"**

The landing page is issued, not designed: it is the culture line's own travel document. A burgundy buckram cover runs down the left edge, gold-blocked, carrying the wordmark, the two hash-routed gatherings, an authored gold seal and the section index for whichever gathering is open. Everything to its right is printed on security paper, and every analysis lands on that paper as a struck stamp that takes real page space. The record is not described; it is set as a machine-readable zone, two fixed 44-character lines built from the record's own fields.

The stock is the world's foundation and is never "plain paper": a guilloché rosette lattice tiled at 104px in visa rose over a pale-green intaglio wash, with paper fibre suspended in the sheet — a single fixed layer composited `multiply` at 26% so the whole booklet is one continuous sheet rather than a texture repeated per section. The cover carries its own separate tooth (a fractal-noise buckram grain at `overlay`, 16%). Type is three registers for three jobs, and the registers do not trade places: an engraved didone for headings, figures and the wordmark; a machine mono for the MRZ, hashes, field labels and measured data; a variable grotesque for prose, controls and stamp lettering.

The one dark region on a light page is earned: grayscale phase-contrast microscopy loses its contrast on cream, so the specimen is a tipped-in plate laid on ink inside a gold hairline, and the analysis instrument rules leader lines from each printed reading back to the pixels it was measured on. Colour is quarantined — document chrome and verdict are two systems that share one ground and never substitute for each other — and no verdict is ever carried by colour alone: the cachet, badge and dot key their *shape* on the verdict, and every state also carries its word.

**Key Characteristics:**
- The ground is security paper — guilloché, intaglio wash and fibre — never a flat fill, and never re-applied per section.
- A verdict is shape + word + ink. Kill the colour and the page still reads.
- Stamp inks number and letter the document; the verdict trio is the product reading an image and appears nowhere else.
- Nearly no radius: one 3px page-corner token, plus the round and oval geometries that *are* verdict meaning.
- Motion is a stamp landing: it stops dead, with no overshoot anywhere in the world.

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

### The Travel Document

Four families on one paper ground, with four separate jobs. They do not substitute for one another, and two of them are formally quarantined from each other.

#### Primary
- **Buckram Burgundy** (`#6B1F2D`, with `#3F1019` / `#571825` / `#83323F` as its cover ramp): the volume's own colour. It is the cover, the skip link, the primary action's fill, the italic clause inside every hook and closing headline, the winning bar on the measured comparison, and the drop state of the ingest mat. It is the page's identity, not a status.
- **Pressed Gold** (`#C7A24D`, damped to `#A5842F` and `#6A5426`, lifted to `#D9BC7A` on the cover): document chrome and the current-state marker. It blocks the cover rule and the seal, fills the checked toggle and the schedule's field values, rules the plate's inner hairline and the leader lines, draws the scan sweep, and carries document addresses, captions and table captions in its damped steps. Gold marks *what this document is* and *where you are in it*.

#### Secondary — stamp inks
- **Stamp Navy** (`#1E2A56`): the interactive stamp ink. It is the secondary control's rule and label, the current leaf in the stepper, the caret, and the global focus ring. If it is navy, it is a control.
- **Stamp Purple** (`#5C3F91`): the clerk's numbering ink — the serial struck beside each chain record and each manifest row, and nothing else.
- **Stamp Green** (`#3F6B45`): the reachable-module mark on the connection panel. A socket answering is document chrome, not a reading of an image.

#### Tertiary — the verdict trio
- **Verdict Green / Amber / Red** (`#2E6B3E` / `#8A5406` / `#B4231A`): the product reading an image, in print-ink values weighted for the paper ground. They appear on the cachet, the verdict dot and name, the action badge, the probability row that was actually predicted, the flagged manifest and chain rows, the severity-matrix cell border, and the chain's broken state. Nowhere else.
- **Lifted trio** (`#6FBF80` green, `#F0705E` red, `#E8503A` evidence stroke): the same three meanings rendered on the ink ground of a plate or a matrix cell, where the print-ink values would disappear. A lifted value is the trio on ink; it is not a fourth colour and it never appears on paper.

#### Neutral
- **Security Paper** (`#F3EEE2` stock, `#EDE6D6` recessed fill and hover, `#E4DBC7` fine row rules and tracks, `#D6CBB2` structural hairlines and enclosure borders): the four-step stock ramp. Every border in the system is one of the last two.
- **Visa Rose** (`#F3DCE0`) and **Intaglio Green** (`#DFE9D8`): the under-printing. They never carry type; they tint the guilloché ground, the visa panel's own stock, the ingest mat and the one tipped-in inverted leaf.
- **Ink** (`#1E1912`): primary type, structural rules under section heads and tables, and the ground of every plate, thumbnail and code block.
- **Ink 2** (`#554B3E`): all secondary prose — ledes, rationale, table body, list copy.
- **Ink 3** (`#6E6456`): field labels, captions, footnotes, meta and inactive marks. **The hex is measured, not chosen:** it reaches 5.0:1 on the paper ground; its predecessor `#7A7062` measured 4.20:1 and failed. Do not lighten this token to taste.

#### Named Rules
**The Colour Quarantine Rule.** Two colour systems share one paper ground and are not interchangeable, and this is the stylesheet's own governing rule, stated in its header. **Stamp inks — navy, purple, green, gold — are document chrome.** They mark pages, number leaves and letter the cachets; a stamp ink never states a verdict. **The verdict trio — `doc-v-green` / `doc-v-amber` / `doc-v-red` — is the product reading an image, and appears nowhere else.** This is enforced in the file and was a real defect once: API reachability originally used the verdict green and had to be moved to the stamp green, because a reachable socket is not a reading of a specimen. The only sanctioned variation is rendering, not meaning: on an ink ground the trio switches to its lifted values so the same three meanings stay legible on a dark plate.

**The Shape-and-Word Rule.** A verdict is never carried by colour alone. Every verdict-bearing element keys its *shape* on `[data-v]` — an oval clears (`normal`), a ruled rectangle refers (`amber`), a heavy barred box refuses (`red`, 3px), a dashed outline is idle — and every state also carries its word, spelled out. Kill the colour and the page still reads. The selector form is load-bearing and is the trap in this system: the action badge carries **its own** `data-v`, because the recommended action and the QC flag are two axes that do not always agree, so its rules are compound (`.badge[data-v="red"]`) and must never become descendant rules. The verdict dot is the opposite — it is a child of `.verdict[data-v]` and inherits. Getting this backwards silently disables the shape channel and leaves colour alone carrying the verdict.

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

### The Travel Document

**Engraved (display) Font:** `Bodoni Moda` (variable, weight 400–900, self-hosted WOFF2), falling back to Didot, Bodoni 72, Georgia
**Machine Font:** `B612 Mono` (self-hosted at 400 and 700), falling back to `ui-monospace`
**Prose / Control Font:** `Archivo` (variable, weight 400–900, width 62%–125%, self-hosted), falling back to `system-ui`

**Character:** Three registers for three jobs. The didone is the engraver's hand — high-contrast, authoritative, reserved for headings, the wordmark and every figure a human reads as a *value*. The mono is the machine's hand — the MRZ, digests, field labels, column heads, states, and any datum a machine wrote. The grotesque is the human hand — prose, instructions, controls, and the heavy condensed lettering inside a struck stamp. The registers never swap: a heading in mono, or a hash in the didone, dissolves the whole conceit.

#### Hierarchy
- **Poster** (didone 600, `clamp(72px, 10vw, 150px)`, line-height 0.92, tabular): the two head-to-head figures, each with a `.28em` unit suffix.
- **Figure** (didone 600, `clamp(40px, 4vw, 58px)`, line-height 0.98, tabular): the confluency reading in the witness column, with its `%` as a `.32em` superscript in Ink 3.
- **Headline** (didone 600, `clamp(27px, 3.4vw, 46px)`, line-height 1.02, `max-width: 22ch`, `text-wrap: balance`): every section head. The major variant steps to `clamp(32px, 4.6vw, 64px)` at 20ch; the closing hook to `clamp(29px, 4.4vw, 62px)` at 17ch.
- **Hook** (didone 600, `clamp(27px, 3.1vw, 45px)`, line-height 1.06, `max-width: 19ch`): the single `h1` in the first viewport, its second clause set italic in Buckram Burgundy.
- **Readout** (didone 600, `clamp(23px, 2.4vw, 33px)`, tabular): the three engraved data fields under the hook.
- **Title** (didone 600, `clamp(19px, 1.9vw, 26px)`): the four bound-output rows and the batch head. The verdict name sits in the same register at 700.
- **Lede** (Archivo 400, `clamp(15.5px, 1.35vw, 18px)`, line-height 1.62, `max-width: 66ch`): the paragraph under each section headline. The hero's subhook is the same register one notch tighter at `clamp(14.5px, 1.1vw, 16.5px)`, 46ch.
- **Body** (Archivo 400, 16px, `wdth` 100, line-height 1.62): running prose, table cells, list copy. Notes and footnotes drop to 13.5px in Ink 3 at 62ch and 74ch respectively.
- **Action** (Archivo 700, 13.5px, `wdth` 86, `letter-spacing: .09em`, uppercase): the primary control's label.
- **Stamp** (Archivo 800, `clamp(13px, 1.25vw, 17px)`–14px, `wdth` 78–80, `letter-spacing: .09–.11em`, uppercase): the word inside a cachet or an action badge. The one place the grotesque is set heavy and condensed, because a rubber stamp is cut, not typeset.
- **Machine label** (B612 Mono, `--micro` = 11px, `letter-spacing` .04–.19em, uppercase): every field label, document address, column head, toggle, tab, stepper label, state word and caption. One size, one token, dozens of usages — the token *is* the label role.
- **Machine data** (B612 Mono, 11–12.5px, `word-break: break-all` on digests): the MRZ, every hash, endpoint strings, code blocks and the seal.

#### Named Rules
**The Three Hands Rule.** Engraved for what a person reads as a value, machine for what a machine wrote, grotesque for what a person reads as a sentence. A heading is never mono; a digest is never didone; an instruction is never uppercase mono — sentence-cased prose in the grotesque, because uppercase destroys word shape and a long mono line is a machine's line, not a person's. The ingest mat is the canonical demonstration: its headline is engraved, its format list is machine, and the sentence around them is Archivo.

**The Micro Floor Rule.** Functional text sits at or above `--micro` (11px), and the label role cites the token rather than typing a size. Colour, weight and letterspacing differentiate labels; half-pixel size steps do not — a 9.5px and a 10.5px label are not a hierarchy, they are two illegible sizes. A relative-unit mark riding a figure (the `%` set at `.32em` on the confluency readout, the `.28em` unit on a poster figure) is a typographic superscript, not a label, and is out of scope.

**The Document Address Rule.** Every section head pairs an engraved headline with a machine-set document address in damped gold, sitting **after** the headline in DOM order and baseline-aligned to its right, stacking **below** it under 760px. It is never an eyebrow and never a kicker: it does not sit above the headline at any width, and it is a coordinate in the volume rather than a category label for the section.

## Layout

### The Console World

Full-viewport split pane, no page scroll: a topbar (fixed height), a main row (grid, fills remaining height), and a one-line footer. The main row (`.main-row`) is a CSS grid — `grid-template-columns: 62fr 38fr`, `grid-template-rows: minmax(0, 1fr)`, 20px gap — not a flex row: the 62/38 image/results split is a fixed track ratio, so the image pane's size holds steady regardless of the audit record's expand/collapse state underneath it. The results pane is the only element permitted its own internal scroll; that scroll is load-bearing, not a rare-case safety net — it's how the audit record can expand to full height without ever resizing the image pane or the page.

Card rhythm in the results stack: 12px gap between cards, 16px internal card padding. Cards stagger into view 100ms apart on analysis complete (status+evidence → confluency → action → rationale → audit) — five stagger steps, not six. The evidence breakdown is internal structure of the status card, not a sixth card; it was built as a standalone sixth card first and folded into the status card specifically because a sixth card overflowed the fixed 1280×800 no-scroll budget and clipped the action badge.

Topbar controls are compact and un-labeled, right-aligned, sitting inline with the wordmark rather than in a form column. The cell-line dropdown and target-% field are grouped into a single bordered **control-cluster** unit with a 1px divider between them; the Analyze button sits outside the cluster as the one squared-off, fixed-size (min 116×40px) action that never stretches to fill the row. Three inputs (cell line, target %, Analyze) is the ceiling.

### The Travel Document

**The cover.** A fixed 178px burgundy column down the left edge at `z-index: 40`, with a 2px damped-gold right border and a gold hairline inset by `box-shadow`. `body` compensates with `padding-left: 178px`. It holds four things in vertical order: the wordmark over a gold rule, the two gathering tabs, the seal and its schema/leaf-count meta centred in the remaining space, and the section index blocked into the foot. Below 1080px the whole cover becomes a **sticky top bar**: the column turns into a row, the border moves to the bottom, the seal shrinks to 28px beside the meta, the tabs run horizontally with their register mark moving from a left tick to a 3px underline, and the section index is dropped. Below 700px the seal is dropped and the tabs take their own full-width row.

**The first viewport.** A two-column grid, `minmax(0, .82fr) minmax(0, 1.3fr)`, giving the plate the larger share, at `min-height: calc(100svh - 40px)` — a floor, not a fixed height, so the leaf fills the fold and grows when the copy needs the room. Left: hook, subhook, the three engraved readouts, and the visa panel carrying the MRZ and the page's primary action full-bleed inside its own tinted stock. Right: the plate with the cachet struck over its top-right corner. Below 1000px it collapses to one column with the plate ordered first, and the cachet leaves the image to land under the caption at a shallower angle.

**The analysis instrument.** `grid-template-columns: minmax(0, 1.42fr) minmax(320px, .82fr)` inside one hairline enclosure: plate and stepper left, witness column right, the readings stacking vertically beside the specimen so leader lines can rule each one back to its pixels. Below 1080px it goes single-column and the witness column's left rule becomes a top rule.

**Section blocks.** Every section is a leaf: `clamp(48px, 5.6vw, 92px)` top, `clamp(44px, 5vw, 80px)` bottom, `clamp(18px, 3.2vw, 52px)` sides, separated by a paper-4 hairline. The head is an ink-ruled baseline with `clamp(24px, 3.2vw, 42px)` of air beneath it. **There are no cards.** There are ruled **enclosures** — the leaf grid, the toggle strip, the stepper, the connection panel, the visa panel and the ingest mat each sit inside one 1px rule, sometimes over one paper step or their own tint. An enclosure is a boundary drawn on the stock; a card is an object above it.

**Two rule weights and their inks.** A 1px paper-3 rule separates rows inside a block; a 1px paper-4 rule separates blocks and bounds enclosures; a 1px **ink** rule marks a structural head — the section-head baseline, the table head, the readout's top rule, the schedule's top, the chain's top. Weight and ink together, never a shadow, never a filled panel.

**Measure.** Ledes cap at 66ch, the subhook at 46ch, footnotes at 74ch, notes at 62ch, output-row prose at 52ch, the hook at 19ch, section headlines at 22ch (20ch major, 17ch closing).

**Breakpoints** (max-width): **1080** — cover becomes a sticky bar, leaf grid and witness column stack; **1000** — the hero collapses to one column with the plate first and the cachet moves under the caption; **900** — upload grid and integration split stack, sideways-scroll notes appear; **820** — output rows go to one column and field values left-align; **760** — section heads stack and the document address drops below the headline; **720** — provenance rows wrap their key above the claim; **700** — chain records drop to two columns with the state on its own row, and the cover's seal is dropped; **640** — head-to-head stacks, the stepper wraps to three rows of three, the toggle strip becomes a ruled column with its state words right-aligned; **560** — the readouts and the teaser strip stack.

#### Named Rules
**The Leader Line Rule.** In the analysis instrument, each printed reading is ruled back to the pixels it was measured on with a dashed damped-gold line and a small terminal dot, measured off the live layout rather than hand-placed, drawn in an absolutely positioned overlay that is never interactive. It is suppressed below 1080px, where the witness column no longer sits beside the plate and a leader would cross empty space. A reading that cannot be pointed at is a claim; a reading with a leader is a measurement.

**The Measured Plate Rule.** The specimen frame carries `aspect-ratio: var(--nw)/var(--nh)` from the image's own intrinsic dimensions, set on the element by the component, so a scientific image is never distorted and never letterboxed into a guessed box. Never replace this with a fixed height or a hardcoded ratio.

**The Real Region Rule.** Anything that scrolls sideways is a real, focusable region — `overflow-x: auto`, `tabindex="0"`, `role="region"`, an `aria-label`, its own focus ring, and a visible machine-set note that appears under 900px. Its caption sits outside the scroll box so it never scrolls away from the thing it names. `body` carries no `overflow-x: hidden`; the mask would hide the next real overflow.

## Elevation & Depth

### The Console World

Flat by design. No drop shadows anywhere — depth is conveyed entirely through the 1px graphite border and background-fill contrast between the near-black ground and the charcoal cards. The one exception is the view-toggle pill floating over the image, which uses a translucent dark fill (`rgba(15,17,23,0.72)`) plus backdrop-blur to read as an overlay control rather than a shadowed chip. The image pane's background layers a fine `repeating-linear-gradient` grid (~3.5% white, 32px cells) and a soft radial vignette under the card fill, so letterboxed margins read as a calibrated stage rather than dead space.

**The Flat Ground Rule.** Nothing on this screen casts a shadow. Separation is fill and border only; a shadow here would read as decoration borrowed from a different, softer product. (The theme layer explicitly zeroes Gradio's default drop-shadow token; nothing overrides it back on.) The image pane's grid/vignette background is a tonal fill layer, not an exception — it has no origin, no direction, and casts nothing.

### The Travel Document

Depth is printing, not stacking. Nothing floats above the page: separation is a rule, a stock step, a tint, or an ink ground. The three material devices are the security stock itself, ink absorbing into that stock, and the single contact shadow under the one physically tipped-in object.

**Ink absorption is a filter, not a bevel.** A single SVG filter (`#ink-bite`, `feTurbulence` + `feDisplacementMap`, defined once in `App.jsx` inside an unpainted host) displaces the perimeter of every struck mark, so a cachet's edge breaks against the paper the way a rubber stamp does. The action badge additionally multiplies into the stock (`mix-blend-mode: multiply`), so it is struck onto the paper rather than laid over it. Never simulate this with a bevel, an inner highlight or a texture image on top of the mark.

#### Shadow Vocabulary
- **Plate contact** (`box-shadow: 0 1px 0 0 var(--doc-paper-4), 0 10px 26px -18px rgba(30,25,18,.6)`): the tipped-in specimen plate only. A hairline of stock beneath the mount plus a wide, heavily inset diffusion — a mounted photograph sitting on a page, not a floating panel. Bounded to `.mat`; nothing else in the world may take it.
- **Struck-mark inset** (`box-shadow: inset 0 0 0 1px color-mix(in srgb, currentColor 32–34%, transparent)`): the second ruled line inside a cachet or badge. An inset rule, not an elevation.
- **Scan emission** (`box-shadow: 0 0 18px 3px rgba(199,162,77,.75)`): the gold scan line during a run, and nothing else.
- **Evidence halo** (`box-shadow: 0 0 0 1px rgba(12,10,7,.9), 0 0 20px 3px rgba(232,80,58,.4)`): behind an evidence-box stroke on an ink ground only, reduced to 12px/1.5px on the severity-matrix tiles.

#### Named Rules
**The Security Stock Rule.** The ground is printed security paper and is composed once, for the whole booklet: a guilloché rosette lattice tiled at 104px in visa rose, plus a suspended paper-fibre `feTurbulence`, on one `position: fixed` layer at `opacity: .26` with `mix-blend-mode: multiply` and `pointer-events: none`; over it a diagonal intaglio wash of pale green and rose at 50%, also multiplied. The cover carries its own separate tooth — a fractal-noise buckram grain at `overlay`, 16%. Never flatten this to a plain fill, never re-apply grain per section, never let it take a pointer event, and never raise its opacity to "make the texture visible" — under-printing is meant to be felt, not read. It is dropped in print.

**The Plate-on-Ink Rule.** Grayscale phase-contrast microscopy loses its contrast on cream stock, so the specimen is mounted: an ink mat with a damped-gold hairline inset 5px, holding a frame outlined in gold over a near-black backing. This is the reason the one dark region on a light page exists, and it is reserved for real specimen imagery — plates, severity-matrix cells, manifest thumbnails and the code block. An ink ground is never used to make a UI panel feel important.

**The Two Emitters Rule.** Only a mark that is meant to emit light may carry a glow, and only two do: the scan sweep and the evidence box, both on the ink ground of a plate. Everywhere else, if something needs to separate it gets a rule, a stock step or a gutter. No offset shadow under a panel, no `backdrop-filter`, no glass.

## Shapes

### The Console World

Four corner radii cover the whole system: **8px** for interactive controls (Analyze button, control-cluster, audit JSON block); **10px** for content cards (status, confluency, results container); **12px** for the image frame, the one deliberately larger radius on the largest single element; and **999px** (full pill) for status-carrying elements (action badge, confidence pill, confluency bar and fill, evidence-breakdown tracks, view-toggle). The evidence-region-count dot is the one deliberate square-ish exception (2px radius) — a tick mark tying back to the red rectangles on the image, not a status pill. The vocabulary reads by role: pills carry status, 8px marks something you act on, 10px is a content container, 12px is the image stage itself.

### The Travel Document

Form is ruled and orthogonal: rectangles bounded by a 1px rule, a stock step or a gutter. Enclosures group controls by sharing one outer border with internal 1px dividers rather than by spacing separate chips.

**The Page-Corner Rule.** There is exactly one radius token — `--r-page: 3px`, the corner of a booklet page — and it belongs to leaf-like objects: the primary and secondary controls, the visa panel, the ingest mat, the connection panel and the code block. Small utility inputs take a 2px near-square. Radius is not a style dial: a new surface does not get 8px because it looks softer.

**Round is meaning, not decoration.** The exceptions to the orthogonal grammar are all verdict geometry, and they are load-bearing under The Shape-and-Word Rule: the cleared cachet is an oval (`border-radius: 46%/50%`), the cleared badge and manifest chip likewise (44%/50%, 40%/50%), the cleared verdict dot is a circle (50%), the referred states take a 1–2px near-square with an inset rule, and the refused states are hard-cornered with a 3px border. The connection dot is also round when a module answers — a filled stamp-green disc against its hollow, square-cornered idle state. Curvature here says something; it is never applied to make a control friendlier.

**Marks are geometric and closed.** A 13px verdict dot, an 8px toggle dot, a 9px connection dot, a 3px flag tick under each stepper leaf, 4–15px bar tracks, 1px and 2px rules, and a single authored gold seal. Any icon on this surface is authored inline SVG on `currentColor`, marked `aria-hidden` — never an icon font, a glyph character, an emoji or a third-party icon package.

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

### The Travel Document

#### Buttons
- **Primary (`.cta`):** burgundy fill, paper text, a `--cover-900` border with a gold hairline inset by `box-shadow`, `12px 22px`, Archivo 700 at `wdth` 86, uppercase, 3px page corner, with a 15px authored SVG. Hover brightens to `--cover-600` and lifts 2px on the snap curve; active returns to 0. **Disabled is inert, not dimmed:** it drops to transparent with an Ink 3 label, a paper-4 rule and no gold — an unavailable control reads as a blank field on the form, not as a live control someone greyed out.
- **Secondary (`.cta2`):** transparent on a 1px stamp-navy rule with a navy machine-set label at 11px/.11em, `12px 18px`. Hover floods navy with paper lettering. Its **pending** variant — an address the document has not been issued yet — turns the rule dashed and the label Ink 3, and does not respond to hover: a visible blank is honest, a removed row is not.
- **Focus:** the global ring, `2px solid` stamp navy at `3px` offset, on every control. Where the real input is zero-sized (toggles, ingest mat) a `:has(input:focus-visible)` rule puts the ring on the visible chrome. Never remove it, never replace it with a colour change.

#### The Cover (signature)
Burgundy buckram with its own fractal-noise tooth, gold-blocked: an engraved wordmark with its second half in gold, over a damped-gold rule. The two gathering tabs are machine-set 11px uppercase in lifted gold, each marked when open by a short gold tick struck in from the left edge plus a darker burgundy fill and paper-white lettering — the fill and the ink carry the state, the tick is the register mark beside it. Below the tabs the seal sits in the cover's own space with the schema and leaf count beneath it. The section index is blocked into the foot: one full-width entry per section, each with its own gold tick that grows to 55% on hover and full on the current entry, whose label goes paper-white at 700. No opacity is used on that lettering — 11px uppercase on burgundy has nothing to give away — and hovering the entry you are already on must not retract its own mark.

#### The Cachet (signature)
The officer's mark, struck over the top-right corner of the plate at `rotate(-7deg)`: a 2px `currentColor` border with an inset rule, a paper fill at 84%, machine-set data lines above and below a heavy condensed word, all displaced by `#ink-bite`. Its shape is its verdict — oval clears, ruled rectangle refers, heavy barred box refuses, dashed is idle. Below 1000px it comes off the image and is struck under the caption at `-3.5deg`, where a stamp on a small document actually lands.

#### The Visa Panel (signature)
The leaf a document gives you to act on, beside the plate: its own tinted stock (a rose-to-green gradient, separable from the ground), a paper-4 rule, a 3px page corner, and a paper inset highlight. Inside, a ruled field head of machine-set key/value pairs, then the machine-readable zone, then the page's actions stacked full-bleed and centred — on a grant page the actions are ruled fields the width of the leaf, not two buttons that happened to wrap.

#### The Machine-Readable Zone (signature)
Two fixed 44-character lines built from the record's own fields — document type and cell line, then the digest, schema version and analysis date — uppercase, `<` as filler, machine-set, ruled top and bottom in ink on a recessed paper fill, with a machine-set caption above. Nothing in it is decorative: it is a second rendering of the same data the page states in words. **The filler is a hazard:** `<` is a tag opener to an HTML parser. React escapes it; the OG renderer must escape it by hand, and failing to do so once swallowed the rest of the document. The line clips rather than wraps, because an MRZ is a fixed-width field.

#### Plate (signature)
A tipped-in specimen: an ink mat with a damped-gold hairline inset 5px, holding a frame with `aspect-ratio` from the image's intrinsic dimensions, outlined in gold over a near-black backing. Layers bottom to top: the specimen at `contrast(1.05)`, the cell mask at 34% revealed by a `clip-path: inset()` wipe over 760ms, the evidence-box layer, and the scan line. Beneath it the caption bar takes its own full-width line, flush left at every width — a plate caption that changes alignment with the viewport is three captions — with the layer toggles and the named layer state on the row above.

#### Evidence Box
2px lifted-red stroke, no fill, with the evidence halo behind it, striking on at a per-box stagger from `scale(1.06)`. Each box carries a lifted-red serial chip above its top-left corner which, on any field larger than the classifier's input, also names the analysed region (`E01 · analysed region, centre 256×256`). The chip wraps rather than clips: a clipped label is a label that lies about what was analysed.

#### Layer Toggles (signature)
Two label-wrapped checkboxes sharing one paper-4 enclosure over a recessed fill, with an internal divider; a `solo` variant closes the border on all four sides so a single toggle or a plain button can stand alone with the same chrome. Machine-set 11px uppercase with an 8px square dot that fills ink when checked, and the whole cell fills gold. Disabled drops to 45% opacity and keeps its words. Below 640px the strip becomes a ruled column with each state word right-aligned, because two layer names and their states cannot hold one 390px line.

#### Verdict Block
A 13px dot with a 2px `currentColor` border and a 22% fill, whose shape is set by the verdict; the verdict name engraved at 700; the confidence right-aligned in machine type. Below it, four probability rows (name / 74px track / value) where only the predicted row is `on` — it takes `currentColor` for its fill and turns its label and value ink; the other three stay paper-4 on paper-3. The action badge sits below, struck at `-1.6deg`, with its own `data-v`.

#### Leaf Stepper (signature)
One enclosure of equal-width buttons, one per record, each carrying a zero-padded leaf number, a truncating short name and a 3px flag tick — paper-4 for a clear leaf, verdict red at 60% for a flagged one. The current leaf inverts to a stamp-navy fill with paper text and a gold tick. Below 640px it wraps to three rows of three, so nine leaves never land as two rows and an orphan.

#### Witness Column (signature)
The right third of the analysis instrument: paper ground, a paper-4 left rule, an ink-ruled head pairing a damped-gold "Witness" label with the leaf counter, then ruled ledger rows (confluency, QC flag, action, rationale, record) whose last row drops its bottom rule. Each row is a machine-set field label over its value; rows snap in on a stagger with the snap curve. The confluency figure is engraved at fixed decimal places and lands with a single `struck` press — one compression, then stillness.

#### Ingest Mat (signature)
The dropzone is the visa panel's stock with nothing on it: a rose-and-green tint, a paper-4 rule at the page corner, and a dashed damped-gold rule inset 6px. Hover warms both rules to gold; drop state turns them burgundy, makes the inner rule solid and floods the field rose. It is a `<label for>` wrapping the real file input, so click and keyboard activation are native and the ring lands on the visible chrome. The headline inside is engraved; the instruction beneath is machine-set but sentence-cased — an instruction, not a label.

#### Connection Panel
The port of entry, beside the mat: one paper-4 enclosure on a recessed fill at the page corner. A 9px connection dot and a machine-set state name — a reachable module fills the dot **stamp green** and turns the label stamp green at 700, an unreachable one is a hollow Ink 3 square, probing is a gold disc on a 1.1s pulse — then a sentence naming the endpoint in damped-gold code, then a bare endpoint field and a mini button on one row. It never uses the verdict trio: a reachable socket is not the product's reading of an image.

#### Chain Record (signature)
One ruled row per record: a stamp-purple serial, the record's short name with its flag and confluency, a truncated prev/this digest pair, and a right-aligned state cell — all machine-set. State is driven by `data-s`: idle in Ink 3, running in damped gold, verified in verdict green, broken in verdict red at 700 with an 8% row wash and a red serial. A tampered row annotates the exact edit in verdict red inside its name line. The chain is capped to a 1020px ledger measure, because the officer's mark belongs beside its entry, not stranded at the far edge of a 1440px page.

#### Provenance Disclosure (signature)
A ruled list of `<details>` rows: a machine-set key in a fixed 15ch column, the claim in prose beside it, and a CSS chevron drawn from two damped-gold borders that rotates on open. The body indents to the claim's column and caps at 74ch. It is a permanent part of the page, never a modal or a dismissible banner, and below 720px the key wraps above the claim.

#### Named Rules
**The Named State Rule.** Every layer state is written in words beside the control that sets it — shown/hidden on each toggle, and a machine-set line naming the combination — including the state where the mask and the evidence layers coincide, which takes ink at 700 with a damped-gold underline rather than being left for the visitor to notice. No layer state is communicated by a fill colour alone.

**The Recomputed-vs-Stated Rule.** The page distinguishes two kinds of number and never lets them blur. **Recomputed:** the nine bound records, whose SHA-256 digests the browser recomputes with WebCrypto over the same canonical JSON the Python writer hashed, and whose chain the visitor can break on the spot. **Stated:** the five evaluation results (2.3 pp, 31 pp, "thirteen times", 98% test accuracy, 100% contamination recall), which are evaluation findings, not per-record output. Every stated figure carries the `stated` mark — machine-set, damped gold, uppercase, with an underlined link to the disclosure — and the page's provenance section says plainly that the browser does not recompute them. A future number belongs in one bucket or the other before it is set; nothing on this page may imply the pipeline produced a figure on this machine that it did not.

**The No-Guessed-Verdict Rule.** There is no model in the browser, so an uploaded file gets only what a browser can honestly compute: its real SHA-256, its dimensions, and a place in a hash-chained ingest manifest. Confluency, QC flag and action stay visibly **empty** — an Ink 3 machine-set pending mark, never a placeholder value — until the analysis service answers.

**The Snap Rule.** A stamp lands and stops dead: the world's entrance curve is `cubic-bezier(.2,.9,.25,1)` and there is **no overshoot anywhere**. Settles use `cubic-bezier(.16,1,.3,1)`. A leaf is one orchestrated moment then stillness — a 760ms scan sweep, the mask wiping over 760ms, boxes striking on a stagger, witness rows snapping in, the confluency figure landing with a single 260ms press. No parallax, no loop, no scroll-linked animation.

**The Reduced-Motion Endpoint Rule.** Under `prefers-reduced-motion: reduce` every animation and transition collapses to 0.001ms, reveal elements and witness rows start visible, the badge stops rotating, the struck press and the leader draw are cancelled with the leaders left drawn. A reduced-motion visitor gets the endpoint of the story, never a partial state.

**The Browser-Surface Rule.** The parts we did not draw still carry the document: selection is gold on ink, the caret is stamp navy, the focus ring is stamp navy at 3px offset, both scrollbar syntaxes are themed in paper with a damped-gold thumb on hover, links are underlined with a damped-gold decoration at a 3px offset, and every numeric column and figure carries `tabular-nums`. A default blue highlight or a default scrollbar breaks the world as surely as a wrong hex.

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

### The Travel Document

#### Do:
- **Do** keep the two colour systems quarantined: stamp inks are chrome, the verdict trio is the product reading an image (The Colour Quarantine Rule). If a new mark is not a reading of a specimen, it takes a stamp ink.
- **Do** give every verdict a shape and a word as well as an ink, and keep the selector form right — the action badge owns its own `[data-v]` and takes compound selectors; the verdict dot inherits from its container (The Shape-and-Word Rule).
- **Do** compose the ground once, as security paper — guilloché, fibre and intaglio wash on one fixed multiplied layer (The Security Stock Rule).
- **Do** mount specimen imagery on ink inside a gold hairline, and size its frame from the image's own intrinsic dimensions (The Plate-on-Ink Rule, The Measured Plate Rule).
- **Do** rule a leader line from a printed reading back to the pixels it was measured on where the layout allows it, measured off the live layout, and suppress it where it would cross empty space.
- **Do** displace a struck mark's perimeter with the shared ink-bite filter and let the badge multiply into the stock.
- **Do** mark every stated evaluation figure as stated, and keep the provenance disclosure on the page (The Recomputed-vs-Stated Rule).
- **Do** keep functional text at the 11px `--micro` token and cite the token rather than typing a size (The Micro Floor Rule).
- **Do** set the document address beside the headline, never above it, stacking below at ≤760px (The Document Address Rule).
- **Do** build a grouped control as one ruled enclosure with internal dividers, not as a card.
- **Do** theme the browser's own surfaces — selection, caret, both scrollbar syntaxes with a hover state, the focus ring, underline offsets and `tabular-nums` (The Browser-Surface Rule).
- **Do** make any sideways-scrolling element a real focusable region with its caption outside the scroll box (The Real Region Rule).

#### Don't:
- **Don't** flatten the ground to a plain fill, re-apply grain per section, or raise the stock's opacity to make the texture read.
- **Don't** state a verdict with a stamp ink, or use a verdict colour on anything that is not the product reading an image.
- **Don't** collapse the verdict shapes back onto colour, and don't turn the badge's `[data-v]` into a descendant selector — that silently disables the shape channel.
- **Don't** cast an offset shadow, blur a backdrop or float a panel. The only sanctioned shadows are the plate's contact pair, the two emitters, and the inset rule inside a struck mark.
- **Don't** add a radius beyond the 3px page corner, and don't round something for softness — round and oval on this surface mean *cleared*.
- **Don't** set a heading in the machine face, a digest in the didone, or a long instruction in uppercase mono (The Three Hands Rule).
- **Don't** type a functional size below 11px; the label role has a token.
- **Don't** put an eyebrow or kicker above a headline; the document address goes beside it.
- **Don't** lighten `doc-ink-3` — the hex is a measured 5.0:1 on the paper ground and its lighter predecessor failed at 4.20:1.
- **Don't** let an unescaped `<` reach an HTML or SVG renderer from the machine-readable zone; the filler is a tag opener and has swallowed a document once.
- **Don't** compute a confluency, flag or action in the browser to fill an empty column, and don't present an evaluation figure as pipeline output.
- **Don't** add overshoot to any curve, a second auto-advance, a loop, or scroll-linked motion (The Snap Rule).
- **Don't** add `overflow-x: hidden` to `body`; the mask would hide the next real overflow.

---

## Cross-surface notes

Two product defects found while building the landing page, written up in full at `site/README.md`. They belong to the pipeline and the console, not to either design system, and neither is a visual-design decision:

1. `demo/app.py::_scale_bboxes` over-scales Grad-CAM boxes for non-256px images. The box comes from a centred 256×256 crop, so only the origin should be offset, not the box scaled.
2. `culture/rationale.py::_bbox_quadrant` emits a spurious quadrant for a full-frame evidence box, because it reads the box's centre.

The landing page works around (1) by naming the analysed region on the evidence-box serial chip rather than by silently rescaling — a labelling decision, not a fix. The fix belongs in `culture/` and `demo/`.
