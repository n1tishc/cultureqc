const assert = (await import("node:assert/strict")).default;
const ownsTask = typeof regressionSpaceId === "undefined";
const task = await taskSpace(ownsTask ? "cultureQC proof journey regression" : regressionSpaceId);
const page = task.page("p1");
const origin = "http://127.0.0.1:5173";
console.log({ spaceId: task.spaceId });

async function activate(selector) {
  await page.focus(selector);
  await page.keyboard.press("Enter");
}

for (const width of [1440, 390]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", { width, height: 1000, deviceScaleFactor: 1, mobile: width < 600 });
  await page.cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  await page.goto(`${origin}/`);
  await page.waitForSelector("a[href='/records#chain']");
  await activate("loc=role:button[name='Understand a review boundary']");
  const recordLink = "a[href='/records?record=evican_ht29#chain']";
  await page.waitForSelector(recordLink);
  assert.equal(await page.evaluate(() => document.activeElement.textContent), "Understand a review boundary");
  await activate(recordLink);
  await page.waitForSelector("#chain");
  await page.waitForFunction(() => document.querySelector("[aria-pressed='true']")?.textContent.includes("HT29"));
  await activate("text=Follow this exception into an illustrative review");
  await page.waitForFunction(() => document.querySelector("#review-example [role='status']")?.textContent.startsWith("Verified"));
  await activate("#review-example summary");
  assert.equal(await page.evaluate(() => document.querySelector("#review-example details").open), true);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  const review = await page.evaluate(() => JSON.parse(document.querySelector("#review-example pre").textContent));
  assert.equal(review.final_action, "human_review");
  assert.equal(review.host_signature_ref, null);
  await activate("text=Inspect the original HT29 reading");
  await page.waitForURL("**/records?record=evican_ht29#chain");
  assert.match(await page.evaluate(() => document.querySelector("[aria-pressed='true']").textContent), /HT29/);
  await activate("text=Return to this reading");
  await page.waitForSelector(recordLink);
  await activate("a[href='/records#chain']");
  await page.waitForSelector("#chain");
  await page.goto(`${origin}/validation#dense`);
  await page.waitForSelector("#dense");
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  console.log(`PASS ${width}px: keyboard sample, exact record, illustrative review, original return, chain CTA, evidence discovery and no page overflow`);
}

for (const hash of ["records", "chain"]) {
  await page.goto(`${origin}/#${hash}`);
  await page.waitForURL("**/records#chain");
  await page.waitForSelector("#chain");
  await page.goto(`${origin}/`);
  await page.waitForSelector("a[href='/records#chain']");
  await page.evaluate((value) => { location.hash = value; }, hash);
  await page.waitForURL("**/records#chain");
  await page.waitForSelector("#chain");
}
console.log("PASS both legacy fragments: direct navigation and already-loaded homepage hash changes");
console.log(await page.snapshot());
if (ownsTask) await task.finish({ keep: [] });
