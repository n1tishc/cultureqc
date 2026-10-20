import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { verifyReviewDemo } from "../src/lib/review-verification.js";
import { sha256 } from "../src/lib/verify.js";

const examples = JSON.parse(readFileSync(new URL("../src/data.json", import.meta.url))).examples;

test("illustrative review verifies without changing the historical chain", async () => {
  const before = JSON.stringify(examples);
  assert.deepEqual(await verifyReviewDemo(examples), { ok: true, count: 10 });
  assert.equal(JSON.stringify(examples), before);
  assert.equal(examples.chain_order.length, 9);
});

test("review edits, broken links and either mismatched checkpoint fail closed", async () => {
  for (const field of ["reason", "prev_record_hash", "reviews_record_hash", "reviews_record_id"]) {
    const copy = structuredClone(examples);
    const event = JSON.parse(copy.review_demo.record.canonical);
    event[field] = "changed";
    copy.review_demo.record.canonical = JSON.stringify(event);
    assert.equal((await verifyReviewDemo(copy)).ok, false, field);
  }
  for (const target of ["original", "extension"]) {
    const copy = structuredClone(examples);
    const checkpoint = target === "original" ? copy.checkpoint : copy.review_demo.checkpoint;
    checkpoint.head_hash = "0".repeat(64);
    assert.equal((await verifyReviewDemo(copy)).ok, false, target);
  }
});

test("even a rehashed review must reference the exact reading ID and hash", async () => {
  for (const field of ["reviews_record_hash", "reviews_record_id", "record_type"]) {
    const copy = structuredClone(examples);
    const event = JSON.parse(copy.review_demo.record.canonical);
    event[field] = "wrong";
    copy.review_demo.record.canonical = JSON.stringify(event);
    copy.review_demo.record.record_hash = await sha256(copy.review_demo.record.canonical);
    copy.review_demo.checkpoint.head_hash = copy.review_demo.record.record_hash;
    assert.equal((await verifyReviewDemo(copy)).ok, false, field);
  }
});

test("unlabelled, missing or truncated illustrative data cannot report success", async () => {
  const unlabelled = structuredClone(examples);
  unlabelled.review_demo.illustrative = false;
  assert.equal((await verifyReviewDemo(unlabelled)).ok, false);
  const missing = structuredClone(examples);
  delete missing.review_demo.record;
  await assert.rejects(verifyReviewDemo(missing));
  const truncated = structuredClone(examples);
  truncated.chain_order.pop();
  assert.equal((await verifyReviewDemo(truncated)).ok, false);
});
