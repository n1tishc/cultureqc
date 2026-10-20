const assert = (await import("node:assert/strict")).default;
const ownsTask = typeof pointerRegressionSpaceId === "undefined";
const task = await taskSpace(ownsTask ? "cultureQC proof pointer regression" : pointerRegressionSpaceId);
const page = task.page("p1");
const origin = "http://127.0.0.1:5173";
console.log({ spaceId: task.spaceId });

for (const width of [1440, 390]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", { width, height: 1000, deviceScaleFactor: 1, mobile: width < 600 });
  await page.cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  await page.goto(`${origin}/`);
  await page.waitForSelector("a[href='/records#chain']");
  assert.equal(await page.evaluate(() => innerWidth), width);
  await page.click("loc=role:button[name='Understand a review boundary']", { label: "Choose review boundary sample" });
  const recordLink = "a[href='/records?record=evican_ht29#chain']";
  await page.waitForSelector(recordLink);
  await page.click(recordLink, { label: "Inspect exact stored record" });
  await page.waitForFunction(() => document.querySelector("[aria-pressed='true']")?.textContent.includes("HT29"));
  await page.click('text="Follow this exception into an illustrative review"', { label: "Follow illustrative review flow" });
  await page.waitForFunction(() => document.querySelector("#review-example [role='status']")?.textContent.startsWith("Verified"));
  await page.click("#review-example summary", { label: "Expand illustrative review JSON" });
  const expanded = await page.evaluate(() => {
    const section = document.querySelector("#review-example");
    const pane = section.querySelector("pre");
    return {
      open: section.querySelector("details").open,
      pageOverflow: document.documentElement.scrollWidth > innerWidth,
      paneOverflow: getComputedStyle(pane).overflowX,
      paneWidth: pane.getBoundingClientRect().width,
      review: JSON.parse(pane.textContent),
      disclosure: section.textContent.includes("not a real review, signature or approval"),
    };
  });
  assert.equal(expanded.open, true);
  assert.equal(expanded.pageOverflow, false);
  assert.ok(expanded.paneWidth <= width);
  assert.equal(expanded.paneOverflow, "auto");
  assert.equal(expanded.disclosure, true);
  assert.equal(expanded.review.final_action, "human_review");
  assert.equal(expanded.review.host_signature_ref, null);
  await page.click("#review-example summary", { label: "Collapse illustrative review JSON" });
  assert.equal(await page.evaluate(() => document.querySelector("#review-example details").open), false);
  await page.click('text="Inspect the original HT29 reading"', { label: "Return to original reading" });
  await page.waitForURL("**/records?record=evican_ht29#chain");
  assert.match(await page.evaluate(() => document.querySelector("[aria-pressed='true']").textContent), /HT29/);
  await page.click('text="Return to this reading"', { label: "Return to homepage sample" });
  await page.waitForSelector(recordLink);
  await page.click("a[href='/records#chain']", { label: "Open chain with automatic scrolling" });
  await page.waitForURL("**/records#chain");
  await page.waitForSelector("#chain");
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  console.log(`PASS ${width}px: pointer sample selection, exact-record navigation, illustrative review expand/collapse, original return, sample return, generic chain CTA and contained JSON overflow`);
}

console.log("All navigation uses selector-based pointer clicks with browser automatic scrolling; no explicit-scroll workaround.");
console.log("Pointer and DOM geometry checks only: not screenshot-based visual acceptance, physical touch, screen-reader or actual 200% zoom verification.");
if (ownsTask) await task.finish({ keep: [] });
