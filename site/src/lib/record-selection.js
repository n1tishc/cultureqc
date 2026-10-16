export function recordIndexFromSearch(search, ids, fallbackIndex) {
  const id = new URLSearchParams(search).get("record");
  const index = ids.indexOf(id);
  return index === -1 ? fallbackIndex : index;
}

export function readingTargetIndex(index, chain, fallbackIndex) {
  return chain[index]?.kind === "change" ? fallbackIndex : index;
}

export function recordUrl(currentUrl, id) {
  const url = new URL(currentUrl);
  url.searchParams.set("record", id);
  return `${url.pathname}${url.search}#chain`;
}
