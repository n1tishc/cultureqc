const assert = (await import("node:assert/strict")).default;
const ownsTask = typeof regressionSpaceId === "undefined";
const task = await taskSpace(ownsTask ? "cultureQC accessibility regression" : regressionSpaceId);
const page = task.page("p1");
const origin = "http://127.0.0.1:5173";
console.log({ spaceId: task.spaceId });

function luminance(color) {
  const channels = color.match(/[\d.]+/g).slice(0, 3).map(Number).map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

function contrast(first, second) {
  const values = [luminance(first), luminance(second)].sort((left, right) => right - left);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

async function activate(selector, key = "Enter") {
  await page.focus(selector);
  await page.press(selector, key);
}

await page.goto(origin);
await page.waitForSelector('.verified[data-ok="true"]');
const tree = await page.cdp("Accessibility.getFullAXTree");
assert.equal(tree.nodes.filter((node) => !node.ignored && node.role?.value === "image" && node.name?.value === "Scale bar: 200 micrometres").length, 1);
const status = tree.nodes.find((node) => !node.ignored && node.role?.value === "status");
assert.ok(status?.properties.some((property) => property.name === "live" && property.value.value === "polite"));
assert.ok(status?.properties.some((property) => property.name === "atomic" && property.value.value === true));
const borders = await page.evaluate(() => [...document.querySelectorAll(".guided-view-controls button")].map((button) => {
  const style = getComputedStyle(button);
  return { label: button.textContent, width: style.borderTopWidth, style: style.borderTopStyle, color: style.borderTopColor, background: style.backgroundColor };
}));
for (const border of borders) {
  assert.equal(border.width, "1px");
  assert.equal(border.style, "solid");
  assert.ok(contrast(border.color, border.background) >= 3);
}
console.log("PASS: exposed physical scale, polite atomic verification status, contrasting view borders");

await activate('loc=role:button[name="Understand a review boundary"]');
await page.waitForSelector('.guided-numbers strong:text-is("52.91%")');
assert.equal(await page.evaluate(() => document.querySelectorAll(".guided-stage .scalebar").length), 0);
console.log("PASS: unknown-scale HT29 has no invented scale");

for (const width of [390, 320]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", { width, height: 844, deviceScaleFactor: 1, mobile: true });
  await page.goto(origin);
  await page.waitForSelector(".nav");
  const layout = await page.evaluate(() => ({ mask: getComputedStyle(document.querySelector(".nav")).maskImage, width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
  assert.equal(layout.mask, "none");
  assert.equal(layout.scrollWidth, layout.width);
}
console.log("PASS: 390px/320px navigation unmasked, no page overflow");

await page.cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
await page.goto(`${origin}/records?record=evican_ht29#chain`);
await page.waitForSelector('.chain .link[data-ok="true"]');
const switchColors = await page.evaluate(() => {
  const input = document.querySelector(".switch input");
  return { track: getComputedStyle(input).backgroundColor, thumb: getComputedStyle(input, "::after").backgroundColor, paper: getComputedStyle(document.body).backgroundColor };
});
assert.ok(contrast(switchColors.track, switchColors.paper) >= 3);
assert.ok(contrast(switchColors.thumb, switchColors.track) >= 3);
console.log("PASS: unchecked switch contrast", { track: contrast(switchColors.track, switchColors.paper), thumb: contrast(switchColors.thumb, switchColors.track) });

await page.evaluate(() => {
  window.v2ScrollCalls = [];
  window.v2OriginalScroll = Element.prototype.scrollTo;
  Element.prototype.scrollTo = function (options) {
    if (this.matches(".json")) window.v2ScrollCalls.push(options.behavior);
    return window.v2OriginalScroll.apply(this, arguments);
  };
});
try {
  for (const preference of ["reduce", "no-preference"]) {
    await page.cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: preference }] });
    await page.evaluate(() => { window.v2ScrollCalls = []; });
    await activate(".switch input >> nth=0", "Space");
    await page.waitForFunction(() => window.v2ScrollCalls.length > 0);
    assert.equal(await page.evaluate(() => window.v2ScrollCalls.at(-1)), preference === "reduce" ? "auto" : "smooth");
    assert.equal(await page.evaluate(() => document.activeElement.matches(".switch input")), true);
    await activate('loc=role:button[name="Reset local demonstration"]');
    await page.waitForFunction(() => document.querySelector(".verdicts").textContent.includes("All 9 of 9"));
  }
} finally {
  await page.evaluate(() => { Element.prototype.scrollTo = window.v2OriginalScroll; delete window.v2OriginalScroll; delete window.v2ScrollCalls; });
  await page.cdp("Emulation.setEmulatedMedia", { features: [] });
}
console.log("PASS: reduced-motion auto / normal smooth, keyboard focus preserved, tamper/reset unchanged");

const injection = await page.cdp("Page.addScriptToEvaluateOnNewDocument", {
  source: 'window.v2RejectVerification = null; Object.defineProperty(crypto.subtle, "digest", { configurable: true, value: () => new Promise((resolve, reject) => { window.v2RejectVerification = reject; }) });',
});
try {
  await page.goto(origin);
  await page.waitForSelector('.verified[data-ok="pending"]');
  await page.focus('loc=role:button[name="Raw image"]');
  await page.waitForFunction(() => !!window.v2RejectVerification);
  await page.evaluate(() => window.v2RejectVerification(new Error("Test verification unavailable")));
  await page.waitForSelector('.verified[data-ok="false"]');
  const result = await page.evaluate(() => ({ text: document.querySelector(".verified").textContent, status: document.querySelector(".verified").getAttribute("role"), focus: document.activeElement.textContent }));
  assert.match(result.text, /unavailable/i);
  assert.equal(result.status, "status");
  assert.equal(result.focus, "Raw image");
} finally {
  await page.cdp("Page.removeScriptToEvaluateOnNewDocument", { identifier: injection.identifier });
  await page.reload();
  assert.equal(await page.evaluate(() => "v2RejectVerification" in window), false, "Verification mock must not survive cleanup");
  await page.waitForSelector('.verified[data-ok="true"]');
}
console.log("PASS: delayed verification failure remains an honest status without moving focus");
console.log("PASS: cleanup removes the verification mock and restores real digest verification");
if (ownsTask) await task.finish({ keep: [] });
