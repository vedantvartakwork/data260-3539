#!/usr/bin/env node
/** Capture the real HW7 upload UI after running both 500-row acceptance cases. */

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
const page = await browser.newPage({ viewport: { width: 1600, height: 1400 } });
const cases = [
  ["membership_wins_500_rows.csv", "bike_membership_ui.png"],
  ["pay_per_use_wins_500_rows.csv", "bike_pay_ui.png"],
];
for (const [fixture, screenshot] of cases) {
  await page.goto("http://127.0.0.1:8839/hw7", { waitUntil: "networkidle" });
  await page.locator("input[type=file]").setInputFiles(
    path.join(root, "reports", "hw07", "fixtures", fixture),
  );
  await page.locator("input[type=url]").fill(
    "https://capitalbikeshare.com/pricing/30-day",
  );
  await page.getByRole("button", { name: "Run agent" }).click();
  await page.locator("#results h3").waitFor({ timeout: 60000 });
  await page.screenshot({
    path: path.join(root, "reports", "hw07", "screenshots", screenshot),
    fullPage: false,
  });
}
await browser.close();
