# V2 — Post-update visual evidence and manual handoff

Date: 2026-10-17. **Screenshot blocker resolved; scoped visual checks and saved accessibility regression pass. V2 remains pending actual 200% zoom and screen-reader confirmation. V3 has not started.**

This follows the [S1–S6 corrections](2026-10-17-v2-corrections.md). The user approved proceeding after the browser-update request. `ego-browser upgrade` reported that the update was installed and restarted Ego Lite; the refreshed runtime guide is v2.1.0. This guide version is not an application-version claim.

## Captured and inspected evidence

All delivered images below were opened and visually inspected, not merely generated. Image dimensions were checked with `sips`. Desktop captures are 1280×800; mobile captures are 390×844. The updated browser reports Chromium 154.0.0.0 on macOS through its user agent. The site is the existing local Vite server at `http://127.0.0.1:5173/`.

| State | Saved image | Observation |
|---|---|---|
| C2C12 default / reset | [Desktop segmentation](assets/2026-10-17-v2/desktop-segmentation.png) | Hero, actual microscopy, 39.41%, CONTINUE, qualifications and exact-record link are visible together. No version-comparison table. |
| C2C12 raw | [Desktop raw](assets/2026-10-17-v2/desktop-raw.png) | After the overlay transition finishes, the raw frame has no cyan contour; measurement and record remain unchanged. |
| C2C12 custom layer | [Desktop custom](assets/2026-10-17-v2/desktop-custom.png) | Cell probability overlay and “Custom layers” state appear; 39.41% and record 4 remain unchanged. Reset restores segmentation. |
| HT29 review boundary | [Desktop HT29](assets/2026-10-17-v2/desktop-ht29.png) | 52.91%, 23.51–82.31% band, 80% target and HUMAN REVIEW are visible with the reason and material qualifications. |
| Mobile entry | [Mobile first view](assets/2026-10-17-v2/mobile-first-view.png) | Navigation is complete and unmasked; hero and microscopy precede the result. The reading is below the first viewport, not missing. |
| Mobile result after scrolling | [Mobile result](assets/2026-10-17-v2/mobile-result.png) | Reading, recommendation, qualifications, verification and exact-record link are readable without horizontal page overflow. |

Independent reviewer `vp_design_review` inspected the mobile first view and desktop HT29 images: scoped visual pass, no demonstrated blockers, no clipped material qualifications or text collisions. The root reviewer inspected all six delivered images. These observations do not certify all pages, all color pairs or assistive-technology speech.

Early intermediate captures are deliberately excluded: the desktop viewport initially remained 1512×792 despite an intended override, and a Raw capture caught the outgoing contour transition. The delivered desktop states use checked dimensions; Raw waits for finite animations to finish. Neither intermediate is presented as an application defect or valid acceptance image.

## Fresh runtime checks

The saved regression was run once against the updated browser, reusing TaskSpace 1:

```sh
{ printf 'const regressionSpaceId = 1;\n'; cat site/tests/accessibility.browser.js; } | ego-browser nodejs
```

Exit 0; all six groups passed: accessible scale/status/borders, absent unknown HT29 scale, 390px/320px navigation and overflow, unchecked switch contrast, reduced-motion scrolling with preserved focus and tamper/reset, and honest delayed verification failure without focus movement. The prior selector-based analysis-disclosure click also succeeds in this browser run; no coordinate fallback was needed.

No application source changed in this follow-up. Build and Node tests were not rerun for documentation/image-only changes; their prior results remain in the corrections report rather than being claimed as fresh.

## Remaining manual acceptance — do not bypass

The user explicitly elected to keep human screen-reader verification pending. A subsequent native-menu zoom attempt also failed to target the task page: the browser's underlying New Tab briefly reached 110% and was reset to a confirmed 100%. Opening the task's full browser space changed its available viewport from 1512×792 to 1500×724; DPR remained 2, with no verified 200% setting on the demo. No zoom acceptance result follows from this attempt; further automated zoom retries are deferred to avoid spending more time on browser control rather than product work.

Native zoom shortcuts still did not change the measured viewport or DPR: 1512×792 and DPR 2 before and after five increase shortcuts. Reset was issued afterward. This is a failed automation attempt, **not evidence of 200% zoom or a website reflow failure**.

1. **200% zoom:** In a normal browser tab, use its menu to explicitly select 200%. Check both homepage tasks, Records, Evidence and Release notes. Confirm text and primary controls remain available, no content overlaps or is clipped, and the page does not require horizontal scrolling to read ordinary content. Record browser/version, confirmed zoom setting and screenshots. Restore 100% afterward.
2. **Screen reader:** With VoiceOver or another real screen reader, navigate by keyboard through sample selection and Raw/Segmentation controls. Confirm labels and selected states, one meaningful physical-scale label for C2C12 and none invented for HT29, intelligible result/view/status announcements without disruptive repetition, and no unexpected focus movement. Actual verification-failure speech remains unconfirmed even though the regression checks its live-region semantics and focus behavior.

If either check exposes a defect, record reproduction, expected/actual behavior and severity before a bounded correction. Do not silently waive these requirements or substitute accessibility-tree checks for speech.

Once those checks pass, V3 is the next runnable node: an actual five-minute presenter rehearsal and fresh human reviewer answers to the five product questions in [05-acceptance](../specs/standalone-product-site/05-acceptance.md). An agent's screenshot review is not that human rehearsal.

## Preservation and handoff

Scientific values, assets used by the application, policies, records and all existing working-tree changes are preserved. Only review documentation and copies of captured evidence are added by this follow-up. No commit, merge, deployment or production-readiness claim occurred. The original server on port 5173 is healthy; an inadvertently started second Vite process on 5174 was stopped. The browser task is handed to the user for manual acceptance rather than silently claiming the gate complete.
