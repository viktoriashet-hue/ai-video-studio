# Rendering playbook: HTML/CSS scene → deterministic PNG sequence → video

## Why not GSAP / a CDN animation library

The default instinct is to reach for GSAP (it's what HyperFrames itself uses). Don't, for this workflow:
GSAP's CDN (`cdn.jsdelivr.net` and friends) is blocked here, and pulling it in as an npm dependency just to
animate a single short scene is a lot of setup for no real benefit. Plain CSS `@keyframes` + `animation` does
everything a 2-5 second overlay scene needs: entrance eases, staggered delays, infinite idle loops. Save GSAP
for when you're actually inside a HyperFrames composition project.

## The render loop

`scripts/render_scene.js` implements this; read it before writing your own version. The core idea:

1. Load the HTML page in headless Chromium (`/opt/pw-browsers/chromium`, pre-installed — never run
   `playwright install`, it'll try to download and fail/waste time).
2. `document.getAnimations().forEach(a => a.pause())` — freezes every running CSS animation at once.
3. For each output frame, compute its timestamp in ms, set `a.currentTime = t` on every animation, then
   `page.screenshot()`.
4. Stitch the PNG sequence into a video with `ffmpeg -framerate <fps> -i %04d.png ...`.

This is slower than a real-time screen recording but it is *exactly* reproducible — you can re-grab frame
0170 six times and get pixel-identical output, which matters when you're QC-ing timing against a voiceover
track frame-by-frame.

## Setting up Playwright if it's not already installed

```bash
mkdir -p /tmp/scratch/render_tools && cd /tmp/scratch/render_tools
npm init -y
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install playwright
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node render_scene.js scene.html out_frames/ 3.0
```

The `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` on install and `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers` on run are
both required — without them npm tries to fetch its own Chromium build, which is slow and sometimes blocked.

## The CSS-specificity trap (read this before writing multi-icon scenes)

If several elements need both a one-time entrance animation (fly to position) AND a continuous idle animation
(gentle drift, so nothing goes fully static — see SKILL.md), the natural instinct is two classes:

```html
<div class="icon i1 settle">...</div>
<div class="icon i2 settle">...</div>
```

```css
.icon.i1 { animation: fly1 0.6s ease forwards; animation-delay: 0.3s; }
.icon.i2 { animation: fly2 0.6s ease forwards; animation-delay: 0.42s; }
.icon.settle { animation-name: fly1, drift; animation-duration: 0.6s, 2.4s; animation-iteration-count: 1, infinite; }
```

**This is broken.** `.icon.i1` and `.icon.settle` both have specificity (0,2,0) — two classes each. Equal
specificity means the rule that appears *later in the stylesheet* wins, for every property it sets, on every
element that matches both selectors. Since `.icon.settle` comes after `.icon.i1`...`.icon.i5` in source order,
**every icon ends up using `fly1`'s trajectory**, not its own — they all cluster in the same spot instead of
spreading out. This is subtle because nothing errors; you just get visually wrong output that looks plausible
at a glance.

The fix: don't factor the idle animation into a shared modifier class. Write both animations directly on each
specific selector, using the multi-value `animation` shorthand (comma-separated values apply positionally to
each animation-name):

```css
.icon.i1 { animation: fly1 0.6s ease forwards, drift1 2.6s ease-in-out infinite alternate; animation-delay: 0.3s, 0.9s; }
.icon.i2 { animation: fly2 0.6s ease forwards, drift2 2.9s ease-in-out infinite alternate; animation-delay: 0.42s, 1.02s; }
```

Give each icon its own `driftN` keyframe (even if they're all just "bob up 12-18px") with a slightly different
duration per icon — identical timing across elements reads as mechanical; a few hundred ms of variance per
icon reads as organic.

## Seeking a still frame to QC

Once frames are rendered, spot-check a handful before encoding to video — cheaper to catch a layout bug at
frame 50 than after burning captions onto a 60s composite. Read a couple of PNGs directly (mid-entrance,
mid-hold, near the end) rather than only checking frame 0.
