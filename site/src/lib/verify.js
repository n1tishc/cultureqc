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
