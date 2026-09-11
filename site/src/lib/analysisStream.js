/** Parse NDJSON across arbitrary network chunk boundaries; legacy JSON supported.
    `onAny`, if given, fires on every parsed line including heartbeats — the
    caller's stall detector needs those to tell a slow server from a dead one. */
export async function readAnalysis(response, onEvent, onAny) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw Error(body.detail || `HTTP ${response.status}`);
  }
  if (!response.headers.get("content-type")?.includes("ndjson"))
    return response.json();
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "",
    result;
  function line(value) {
    if (!value.trim()) return;
    const event = JSON.parse(value);
    onAny?.(event);
    if (event.stage === "error") throw Error(event.detail || "Analysis failed");
    if (event.stage === "result") result = event.result;
    else if (event.stage !== "heartbeat") onEvent(event);
  }
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary;
      while ((boundary = buffer.indexOf("\n")) >= 0) {
        line(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 1);
      }
      if (done) break;
    }
    line(buffer);
    if (!result)
      throw Error(
        "Connection ended before the final record. Retry this image.",
      );
    return result;
  } finally {
    reader.releaseLock();
  }
}
