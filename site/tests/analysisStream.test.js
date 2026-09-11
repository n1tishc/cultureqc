import test from "node:test";
import assert from "node:assert/strict";
import { readAnalysis } from "../src/lib/analysisStream.js";
function response(parts) {
  return new Response(
    new ReadableStream({
      start(c) {
        for (const p of parts) c.enqueue(new TextEncoder().encode(p));
        c.close();
      },
    }),
    { headers: { "content-type": "application/x-ndjson" } },
  );
}
test("handles fragmented stage and final records, ignoring heartbeats", async () => {
  const events = [];
  const result = await readAnalysis(
    response([
      '{"stage":"segmen',
      'tation","status":"running"}\n{"stage":"heartbeat"}\n',
      '{"stage":"result","result":{"value":42}}',
    ]),
    (e) => events.push(e),
  );
  assert.deepEqual(events, [{ stage: "segmentation", status: "running" }]);
  assert.deepEqual(result, { value: 42 });
});
test("rejects an interrupted stream instead of displaying a verdict", async () => {
  await assert.rejects(
    readAnalysis(response(['{"stage":"segmentation"}\n']), () => {}),
    /before the final record/,
  );
});
test("surfaces server errors and supports the legacy response contract", async () => {
  await assert.rejects(
    readAnalysis(
      response(['{"stage":"error","detail":"Model failed"}\n']),
      () => {},
    ),
    /Model failed/,
  );
  assert.deepEqual(await readAnalysis(Response.json({ value: 42 }), () => {}), {
    value: 42,
  });
});
