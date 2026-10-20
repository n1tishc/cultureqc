const assert = (await import("node:assert/strict")).default;
const ownsTask = typeof regressionSpaceId === "undefined";
const task = await taskSpace(ownsTask ? "cultureQC technical controls regression" : regressionSpaceId);
const page = task.page("p1");
console.log({ spaceId: task.spaceId });

const groups = [
  {
    path: "/#timeline",
    selector: '.tabs[aria-label="Replayed flasks"]',
    names: ["Normal flask A", "Normal flask B", "Contamination", "Growth stall", "Lamp dimming"],
    output: ".tl-chart svg",
  },
  {
    path: "/validation#dense",
    selector: '.seg-tabs[aria-label="Imaging setup"]',
    names: ["lsm_2796", "lsm_hek_1024", "cd7_huvec_dic", "oir_1024"],
    output: ".ft-pair",
  },
];

await page.cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
try {
  for (const group of groups) {
    await page.goto(`http://127.0.0.1:5173${group.path}`);
    await page.waitForSelector(`${group.selector} button`);
    assert.equal(await page.evaluate((selector) => document.querySelector(selector).getAttribute("role"), group.selector), "group");
    const buttons = `${group.selector} button`;
    await page.focus(`${buttons} >> nth=0`);
    for (let index = 0; index < group.names.length; index++) {
      console.log(`Checking ${group.names[index]}`);
      if (index > 0) await page.keyboard.press("Tab");
      assert.equal(await page.evaluate((selector) => document.activeElement === document.querySelectorAll(selector)[0], `${buttons}:nth-child(${index + 1})`), true);
      await page.keyboard.press(index % 2 ? "Space" : "Enter");
      await page.waitForFunction(({ selector, index }) => document.querySelectorAll(`${selector} button`)[index]?.getAttribute("aria-pressed") === "true", { selector: group.selector, index });
      const state = await page.evaluate(({ selector, output }) => {
        const controls = [...document.querySelectorAll(`${selector} button`)];
        const selected = controls.find((button) => button.getAttribute("aria-pressed") === "true");
        const style = getComputedStyle(selected);
        return {
          pressed: controls.filter((button) => button.getAttribute("aria-pressed") === "true").length,
          native: controls.every((button) => !button.hasAttribute("role") && !button.hasAttribute("aria-selected") && button.tabIndex === 0),
          focused: document.activeElement === selected,
          visibleFocus: selected.matches(":focus-visible") && style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0,
          selectedBackground: style.backgroundColor,
          otherBackground: getComputedStyle(controls.find((button) => button !== selected)).backgroundColor,
          output: document.querySelector(output)?.getAttribute("aria-label"),
          images: [...document.querySelectorAll(`${output} img`)].map((image) => image.alt),
        };
      }, group);
      assert.equal(state.pressed, 1);
      assert.equal(state.native, true);
      assert.equal(state.focused, true);
      assert.equal(state.visibleFocus, true);
      assert.notEqual(state.selectedBackground, state.otherBackground);
      assert.ok(state.output.includes(group.names[index]));
      for (const description of state.images) assert.ok(description.includes(group.names[index]));
      await page.keyboard.press("Enter");
      assert.equal(await page.evaluate((selector) => document.querySelectorAll(`${selector} button[aria-pressed="true"]`).length, group.selector), 1);
    }
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate((selector) => document.querySelector(selector).contains(document.activeElement), group.selector), false);
    await page.keyboard.press("Shift+Tab");
    assert.equal(await page.evaluate((selector) => document.activeElement === document.querySelector(`${selector} button:last-child`), group.selector), true);
    if (group.output === ".tl-chart svg") {
      await page.focus(".visits button >> nth=0");
      await page.keyboard.press("Enter");
      await page.focus(`${buttons} >> nth=4`);
      await page.keyboard.press("Enter");
      assert.equal(await page.evaluate(() => document.querySelector('.visits button').getAttribute("aria-pressed")), "true");
      console.log("PASS: reactivating the selected flask preserves the chosen visit");
    }
    console.log(`PASS: ${group.selector}: all options, Tab order, Enter/Space, pressed styling, focus and output`);
  }
} finally {
  await page.cdp("Emulation.setEmulatedMedia", { features: [] });
}

if (ownsTask) await task.finish({ keep: [] });
