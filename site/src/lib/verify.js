/* Re-verify the chained records in the browser.

   Each record ships as the exact canonical JSON string culture/records.py
   hashed (site/assets/build_data.py checks that on export), so the page
   re-hashes those bytes rather than re-serializing numbers itself: Python
   writes 80.0 where JavaScript would write 80, and one differing byte would
   read as a broken chain. */

export const GENESIS = "0".repeat(64);

export async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/* records: [{canonical, record_hash}] in chain order.
   Returns one result per record: the recomputed hash, whether it matches the
   stored one, and whether prev_record_hash equals the hash recomputed for the record
   before it, so an edit breaks that record and the link after it. */
export async function verifyChain(records) {
  const out = [];
  let prev = GENESIS;
  for (const r of records) {
    const computed = await sha256(r.canonical);
    const body = JSON.parse(r.canonical);
    const hashOk = computed === r.record_hash;
    const linkOk = body.prev_record_hash === prev;
    out.push({ computed, hashOk, linkOk, ok: hashOk && linkOk });
    prev = computed;
  }
  return out;
}

/* Check verifyChain's results against an anchored checkpoint
   (culture/records.py checkpoint(): the record count and head hash, stored
   outside the log). Fewer records than it counted is a deleted tail; a record
   at its count that no longer hashes to its head is a rewrite. The same two
   rules as culture.records.verify_chain(checkpoint=...). */
export function checkCheckpoint(results, cp) {
  if (results.length < cp.count) return { ok: false, status: "truncated" };
  if (results[cp.count - 1].computed !== cp.head_hash) return { ok: false, status: "rewritten" };
  return { ok: true, status: "intact" };
}

export function verificationMessage(results, checkpoint) {
  const matching = results.filter((result) => result.ok).length;
  const chainMatches = matching === results.length;
  const checkpointMatches = checkCheckpoint(results, checkpoint).ok;
  if (chainMatches && checkpointMatches) {
    return `All ${matching} of ${results.length} records re-hash to their stored SHA-256 and link to the one before, and the chain matches the checkpoint: ${checkpoint.count} records, head ${checkpoint.head_hash.slice(0, 8)}…`;
  }
  if (!chainMatches) {
    return `Verification failed: ${results.length - matching} of ${results.length} records have a hash or link mismatch. Do not rely on this chain; inspect the failed records and their source artifacts.`;
  }
  return "The records link together, but the chain does not match the anchored checkpoint. It may have been rewritten or truncated; do not treat it as the verified stored chain.";
}

/* What someone with write access to the whole log can do: edit record k
   (0-based), then recompute its hash and every later prev_record_hash and
   record_hash so each link checks out again. */
export async function rewriteFrom(records, k, edit) {
  const out = records.slice(0, k);
  let prev = k > 0 ? records[k - 1].record_hash : GENESIS;
  for (let i = k; i < records.length; i++) {
    let canonical = i === k ? edit(records[i].canonical) : records[i].canonical;
    canonical = canonical.replace(/"prev_record_hash":"[0-9a-f]{64}"/, `"prev_record_hash":"${prev}"`);
    const record_hash = await sha256(canonical);
    out.push({ ...records[i], canonical, record_hash });
    prev = record_hash;
  }
  return out;
}
