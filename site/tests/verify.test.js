import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { verifyChain } from "../src/lib/verify.js";

const data = JSON.parse(readFileSync(new URL("../src/data.json", import.meta.url)));
const byId = Object.fromEntries(data.examples.items.map((e) => [e.id, e.record]));
const chain = data.examples.chain_order.map((id) => byId[id]);

test("every exported record re-hashes to its stored SHA-256 and links to the one before", async () => {
  const res = await verifyChain(chain);
  assert.equal(res.length, 7);
  res.forEach((r, i) => assert.ok(r.ok, `record ${i + 1}: hash ${r.hashOk} link ${r.linkOk}`));
});

test("changing one reading breaks that record and the link after it", async () => {
  const tampered = chain.map((r) => ({ ...r }));
  tampered[2].canonical = tampered[2].canonical.replace('"confluency_pct":51.42', '"confluency_pct":61.42');
  assert.notEqual(tampered[2].canonical, chain[2].canonical);
  const res = await verifyChain(tampered);
  assert.ok(res[0].ok && res[1].ok);
  assert.equal(res[2].hashOk, false);
});
