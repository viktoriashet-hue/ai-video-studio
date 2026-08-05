// Deterministic, frame-seeked render of an HTML/CSS animation to a PNG sequence.
// Usage: node render_scene.js <scene.html> <out_dir> <duration_seconds> [fps] [width] [height]
//
// Requires the pre-installed Chromium in this environment:
//   PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node render_scene.js ...
// If playwright isn't installed yet in your scratch dir:
//   npm init -y && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install playwright

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const [, , htmlPath, outDir, durationArg, fpsArg, widthArg, heightArg] = process.argv;

if (!htmlPath || !outDir || !durationArg) {
  console.error('Usage: node render_scene.js <scene.html> <out_dir> <duration_seconds> [fps=24] [width=1080] [height=1920]');
  process.exit(1);
}

const DURATION_S = parseFloat(durationArg);
const FPS = fpsArg ? parseInt(fpsArg, 10) : 24;
const WIDTH = widthArg ? parseInt(widthArg, 10) : 1080;
const HEIGHT = heightArg ? parseInt(heightArg, 10) : 1920;

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT } });
  await page.goto('file://' + path.resolve(htmlPath));

  // Pause every CSS animation on the page so we can seek deterministically.
  // Without this, timing depends on how fast the machine renders each screenshot.
  await page.evaluate(() => {
    document.getAnimations().forEach(a => a.pause());
  });

  const totalFrames = Math.round(DURATION_S * FPS);
  for (let f = 0; f < totalFrames; f++) {
    const tMs = (f / FPS) * 1000;
    await page.evaluate((t) => {
      document.getAnimations().forEach(a => { a.currentTime = t; });
    }, tMs);
    const frameName = String(f).padStart(4, '0') + '.png';
    await page.screenshot({ path: path.join(outDir, frameName) });
  }

  await browser.close();
  console.log(`rendered ${totalFrames} frames (${DURATION_S}s @ ${FPS}fps) to ${outDir}`);
})();

// After this, encode with:
//   ffmpeg -y -framerate <fps> -i <out_dir>/%04d.png -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p scene.mp4
// This produces a SILENT video -- mux in audio separately (see references/compositing-playbook.md).
