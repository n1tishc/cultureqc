import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { verifyChain } from "../src/lib/verify.js";

const data = JSON.parse(readFileSync(new URL("../src/data.json", import.meta.url)));
// The stored chain: the approved profile changes first, then the readings.
const byId = Object.fromEntries(
  [...data.examples.items, ...(data.examples.changes || [])].map((e) => [e.id, e.record]),
);
const chain = data.examples.chain_order.map((id) => byId[id]);

test("every exported record re-hashes to its stored SHA-256 and links to the one before", async () => {
  const res = await verifyChain(chain);
  assert.equal(res.length, data.examples.items.length + (data.examples.changes || []).length);
  assert.equal(res.length, data.examples.checkpoint.count);
  res.forEach((r, i) => assert.ok(r.ok, `record ${i + 1}: hash ${r.hashOk} link ${r.linkOk}`));
});

test("changing one reading breaks that record and the link after it", async () => {
  const k = data.examples.chain_order.indexOf("c2c12_normal_40_100");
  const tampered = chain.map((r) => ({ ...r }));
  tampered[k].canonical = tampered[k].canonical.replace(/"confluency_pct":[\d.]+/, '"confluency_pct":61.42');
  assert.notEqual(tampered[k].canonical, chain[k].canonical);
  const res = await verifyChain(tampered);
  for (let i = 0; i < k; i++) assert.ok(res[i].ok, `record ${i + 1}`);
  assert.equal(res[k].hashOk, false);
  assert.equal(res[k + 1].linkOk, false);
});
