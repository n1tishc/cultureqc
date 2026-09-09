# cultureQC Demo UI Plan

## Context

This is a demo for a cell culture quality control tool. The audience is a VP at a lab automation company (Celltrio). The UI must look like real lab software — not a student project. The analysis backend already exists in `pipeline.py` and works. This plan is only about the presentation layer.

## Reference products (what the industry looks like)

- Sartorius Incucyte: split-pane, phase image with colored mask overlay, results panel on right
- Molecular Devices CellXpress.ai: clean image viewer, toggleable annotation overlays, card-based results
- Leica Mateo: large image hero, confluency as big number with progress indicator
- CellProfiler Analyst: image viewer with overlay toggle, sidebar results

Every single one uses: dark theme, image as hero (60%+ of viewport), status communicated by color, metrics as large scannable numbers, audit/metadata collapsed by default.

---

## Framework recommendation

Options in order of polish ceiling:

1. **React + FastAPI** — total control, looks like real software. Backend is one POST endpoint calling `pipeline.py`. Best option if comfortable with React.
2. **NiceGUI** — Python framework with full Tailwind CSS + Quasar components. High polish ceiling, stays in Python.
3. **Gradio Blocks + custom theme** — minimum changes to current stack. Use `gr.Blocks`, custom `gr.themes.Base` subclass, `elem_classes` on every component, and a `css=` string. Good enough for a screen recording.

Pick one. The layout and design rules below apply regardless.

---

## Layout: split-pane, image-dominant

```
┌─────────────────────────────────────────────────────────────┐
│  ◉ cultureQC            [cell line ▾] [target %] [Analyze]  │
├──────────────────────────────────┬──────────────────────────┤
│                                  │  STATUS CARD             │
│                                  │  ┌────────────────────┐  │
│                                  │  │ 🟢 Normal          │  │
│       IMAGE VIEWER               │  │ confidence: 0.97   │  │
│       (60–65% width)             │  └────────────────────┘  │
│                                  │                          │
│    original ← toggle → overlay   │  CONFLUENCY CARD         │
│                                  │  ┌────────────────────┐  │
│                                  │  │     82.3%          │  │
│                                  │  │  ████████░░ 80%    │  │
│                                  │  │  target ↑          │  │
│                                  │  └────────────────────┘  │
│                                  │                          │
│                                  │  ACTION CARD             │
│                                  │  ┌────────────────────┐  │
│                                  │  │  → Passage         │  │
│                                  │  └────────────────────┘  │
│                                  │                          │
│                                  │  RATIONALE               │
│                                  │  "No abnormalities..."   │
│                                  │                          │
│                                  │  ▸ Audit Record (JSON)   │
├──────────────────────────────────┴──────────────────────────┤
│  cultureQC v0.1 · Cellpose-SAM · EfficientNet-B0           │
└─────────────────────────────────────────────────────────────┘
```

### Top bar
- Left: app name/logo "cultureQC" — small, not a giant header
- Right: cell line dropdown, target confluency numeric input, "Analyze" button
- Upload is either: drag-drop on the image area (dropzone when empty), OR a subtle upload button in the top bar
- No other controls. Three inputs total.

### Image viewer (left, 60–65% width)
- The microscopy image is the largest element on screen
- Toggle between original and analysis overlay: simple switch or two radio buttons above the image, not a dropdown
- Overlay rendering:
  - Cell mask: semi-transparent green at 30–40% opacity so original is always visible underneath
  - Evidence boxes (Grad-CAM): 2px red stroke, no fill, subtle glow/drop-shadow so they pop on dark cell backgrounds
  - Max 8 boxes (already implemented in backend)
- When no image is loaded: show a centered dropzone with dashed border and "Drop a microscope image" text
- Image should fill its container, maintain aspect ratio, no scrollbars

### Results panel (right, 35–40% width)
- Vertical stack of cards. No form labels like "QC Flag:". The card IS the information.
- Cards appear only after analysis runs. Before that, the panel shows a brief instruction or is empty.

#### Card 1: Status
- Full-width card
- Background: subtle tint of the status color at ~8% opacity
- Content: status icon + label ("Normal", "Contamination Suspected", "Detachment", "Image Quality") at 20–24px, semi-bold or uppercase
- Confidence as a small pill/badge next to the label (e.g. "0.97")
- Status color drives the card tint:
  - `normal` → green
  - `contamination_suspected` → red
  - `detachment` → amber
  - `image_quality` → amber

#### Card 2: Confluency
- Confluency percentage as the largest number on screen: 48–56px, bold, monospace or semi-bold sans-serif
- Horizontal progress bar below the number showing actual vs target
- Target marked with a vertical line or label on the bar
- If confluency > target: bar fill is green. If below: bar fill is neutral/gray.
- Below the bar: small text "Target: 80%" and "Method: Cellpose-SAM cpsam_v2 prob-map"

#### Card 3: Action
- Single word or short phrase: "Passage", "Feed", "Hold", "Human Review"
- Styled as a prominent pill/badge
- Same color as the status card (green/amber/red)
- This is the "what do I do" answer — should be instantly readable

#### Rationale
- Below the cards, not in a card — just a text block
- 14px, regular weight, secondary/muted text color
- 1–2 sentences from the template rationale
- No label above it — the text speaks for itself

#### Audit Record
- Collapsed by default: just a row with a chevron and "Audit Record"
- Expands on click to show the full JSON record, syntax-highlighted or in a monospace code block
- The VP doesn't need to see this on first glance but it must be there when they look for it

### Footer
- Single line, small text, muted color
- Content: "cultureQC v0.1 · Cellpose-SAM · EfficientNet-B0 · MIT"
- No links, no clutter

---

## Color system

Dark theme only. No light mode toggle needed.

| Token | Value | Usage |
|---|---|---|
| `bg-primary` | `#0f1117` | Page background |
| `bg-card` | `#1a1d24` | Card backgrounds |
| `bg-card-border` | `#2a2d34` | Subtle card borders, 1px |
| `text-primary` | `#f0f0f0` | Headings, big numbers |
| `text-secondary` | `#9ca3af` | Labels, rationale, metadata |
| `text-muted` | `#6b7280` | Footer, collapsed sections |
| `status-green` | `#22c55e` | Normal, passage |
| `status-amber` | `#f59e0b` | Feed, hold, detachment, image_quality |
| `status-red` | `#ef4444` | Contamination, human review |
| `overlay-mask` | `#22c55e` at 35% opacity | Cell segmentation overlay on image |
| `overlay-evidence` | `#ef4444` | Evidence bounding boxes, 2px stroke |
| `accent` | `#3b82f6` | Analyze button, interactive elements |

Status color usage:
- Status card background tint: status color at 8% opacity
- Status card text/icon: status color at full opacity
- Action badge: status color background at 15% opacity, status color text
- Progress bar fill: green if above target, neutral gray if below
- Evidence boxes on image: always red regardless of flag

---

## Typography

| Element | Size | Weight | Font |
|---|---|---|---|
| App name in top bar | 16px | 600 | System sans-serif |
| Confluency number | 48–56px | 700 | Monospace or `JetBrains Mono` or `SF Mono` |
| Status label | 20–24px | 600 | System sans-serif |
| Action badge | 16–18px | 600 | System sans-serif |
| Card secondary text | 13px | 400 | System sans-serif |
| Rationale | 14px | 400 | System sans-serif |
| Audit record JSON | 12px | 400 | Monospace |
| Footer | 12px | 400 | System sans-serif |

Visual hierarchy (where the VP's eyes go in order):
1. Image (biggest area)
2. Status card color (instant read: green = good, red = problem)
3. Confluency number (biggest text)
4. Action badge (what to do)
5. Everything else

---

## Interaction flow

### Empty state
- Image area shows dropzone: dashed border, centered icon + "Drop a microscope image or click to upload"
- Results panel is empty or shows a single line: "Upload an image to begin analysis"
- Top bar inputs have defaults: cell line = "A172", target = 80

### After upload, before analysis
- Image appears in the viewer (original, no overlay)
- Results panel still empty
- "Analyze" button is enabled and visually prominent

### During analysis
- Brief loading state on the image area: subtle pulse/skeleton overlay, NOT a spinner with text like "Running Cellpose-SAM..."
- Analyze button shows a loading state (spinner icon replaces text, or button dims)
- Duration: ~3–5 seconds for the full pipeline

### After analysis
- Overlay appears on the image (default: overlay ON, toggle available)
- Results cards animate in from the right, staggered 100ms apart. Subtle slide-in + fade, not bouncy.
- Status card color transition is smooth (200ms ease)
- All data populated from the pipeline response

### Running a second image
- Upload replaces the image, clears results
- Or: previous results fade out, new results animate in after analysis
- Status card color shift should be visible (green → red if going from normal to contamination)

---

## Contamination case (the money shot)

When the flag is `contamination_suspected`:
- Status card: red tint background, "Contamination Suspected" in red, high confidence
- Evidence boxes: multiple red bounding boxes on the image overlay, prominent
- Action: "Human Review" in red badge
- Rationale: "Small dark rod-like objects detected in the [quadrant], absent from background regions..."
- This is what no other tool shows: WHERE the contamination is with explainable bounding boxes

This is the frame that ends the demo video. Make it look unmistakable.

---

## Things to NOT do

- ❌ No Gradio default purple/orange accent colors
- ❌ No vertical stack where you scroll past the image to see results
- ❌ No raw JSON visible on the main screen (collapsed only)
- ❌ No "Output:" or "Input:" labels above components
- ❌ No multiple tabs — everything on one screen
- ❌ No loading text like "Running Cellpose-SAM..." — implementation details don't belong in the UI
- ❌ No giant page title taking up vertical space
- ❌ No form-style layout with labels left and values right
- ❌ No scrolling required to see the full result after analysis

---

## Backend wiring

The analysis backend is already implemented. The UI just needs to call it.

### Input to pipeline
```python
from culture.pipeline import analyze_image

result = analyze_image(
    image_path="/path/to/uploaded/image.png",
    cell_line="A172",
    target_confluency=80.0,
    hours_since_passage=48,
)
```

### Output from pipeline (dict)
```json
{
  "confluency_pct": 82.3,
  "confluency_confidence": 0.91,
  "confluency_method": "cpsam_v2_probmap",
  "qc_flag": "normal",
  "qc_confidence": 0.97,
  "evidence_boxes": [[x1,y1,x2,y2], ...],
  "rationale": "No abnormalities detected...",
  "recommended_action": "passage",
  "overlay_image_path": "/tmp/overlay.png",
  "record": { ... full hash-chained JSON record ... }
}
```

### What the UI renders from each field
| Pipeline field | UI element |
|---|---|
| `qc_flag` | Status card label + color |
| `qc_confidence` | Status card confidence pill |
| `confluency_pct` | Big number in confluency card |
| `confluency_confidence` | Small text below confluency |
| `confluency_method` | Small text in confluency card |
| `evidence_boxes` | Red bounding boxes drawn on the overlay image |
| `rationale` | Rationale text block |
| `recommended_action` | Action badge |
| `overlay_image_path` | Image viewer overlay mode |
| `record` | Collapsed audit record JSON |

### Image overlay rendering
The overlay image with the green cell mask is generated by the pipeline. The evidence boxes (red) should be drawn on top by the UI when rendering, OR the pipeline can composite them. Currently the pipeline returns both the overlay image and the box coordinates — use whichever is simpler in your framework.

---

## Video recording specs

After the UI is built:
- Window: 1280×800
- Run three images in sequence WITHOUT refreshing the page:
  1. Normal A172 → green status, high confluency, "Passage"
  2. SHSY5Y → green status, shows accurate confluency where threshold would fail
  3. Contaminated tile (late severity) → red status, red evidence boxes, "Human Review"
- The status card color shifting green → green → red across the three runs IS the visual narrative
- Final frame = contamination state with red boxes. That's the thumbnail.
- Record with QuickTime (Cmd+Shift+5) or OBS, export 720p MP4
- Extract 10s GIF of the contamination shot for email:
  ```bash
  ffmpeg -ss [START] -t 10 -i demo_video.mp4 -vf "fps=10,scale=600:-1" contamination_demo.gif
  ```
