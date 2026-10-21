import test from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_SCENARIO_ID, EXAMPLE_CONTEXT, GUIDED_SCENARIOS, initialLayers, layersForView, layerView, scenarioIdFromSearch, scenarioSelectionFromSearch, scenarioUrl } from "../src/lib/scenarios.js";
import data from "../src/data.json" with { type: "json" };

const allIds = data.examples.items.map((item) => item.id);

test("two independent analysis tasks start with the review-boundary example", () => {
  assert.deepEqual(GUIDED_SCENARIOS.map((scenario) => scenario.id), ["evican_ht29", "c2c12_normal_20_40"]);
  assert.equal(DEFAULT_SCENARIO_ID, "evican_ht29");
  assert.equal(scenarioIdFromSearch("?example=c2c12_normal_20_40"), "c2c12_normal_20_40");
  assert.equal(scenarioIdFromSearch("?example=unknown"), DEFAULT_SCENARIO_ID);
  assert.equal(scenarioIdFromSearch(""), DEFAULT_SCENARIO_ID);
  assert.equal(allIds.length, 7);
  for (const id of allIds) assert.equal(scenarioIdFromSearch(`?example=${id}`, allIds), id);
});

test("missing selection differs from an explicitly invalid selection", () => {
  assert.deepEqual(scenarioSelectionFromSearch("", allIds), { id: DEFAULT_SCENARIO_ID, invalid: false });
  assert.deepEqual(scenarioSelectionFromSearch("?campaign=pilot", allIds), { id: DEFAULT_SCENARIO_ID, invalid: false });
  for (const search of ["?example=unknown", "?example=", "?example=%3Cscript%3E"]) {
    assert.deepEqual(scenarioSelectionFromSearch(search, allIds), { id: DEFAULT_SCENARIO_ID, invalid: true });
  }
  for (const id of allIds) {
    assert.deepEqual(scenarioSelectionFromSearch(`?example=${id}`, allIds), { id, invalid: false });
  }
});

test("scenario navigation preserves other query values and points to the demo", () => {
  assert.equal(
    scenarioUrl("https://example.test/?campaign=pilot#old", "c2c12_contamination_1", allIds),
    "/?campaign=pilot&example=c2c12_contamination_1#demo",
  );
  assert.equal(scenarioUrl("https://example.test/", "unknown"), `/?example=${DEFAULT_SCENARIO_ID}#demo`);
  for (const id of allIds) {
    assert.equal(scenarioUrl("https://example.test/", id, allIds), `/?example=${id}#demo`);
  }
});

test("raw clears every overlay; segmentation and reset restore contour only", () => {
  const custom = { prob: true, contour: true, band: true, anom: true };
  assert.equal(layerView(custom), "custom");
  assert.deepEqual(layersForView("raw"), { prob: false, contour: false, band: false, anom: false });
  assert.equal(layerView(layersForView("raw")), "raw");
  assert.equal(layerView(initialLayers()), "segmentation");
  assert.deepEqual(layersForView("segmentation"), initialLayers());
  const modified = initialLayers();
  modified.anom = true;
  assert.equal(layerView(modified), "custom");
  assert.equal(layerView(initialLayers()), "segmentation");
  assert.equal(layerView({ prob: true, contour: false, band: false, anom: false }), "custom");
});

test("primary examples retain stored measurements, reasons and record identity", () => {
  const coverage = data.examples.items.find((item) => item.id === "c2c12_normal_20_40");
  const boundary = data.examples.items.find((item) => item.id === "evican_ht29");
  assert.equal(coverage.confluency.pct.toFixed(2), "39.41");
  assert.equal(coverage.confluency.interval, null);
  assert.equal(coverage.action, "continue");
  assert.equal(boundary.confluency.pct.toFixed(2), "52.91");
  assert.deepEqual(boundary.confluency.interval.map((value) => value.toFixed(2)), ["23.51", "82.31"]);
  assert.equal(boundary.target, 80);
  assert.equal(boundary.action, "human_review");
  for (const item of [coverage, boundary]) {
    assert.ok(item.action_reason);
    assert.ok(item.record.canonical);
    assert.equal(data.examples.chain_order[item.record.index - 1], item.id);
  }
  assert.match(EXAMPLE_CONTEXT.c2c12_contamination_1.scope, /16\.5×/);
  assert.match(EXAMPLE_CONTEXT.c2c12_contamination_real_size.scope, /SYNTHETIC/);
  assert.match(EXAMPLE_CONTEXT.evican_pc3.scope, /not calibrated for PC3/);
});
