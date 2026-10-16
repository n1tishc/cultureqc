import test from "node:test";
import assert from "node:assert/strict";
import { readingTargetIndex, recordIndexFromSearch, recordUrl } from "../src/lib/record-selection.js";

const ids = ["change1", "change2", "evican_ht29"];

test("record deep links select exact records and fall back on invalid ids", () => {
  assert.equal(recordIndexFromSearch("?record=evican_ht29", ids, 1), 2);
  assert.equal(recordIndexFromSearch("?record=unknown", ids, 1), 1);
  assert.equal(recordIndexFromSearch("", ids, 1), 1);
});

test("record URLs retain unrelated parameters and target the chain", () => {
  assert.equal(recordUrl("https://example.test/records?campaign=pilot#old", "evican_ht29"), "/records?campaign=pilot&record=evican_ht29#chain");
});

test("a selected reading becomes the tamper target; a change uses the fallback reading", () => {
  const chain = [{ kind: "change" }, { kind: "change" }, { kind: "reading" }];
  assert.equal(readingTargetIndex(2, chain, 2), 2);
  assert.equal(readingTargetIndex(0, chain, 2), 2);
});
