# V2 — Local browser and accessibility acceptance

Date: 2026-10-17. Branch: `slice-1b-compute-cache`. **Initial inspection complete; subsequent code fixes pass scoped confirmation, but missing acceptance evidence keeps V2 pending. V3 must not start.** See the [correction and confirmation record](2026-10-17-v2-corrections.md); the findings and results below describe the original inspection.

Dependencies I4 and [V1 correction/retest](2026-10-16-v1-acceptance.md) are complete. Root ran the local browser matrix; an independent reviewer performed the [source accessibility audit and six fix packets](2026-10-17-v2-source-audit.md). This is a review, not a new redesign or implementation batch. No UI source or scientific artifact was edited during V2.

## Executive result

The standalone product story and critical stored-analysis flows work in the tested browser states: both primary readings retain their qualifications, all seven samples select correctly, exact records and return links preserve identity, and verification failures do not falsely pass. This is materially stronger evidence than checking a successful build alone.

It is **not ready for VP-demo signoff**. Five confirmed accessibility/implementation defects need a bounded correction batch; the obsolete mobile navigation fade is an additional risk. Screenshot capture failed for both device classes, so visual hierarchy, rendered legibility and the full visual acceptance contract remain unverified. No invented visual score or rehearsal result is assigned.

## Environment and method

- Existing Vite server: `http://127.0.0.1:5173/`; no new server, dependency installation or deployment.
- Ego Lite CLI reported version `0.5.1.13` and an available update; the page user agent reports Chromium `152.0.0.0` on macOS. Upgrade was not performed. Existing agent TaskSpace 6 was reused; no additional space was created for V2.
- Desktop requested and functionally observed at **1280 × 800**. Mobile geometry checked at **390 × 844** and **320 × 844** using CDP viewport emulation, not physical devices.
- Native pointer actions were used for Raw image and Segmentation. Other functional journeys used native keyboard focus/Enter/Space. A sequential Tab journey was tested separately; programmatically focusing a control is not claimed as proof of its tab order.
- Browser-only fault injection used `Network.setBlockedURLs`, a temporary rejecting `crypto.subtle.digest`, and a temporary delayed fetch for the default contour. Blocks and document-start injections were removed in `finally` blocks. Nothing was written into canonical data or backend code.
- Commands were run via `ego-browser nodejs` heredocs. The V1 saved media-reset script remains separately reproducible with `ego-browser nodejs < site/tests/media-reset.browser.js`.

## Browser matrix

| Acceptance area | Observed result | Limit / disposition |
|---|---|---|
| Default first view | DOM contains approved hero, actual C2C12 image, 39.41%, continue, no-band and no-clearance qualification; no version comparison table in opening | Screenshot unavailable; visual first-view acceptance pending |
| HT29 task | 52.91%; 23.51–82.31% band; target 80%; human review and mixed-setup/non-blind/unsupported-bank qualifications; link selects record 9 | Content/state pass; annotated screenshot pending |
| Layers/reset | Pointer Raw removes overlays; Segmentation restores contour; keyboard anomaly toggle produces Custom layers; Reset restores default | Values/identity retained; pointer coverage incomplete due interception described below |
| Selection | All seven More examples buttons and all seven direct `?example=` URLs select their exact record links; one selected button; unknown ID shows explicit fallback notice | Pass for tested states; V1 regression independently covers Back/Forward, reset and unrelated-query retention |
| Query retention | HT29 switch retained `campaign=v2`; invalid-ID recovery also retained unrelated campaign | Pass |
| Exact records | C2C12 → record 4; HT29 → record 9; both Return to this reading links restore exact readings | Pass |
| Tamper/reset | On record 9, edit makes chain/checkpoint fail; rewrite makes chain pass/checkpoint fail; truncation makes remaining chain pass/checkpoint fail. Reset after each restores all nine | Pass; browser-local demonstration only |
| Forced verification failure | Home says unavailable/no match confirmed; Records says could not verify and shows zero verified record buttons | Pass for honesty; workspace live announcement defect S4 remains |
| Missing media | Individually blocked default image, contour and enabled probability layer each show named error/retry, preserve exact identity, and recover on Retry media | Pass for these three fault cases, not every possible asset |
| Delayed contour/sample switch | With default contour fetch delayed 1.8 seconds, switching to HT29 yields HT29 image, 52.91%, record link and contour viewBox `0 0 111 104` | No substitution observed; this does not exhaust every late-response ordering |
| Page entries/legacy routes | Four entries load; all six moved hashes resolve to contracted destinations; all ten retained hashes exist, with technical disclosure open where required | Pass for local destinations; external services not checked |
| Keyboard | Skip link, Enter to main, then 12 sequential Tabs traverse primary links/controls/disclosures and exit workspace; each observed focus state has a 2px outline | No trap in tested primary journey; not a screen-reader/full-site certification |
| Narrow reflow | All four entries have document scrollWidth equal to innerWidth at 390 and 320 | Page-overflow pass; internally scrolling tables/code are not page overflow; visual clipping and text legibility still pending |
| Mobile image/result order | At 390, image rectangle starts y417, ends y665; result rail starts y772 | DOM geometry supports image-before-result, not visual screenshot acceptance |
| Reduced motion | Emulated preference matches and document scroll behavior becomes `auto` | Partial: explicit Records JSON smooth scroll ignores preference (S2) |
| 200% text zoom | Not completed | Pending; narrow viewport tests are not a substitute |
| Contrast / scale / announcements | Source audit and computed-style confirmations below | Fails/pending corrections; no global contrast or assistive-technology certification |

### Route inventory exercised

- Moved: `/#records` → `/records`; `/#integration` → `/records#integration`; `/#validation` → `/validation#checks`; `/#limits` → `/validation#detectability`; `/#confluency` → `/validation#confluency`; `/#changes` → `/release-notes`.
- Retained: `#timeline`, `#accuracy`, `#passage`, `#specs`, `#scope`, `#how`, `#top`, `#evidence`, `#pilot`, `#trail`.
- Samples: `c2c12_normal_0_20`, `c2c12_normal_20_40`, `c2c12_normal_40_100`, `c2c12_contamination_1`, `c2c12_contamination_real_size`, `evican_pc3`, `evican_ht29`.

## Defects returned to owners

Use the independent report's V2-S1–S6 packets for scope, source lines, reproduction and acceptance criteria. Fix in one coordinated batch, not unrelated polish.

1. **S1 / P1:** unchecked tamper-switch contrast. Browser computed styles confirm track `rgb(200, 207, 215)`, white thumb, paper `rgb(245, 246, 248)` and `0px none` border. Source ratios are 1.45:1 track/paper and 1.57:1 thumb/track, below the requested 3:1. Owner: shared stylesheet/Records UI.
2. **S2 / P2:** JSON's explicit smooth scroll ignores reduced-motion preference. Owner: Records UI.
3. **S3 / P2:** physical scale label is hidden from assistive technology. Owner: workspace.
4. **S4 / P2:** asynchronous workspace verification lacks its own status announcement. Owner: workspace.
5. **S5 / P2:** undefined primary-control border token. Browser confirms empty `--stage-rule-2` and both Raw/Segmentation borders computed as `0px none`; selected color alone does not create a boundary. Owner: workspace stylesheet.
6. **S6 / P2 risk:** the mobile nav retains `linear-gradient(... calc(100% - 40px), transparent)` masking despite fitted navigation. Browser confirms the computed mask at 390px; actual impact on Integration's text/focus must be visually established. Owner: homepage/shared navigation stylesheet.

Secondary tab-pattern semantics are recorded in the independent report, not folded into an unbounded primary-journey rewrite. Material source qualifications and scientific values must remain unchanged.

## Capture and automation limitations

The single initial desktop/mobile capture batch attempted:

| Intended file | Sample / viewport | Result |
|---|---|---|
| `/tmp/cultureqc-v2-desktop-default.png` | `c2c12_normal_20_40`, requested 1280 × 800 | `CdpRequestTimeoutError: Page.captureScreenshot`; no usable image |
| `/tmp/cultureqc-v2-mobile-default.png` | `c2c12_normal_20_40`, 390 × 844 | `CDP request timed out: Page.captureScreenshot`; no usable image |

These are **attempted locations, not delivered screenshot evidence**. No image was inspected or counted as a visual pass. After the desktop timeout, the viewport read 640 × 400; the intended capture dimensions therefore cannot be certified. The next functional round explicitly restored and observed 1280 × 800. No repeated screenshot loop or alternate browser was used to manufacture a pass. Task/HT29/layer screenshots remain missing along with first-view evidence.

After successful Raw/Segmentation pointer activation, clicking the analysis-details summary encountered `ElementResolutionError: <div> intercepts pointer events` during automation scrolling. A subsequent snapshot showed the summary still closed and the nearby view controls unobstructed at their centres. This does not establish a permanent UI obstruction or certify pointer behavior; reproduce the summary interaction manually or in the confirmation batch. Keyboard opening and layer activation succeeded.

The fault-injection batch completed its assertions and computed-style outputs, then an optional `Browser.getVersion` query failed because that method was unavailable. This metadata error is not counted as a successful command exit or an application failure. Temporary fault injections had already been removed.

## Closure and next dispatch

- TaskSpace 6 closed successfully with `finish({ keep: [] })` after recording a clean default page with no media errors. The local Vite server remains running for the user.
- Documentation-only V2 work; `git diff --check` passes. Protected tracked backend/data/report/assets/deployment paths remain unchanged from HEAD. The known pre-existing `site/src/data.json` addition remains 12 lines and was not edited.
- Do not rerun all scientific tests to imply these accessibility defects are fixed. V1's 11 Node + 130 Python tests and production build are recorded in its own fresh correction result, not presented as newly rerun by V2.
- Return S1–S5 to the owners for a bounded correction batch; verify S6 and pointer behavior. Then run focused regression/build checks and the one allowed confirmation batch, including actual screenshots, 200% text zoom and accessibility status/scale checks.
- If browser capture remains unavailable, leave visual acceptance pending and request a manual capture/review or user-approved browser repair/update. The tooling update is not itself evidence of a fix.
- V3 still requires V2 plus a real timed presenter/fresh-reviewer rehearsal. No deployment, production-readiness or commercial-clearance claim follows from this report.
