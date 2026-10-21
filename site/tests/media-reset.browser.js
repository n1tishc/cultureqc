const assert = (await import("node:assert/strict")).default;
const ownsTask = typeof regressionSpaceId === "undefined";
const task = await taskSpace(ownsTask ? "cultureQC media-reset regression" : regressionSpaceId);
console.log({ spaceId: task.spaceId });
const page = task.page("p1");
const origin = "http://127.0.0.1:5173";
const blocked = ["*evican_ht29.webp*", "*evican_ht29_contour.json*"];

async function reading() {
  return page.evaluate(() => ({
    record: document.querySelector(".guided-record a").getAttribute("href"),
    value: document.querySelector(".guided-numbers strong").textContent,
    image: document.querySelector(".stage-frame img").getAttribute("src"),
    layers: [...document.querySelector(".stage-frame").attributes].filter((attribute) => attribute.name.startsWith("data-")).map((attribute) => attribute.name),
    campaign: new URLSearchParams(location.search).get("campaign"),
    historyLength: history.length,
  }));
}

async function ready() {
  await page.waitForSelector(".stage-frame[data-contour]", { timeout: 10000 });
  await page.waitForSelector(".guided-media-error", { state: "detached", timeout: 10000 });
  await page.waitForSelector(".guided-media-status", { state: "detached", timeout: 10000 });
}

async function activate(name) {
  const selector = `loc=role:button[name="${name}"]`;
  await page.focus(selector);
  await page.press(selector, "Enter");
}

await page.cdp("Network.enable");
try {
  for (const recovery of ["Reset", "Understand a review boundary", "Retry media"]) {
    await page.cdp("Network.setBlockedURLs", { urls: blocked });
    await page.goto(`${origin}/?campaign=${encodeURIComponent(recovery)}`);
    await page.waitForSelector('.guided-media-error:has-text("Stored image, Cutoff contour")', { timeout: 10000 });
    const error = await page.evaluate(() => document.querySelector(".guided-media-error").textContent);
    assert.match(error, /Stored image/);
    assert.match(error, /Cutoff contour/);
    const failed = await reading();
    assert.equal(failed.value, "52.91%");
    assert.equal(failed.record, "/records?record=evican_ht29#chain");
    await page.cdp("Network.setBlockedURLs", { urls: [] });
    await activate(recovery);
    await ready();
    const recovered = await reading();
    assert.equal(recovered.value, failed.value);
    assert.equal(recovered.record, failed.record);
    assert.equal(recovered.historyLength, failed.historyLength);
    assert.equal(recovered.campaign, recovery);
    assert.deepEqual(recovered.layers, ["data-contour"]);
    assert.match(recovered.image, /retry=1$/);
    console.log(`PASS: initial media failures recover through ${recovery}`);
  }
  await activate("Raw image");
  assert.deepEqual((await reading()).layers, []);
  await activate("Reset");
  await ready();
  assert.deepEqual((await reading()).layers, ["data-contour"]);
  await activate("Measure coverage");
  await ready();
  assert.equal((await reading()).value, "39.41%");
  await activate("Reset");
  await ready();
  assert.equal((await reading()).value, "52.91%");
  assert.equal((await reading()).campaign, "Retry media");
  await page.evaluate(() => history.back());
  await page.waitForSelector('.guided-numbers strong:text-is("39.41%")', { timeout: 10000 });
  await ready();
  assert.equal((await reading()).record, "/records?record=c2c12_normal_20_40#chain");
  await page.evaluate(() => history.forward());
  await page.waitForSelector('.guided-numbers strong:text-is("52.91%")', { timeout: 10000 });
  await ready();
  console.log("PASS: normal reset, sample switch, query preservation and history");
} finally {
  await page.cdp("Network.setBlockedURLs", { urls: [] });
}
if (ownsTask) await task.finish({ keep: [] });
