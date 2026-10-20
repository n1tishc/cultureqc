import { checkCheckpoint, verifyChain } from "./verify.js";

export async function verifyReviewDemo(examples) {
  const demo = examples.review_demo;
  const byId = Object.fromEntries([...examples.items, ...examples.changes].map((item) => [item.id, item.record]));
  const reading = byId[demo.reading_id];
  const body = JSON.parse(demo.record.canonical);
  const original = examples.chain_order.map((id) => byId[id]);
  const results = await verifyChain([...original, demo.record]);
  const linked = body.reviews_record_hash === reading.record_hash
    && body.reviews_record_id === JSON.parse(reading.canonical).record_id;
  return {
    ok: demo.illustrative === true && body.record_type === "review" && linked
      && results.every((result) => result.ok)
      && checkCheckpoint(results.slice(0, original.length), examples.checkpoint).ok
      && checkCheckpoint(results, demo.checkpoint).ok,
    count: results.length,
  };
}
