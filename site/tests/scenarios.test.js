import test from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_SCENARIO_ID, GUIDED_SCENARIOS, scenarioIdFromSearch, scenarioUrl } from "../src/lib/scenarios.js";
import data from "../src/data.json" with { type: "json" };

const allIds = data.examples.items.map((item) => item.id);

test("guided scenarios resolve valid links and ignore unknown values", () => {
  assert.equal(GUIDED_SCENARIOS.length, 3);
  assert.equal(scenarioIdFromSearch("?example=evican_pc3"), "evican_pc3");
  assert.equal(scenarioIdFromSearch("?example=unknown"), DEFAULT_SCENARIO_ID);
  assert.equal(scenarioIdFromSearch(""), DEFAULT_SCENARIO_ID);
  assert.equal(allIds.length, 7);
  for (const id of allIds) assert.equal(scenarioIdFromSearch(`?example=${id}`, allIds), id);
});

test("scenario navigation preserves other query values and points to the demo", () => {
  assert.equal(
    scenarioUrl("https://example.test/?campaign=pilot#old", "c2c12_contamination_1"),
    "/?campaign=pilot&example=c2c12_contamination_1#demo",
  );
  assert.equal(scenarioUrl("https://example.test/", "unknown"), `/?example=${DEFAULT_SCENARIO_ID}#demo`);
  for (const id of allIds) {
    assert.equal(scenarioUrl("https://example.test/", id, allIds), `/?example=${id}#demo`);
  }
});
