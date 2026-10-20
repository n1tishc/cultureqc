export const GUIDED_SCENARIOS = [
  {
    id: "c2c12_normal_20_40",
    title: "Measure coverage",
    specimen: "C2C12 · real frame · mid density",
    note: "Switch between the raw image and its computed cutoff contour to inspect measured coverage.",
    scope: "Research demonstration. This example has no calibrated error band. Its normal-source label is not a health finding or contamination clearance.",
  },
  {
    id: "evican_ht29",
    title: "Understand a review boundary",
    specimen: "EVICAN HT29 · real frame",
    note: "The setup-level band crosses the target. This demonstrates the review rule, not validated biological action.",
    scope: "Research demonstration. Mixed-setup EVICAN calibration is not fully blind; the C2C12 anomaly bank is not calibrated for HT29.",
  },
];

export const EXAMPLE_CONTEXT = {
  ...Object.fromEntries(GUIDED_SCENARIOS.map((scenario) => [scenario.id, scenario])),
  evican_pc3: {
    title: "EVICAN PC3 · sparse culture",
    specimen: "EVICAN PC3 · real frame",
    note: "The stored rule recommends continued culture because the band is below the target. The anomaly score is flagged, but this stored policy did not let that flag change the action.",
    scope: "Research recommendation, not universal clearance or a contamination-free finding. EVICAN calibration is mixed-setup and its C2C12 anomaly bank is not calibrated for PC3.",
  },
  c2c12_contamination_1: {
    title: "Oversized bacteria · synthetic stress test",
    specimen: "C2C12 · synthetic stress test",
    note: "The stored quality gate found exposure out of range, so the action is to re-image before a culture decision.",
    scope: "OVERSIZED SYNTHETIC STRESS TEST: pasted bacteria are 16.5× too large. This is not evidence of realistic contamination detection. This setup has no calibrated error band.",
  },
  c2c12_contamination_real_size: {
    title: "Real-size bacteria · synthetic example",
    specimen: "C2C12 · simulated bacteria",
    scope: "SYNTHETIC EXAMPLE: bacteria were added to a real frame. Real-size detection performed near chance; this continue recommendation is not contamination clearance. No calibrated error band is available.",
  },
};

export const DEFAULT_SCENARIO_ID = GUIDED_SCENARIOS[0].id;

function isAllowed(id, allowedIds) {
  return allowedIds ? allowedIds.includes(id) : GUIDED_SCENARIOS.some((scenario) => scenario.id === id);
}

export function scenarioIdFromSearch(search, allowedIds) {
  return scenarioSelectionFromSearch(search, allowedIds).id;
}

export function scenarioSelectionFromSearch(search, allowedIds) {
  const requestedId = new URLSearchParams(search).get("example");
  return {
    id: isAllowed(requestedId, allowedIds) ? requestedId : DEFAULT_SCENARIO_ID,
    invalid: requestedId !== null && !isAllowed(requestedId, allowedIds),
  };
}

export function initialLayers() {
  return { prob: false, contour: true, band: false, anom: false };
}

export function layersForView(view) {
  return { ...initialLayers(), contour: view === "segmentation" };
}

export function layerView(layers) {
  if (!Object.values(layers).some(Boolean)) return "raw";
  return layers.contour && !layers.prob && !layers.band && !layers.anom ? "segmentation" : "custom";
}

export function scenarioUrl(href, id, allowedIds) {
  const url = new URL(href);
  url.searchParams.set("example", isAllowed(id, allowedIds) ? id : DEFAULT_SCENARIO_ID);
  url.hash = "demo";
  return `${url.pathname}${url.search}${url.hash}`;
}
