const assert = (await import("node:assert/strict")).default;
const ownsTask = typeof regressionSpaceId === "undefined";
const task = await taskSpace(ownsTask ? "cultureQC evidence regression" : regressionSpaceId);
const page = task.page("p1");
const origin = "http://127.0.0.1:5173";
console.log({ spaceId: task.spaceId });

await page.goto(`${origin}/validation`);
await page.waitForSelector("#dense");
const opening = await page.evaluate(() => ({
  highlights: document.querySelector(".glance").innerText,
  catalogue: document.querySelector('[aria-label="Validation checks V1 to V10"]') !== null,
  sections: [...document.querySelectorAll("main section[id]")].map((section) => section.id),
  limits: document.querySelector("#detectability").innerText,
  legacy: document.getElementById("checks").contains(document.getElementById("detectability")),
}));
assert.match(opening.highlights, /7\.61 → 2\.22 pp/);
assert.match(opening.highlights, /71% lower mean error/);
assert.match(opening.highlights, /not a v2 release benchmark/);
assert.match(opening.highlights, /9 linked records/);
assert.equal(opening.catalogue, false);
assert.ok(opening.sections.indexOf("dense") < opening.sections.indexOf("profiles"));
assert.match(opening.limits, /realistic-scale simulated bacterial contamination was not detected/);
assert.match(opening.limits, /0 of 2 simulated growth stalls/);
assert.equal(opening.legacy, true);

for (const summary of ["Full criteria and split-by-split results", "Full detection scope and supporting experiments"]) {
  const selector = `summary:text-is("${summary}")`;
  const isOpen = () => page.evaluate((text) => [...document.querySelectorAll("summary")].find((element) => element.textContent === text).parentElement.open, summary);
  assert.equal(await isOpen(), false);
  await page.focus(selector);
  await page.keyboard.press("Enter");
  assert.equal(await isOpen(), true);
  assert.equal(await page.evaluate((text) => document.activeElement.textContent === text, summary), true);
  if (summary.startsWith("Full criteria")) {
    assert.match(await page.evaluate(() => document.querySelector('[aria-label="Pre-registered criteria for the shipped and fine-tuned readings"]').innerText), /fail/);
  } else {
    assert.equal(await page.evaluate(() => document.querySelector('[aria-label="Detectability matrix"] tbody').rows.length), 7);
  }
  await page.keyboard.press("Enter");
  assert.equal(await isOpen(), false);
}
console.log("PASS: measured gains, audit link, preserved adverse evidence and keyboard disclosure");

try {
  for (const width of [1280, 390]) {
    await page.cdp("Emulation.setDeviceMetricsOverride", { width, height: 844, deviceScaleFactor: 1, mobile: width < 600 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth === innerWidth), true);
  }
} finally {
  await page.cdp("Emulation.clearDeviceMetricsOverride");
}
await page.goto(`${origin}/validation#checks`);
await page.waitForSelector("#checks #detectability");
await page.goto(`${origin}/records#chain`);
await page.waitForFunction(() => document.querySelector(".verdicts")?.textContent.includes("All 9 of 9"));
console.log("PASS: desktop/mobile document width, legacy anchor and verified record chain");
if (ownsTask) await task.finish({ keep: [] });
