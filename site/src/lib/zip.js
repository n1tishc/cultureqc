/* Reading a ZIP in the browser with no library.

   DecompressionStream("deflate-raw") is what makes this possible — the central
   directory is parsed by hand and each entry is inflated by the platform. The
   alternative was shipping a zip library to do what the browser already does. */

async function inflateRaw(u8) {
  const stream = new Blob([u8])
    .stream()
    .pipeThrough(new DecompressionStream("deflate-raw"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

export async function readZip(file) {
  const buf = await file.arrayBuffer();
  const dv = new DataView(buf);
  let eocd = -1;
  const floor = Math.max(0, buf.byteLength - 66000);
  for (let i = buf.byteLength - 22; i >= floor; i--) {
    if (dv.getUint32(i, true) === 0x06054b50) {
      eocd = i;
      break;
    }
  }
  if (eocd < 0)
    throw new Error("not a readable ZIP — no end-of-central-directory record");
  const n = dv.getUint16(eocd + 10, true);
  let off = dv.getUint32(eocd + 16, true);
  if (off === 0xffffffff)
    throw new Error("ZIP64 archives are not supported here — unzip it first");

  const entries = [];
  for (let k = 0; k < n && off + 46 <= buf.byteLength; k++) {
    if (dv.getUint32(off, true) !== 0x02014b50) break;
    const method = dv.getUint16(off + 10, true);
    const csize = dv.getUint32(off + 20, true);
    const nameLen = dv.getUint16(off + 28, true);
    const extraLen = dv.getUint16(off + 30, true);
    const cmtLen = dv.getUint16(off + 32, true);
    const lho = dv.getUint32(off + 42, true);
    const name = new TextDecoder().decode(
      new Uint8Array(buf, off + 46, nameLen),
    );
    off += 46 + nameLen + extraLen + cmtLen;

    const base = name.split("/").pop();
    if (
      name.endsWith("/") ||
      name.startsWith("__MACOSX/") ||
      base.startsWith("._") ||
      !base
    )
      continue;
    if (!/\.(png|jpe?g|tiff?|bmp|webp)$/i.test(base)) continue;

    const lnLen = dv.getUint16(lho + 26, true);
    const leLen = dv.getUint16(lho + 28, true);
    const start = lho + 30 + lnLen + leLen;
    if (start + csize > buf.byteLength) continue;
    const raw = new Uint8Array(buf.slice(start, start + csize));
    let bytes;
    if (method === 0) bytes = raw;
    else if (method === 8) bytes = await inflateRaw(raw);
    else continue;
    entries.push(new File([bytes], base, { type: "" }));
  }
  if (!entries.length) throw new Error("no readable images inside that ZIP");
  return entries;
}
