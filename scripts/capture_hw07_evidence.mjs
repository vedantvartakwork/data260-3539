#!/usr/bin/env node
/** Capture the compact evidence pages used in the HW7 report. */

import { createRequire } from "node:module";
import path from "node:path";
import process from "node:process";

const require = createRequire(import.meta.url);
const { chromium } = require(
  "/Users/vedantvartak/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright",
);

const root = process.cwd();
const browser = await chromium.launch({
  executablePath: "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
  headless: true,
});
const page = await browser.newPage({ viewport: { width: 1800, height: 1250 }, deviceScaleFactor: 1 });
const names = ["auth", "agent", "reflexion", "security", "files", "lint"];
for (const name of names) {
  const source = path.join(root, "reports", "hw07", "evidence_html", `${name}.html`);
  const destination = path.join(root, "reports", "hw07", "screenshots", `${name}.png`);
  await page.goto(`file://${source}`, { waitUntil: "load" });
  await page.screenshot({ path: destination, fullPage: true });
}
await browser.close();
