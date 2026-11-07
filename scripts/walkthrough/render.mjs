// Renders walkthrough.html frame by frame with Playwright, then ffmpeg joins the frames.
// Run from scripts/ after `npm ci`, with ffmpeg on PATH:
//   node walkthrough/render.mjs preview 1 5 12     -> walkthrough/preview-<t>.png for each time
//   node walkthrough/render.mjs full <out-dir>      -> frames/*.png, walkthrough.mp4, walkthrough.gif
// The page is deterministic: every frame is `window.seek(t)` at t = frame / FPS.
import { chromium } from "playwright";
import { mkdirSync, copyFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const page_url = `file://${join(here, "walkthrough.html")}`;
copyFileSync(join(here, "..", "..", "docs", "assets", "pipeline-dark.svg"), join(here, "pipeline-dark.svg"));

const [mode, ...rest] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
await page.goto(page_url);
await page.waitForLoadState("networkidle");
const total = await page.evaluate(() => window.TOTAL);
const fps = await page.evaluate(() => window.FPS);

if (mode === "preview") {
  for (const t of rest.map(Number)) {
    await page.evaluate(t => window.seek(t), t);
    await page.screenshot({ path: join(here, `preview-${t}.png`) });
  }
} else {
  const out = rest[0];
  const frames = join(out, "frames");
  mkdirSync(frames, { recursive: true });
  const count = Math.round(total * fps);
  const started = Date.now();
  for (let i = 0; i < count; i++) {
    const path = join(frames, `f${String(i).padStart(5, "0")}.png`);
    if (existsSync(path)) continue;
    await page.evaluate(t => window.seek(t), i / fps);
    await page.screenshot({ path });
    if (i % 300 === 0) console.log(`frame ${i}/${count}, ${Math.round((Date.now() - started) / 1000)}s`);
  }
  console.log(`rendered ${count} frames (${total}s at ${fps} fps)`);
  const pattern = join(frames, "f%05d.png");
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(fps), "-i", pattern,
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", join(out, "walkthrough.mp4")]);
  // GIF: 12 fps, 960 px wide, one palette for the whole clip, Bayer dithering for small size.
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(fps), "-i", pattern,
    "-vf", "fps=12,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
    "-loop", "0", join(out, "walkthrough.gif")]);
  console.log("wrote walkthrough.mp4 and walkthrough.gif");
}
await browser.close();
