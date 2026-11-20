const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const readmeUrl = process.env.README_PREVIEW_URL;
const viewports = [
  { width: 390, height: 844 },
  { width: 1363, height: 936 },
];

async function checkPreview(browser, viewport, colorScheme) {
  const page = await browser.newPage({ viewport, colorScheme });
  try {
    const response = await page.goto(readmeUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    assert.equal(response.status(), 200, "The public GitHub preview did not load");
    const readme = page.locator("article.markdown-body");
    await readme.getByRole("heading", { name: "Quick start", exact: true }).waitFor();
    await readme.getByRole("heading", { name: "First tool call", exact: true }).waitFor();

    const images = readme.locator("img");
    assert.equal(await images.count(), 2);
    for (const image of await images.all()) {
      await image.scrollIntoViewIfNeeded();
      await image.evaluate(async (element) => element.decode());
      assert((await image.getAttribute("alt")).trim().length > 0);
    }
    const layout = await readme.evaluate((article) => {
      const boxes = (selector) => [...article.querySelectorAll(selector)]
        .map((element) => element.getBoundingClientRect());
      const start = boxes("h2")[0];
      return {
        color: getComputedStyle(article).color,
        quickStart: start.top + window.scrollY,
        firstImage: boxes("img")[0].top + window.scrollY,
        articleOverflow: article.scrollWidth - article.clientWidth,
        codeOverflow: [...article.querySelectorAll("pre")]
          .filter((code) => code.scrollWidth > code.clientWidth + 2).length,
      };
    });
    assert(layout.quickStart < layout.firstImage, "Artwork precedes the quick start");
    if (viewport.width >= 1000) {
      assert(layout.quickStart < viewport.height, "The desktop quick start is below the fold");
      assert.equal(layout.codeOverflow, 0, "Desktop code blocks overflow");
    }
    assert(layout.articleOverflow <= 2, "The README article overflows horizontally");
    console.log(`${viewport.width} × ${viewport.height}, ${colorScheme}: headings and both images render; code blocks with internal scroll: ${layout.codeOverflow}`);
    return layout.color;
  } finally {
    await page.close();
  }
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome" });
  try {
    for (const viewport of viewports) {
      const light = await checkPreview(browser, viewport, "light");
      const dark = await checkPreview(browser, viewport, "dark");
      assert.notEqual(light, dark, "GitHub did not apply distinct light and dark themes");
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
