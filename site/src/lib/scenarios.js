export const GUIDED_SCENARIOS = [
  {
    id: "evican_ht29",
    title: "Boundary: a person decides",
    specimen: "EVICAN HT29 · real frame",
    note: "The setup-level band crosses the target. This demonstrates the review rule, not validated biological action.",
    scope: "Research demonstration. Mixed-setup EVICAN calibration is not fully blind; the C2C12 anomaly bank is not calibrated for HT29.",
  },
  {
    id: "evican_pc3",
    title: "Sparse: continue recommendation",
    specimen: "EVICAN PC3 · real frame",
    note: "The stored rule recommends continued culture because the band is below the target. The anomaly score is flagged, but this stored policy did not let that flag change the action.",
    scope: "Research recommendation, not universal clearance or a contamination-free finding. EVICAN calibration is mixed-setup and its C2C12 anomaly bank is not calibrated for PC3.",
  },
  {
    id: "c2c12_contamination_1",
    title: "Image quality: capture again",
    specimen: "C2C12 · synthetic stress test",
    note: "The stored quality gate found exposure out of range, so the action is to re-image before a culture decision.",
    scope: "OVERSIZED SYNTHETIC STRESS TEST: pasted bacteria are 16.5× too large. This is not evidence of realistic contamination detection. This setup has no calibrated error band.",
  },
];

export const DEFAULT_SCENARIO_ID = GUIDED_SCENARIOS[0].id;

function isAllowed(id, allowedIds) {
  return allowedIds ? allowedIds.includes(id) : GUIDED_SCENARIOS.some((scenario) => scenario.id === id);
}

export function scenarioIdFromSearch(search, allowedIds) {
  const id = new URLSearchParams(search).get("example");
  return isAllowed(id, allowedIds) ? id : DEFAULT_SCENARIO_ID;
}

export function scenarioUrl(href, id, allowedIds) {
  const url = new URL(href);
  url.searchParams.set("example", isAllowed(id, allowedIds) ? id : DEFAULT_SCENARIO_ID);
  url.hash = "demo";
  return `${url.pathname}${url.search}${url.hash}`;
}
