/* SHA-256 and canonical JSON, in the browser.

   canonJSON must stay byte-identical to Python's
   json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True),
   because the page recomputes digests that culture/records.py produced. Any
   drift here shows up as a chain that fails to verify, which is the one thing
   this page cannot afford to get wrong. */

export const GENESIS = "0".repeat(64);

function hex(buf) {
  return [...new Uint8Array(buf)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function sha256(text) {
  return hex(
    await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)),
  );
}

export async function sha256Bytes(buf) {
  return hex(await crypto.subtle.digest("SHA-256", buf));
}

function jstr(s) {
  let o = '"';
  for (const ch of String(s)) {
    const c = ch.codePointAt(0);
    if (ch === '"') o += '\\"';
    else if (ch === "\\") o += "\\\\";
    else if (c === 8) o += "\\b";
    else if (c === 9) o += "\\t";
    else if (c === 10) o += "\\n";
    else if (c === 12) o += "\\f";
    else if (c === 13) o += "\\r";
    else if (c < 0x20) o += "\\u" + c.toString(16).padStart(4, "0");
    else if (c < 0x7f) o += ch;
    else if (c <= 0xffff) o += "\\u" + c.toString(16).padStart(4, "0");
    else {
      const x = c - 0x10000;
      o +=
        "\\u" +
        (0xd800 + (x >> 10)).toString(16).padStart(4, "0") +
        "\\u" +
        (0xdc00 + (x & 0x3ff)).toString(16).padStart(4, "0");
    }
  }
  return o + '"';
}

export function canonJSON(v) {
  if (v === null || v === undefined) return "null";
  const t = typeof v;
  if (t === "boolean") return v ? "true" : "false";
  if (t === "number") return String(v);
  if (t === "string") return jstr(v);
  if (Array.isArray(v)) return "[" + v.map(canonJSON).join(",") + "]";
  return (
    "{" +
    Object.keys(v)
      .sort()
      .map((k) => jstr(k) + ":" + canonJSON(v[k]))
      .join(",") +
    "}"
  );
}
