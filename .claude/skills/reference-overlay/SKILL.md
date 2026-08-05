---
name: reference-overlay
description: Recreate a visual/motion overlay from a reference screenshot or video (someone else's Reels card, dashboard UI, sticker pack, title-card style, etc.) and composite it onto the user's real footage as a rendered animated scene. Use this whenever the user pastes or uploads a reference image/screenshot of a UI, card, sticker, or video style and asks to make "something like this," "наложение как на картинке," "в таком стиле," or to insert a similar element into their video — even if they don't say the word "skill" or "motion design" explicitly. Also use it any time a scene needs downloaded icons/logos/emoji composited with drawn geometry into a seek-safe animated clip (per the "не рисуй то, что можно скачать" rule), not just when a reference image is present.
---

# Reference Overlay

Turns a reference image (or a style already established via `references/motion-design-guide.md`) into a real
animated video clip, built from actually-downloaded assets, rendered deterministically, and composited onto
the user's footage. This is the exact workflow used to build the "твои личные данные" opener and the
neon-accent captions for the Instagram privacy video — it works, it's just tedious to reinvent each time.

This skill is the *mechanics*. For *what to draw vs what to download*, defer to CLAUDE.md's rule
("не рисуй то, что можно скачать") — don't restate it here, just follow it. For overall motion taste
(pacing, transitions, one-idea-per-beat), defer to `references/motion-design-guide.md` if the project has one.

## The four steps

1. **Decompose the reference** — list every element, split into СКАЧАТЬ (organic/detailed: faces, hands,
   logos, detailed icons) vs РИСОВАТЬ (primitives: cards, gradients, glow, type). This is CLAUDE.md's rule;
   just apply it. Show the split to the user before writing any code, same as always.
2. **Source the downloads** — see `references/asset-sources.md` for exactly which CDNs work and which don't
   in this environment, with working fallback hosts. Don't assume a CDN URL works; the network policy here
   blocks several of the "obvious" ones.
3. **Build the scene as HTML/CSS and render it deterministically** — see `references/rendering-playbook.md`.
   Plain CSS animations, Playwright screenshots, no timing guesswork.
4. **Composite onto the real footage** — see `references/compositing-playbook.md` for muxing graphics with
   real voiceover audio, handling fake-transparency (checkerboard) source clips, and burning two-tier
   accented captions.

## Why deterministic, frame-seeked rendering (not screen-recording the animation)

Recording a browser in real time is not repeatable: timing drifts, dropped frames happen, and you can't
re-grab a single frame to QC it without re-running the whole thing. Instead, pause every CSS animation and
step through time yourself:

```js
await page.evaluate(() => { document.getAnimations().forEach(a => a.pause()); });
// then per frame:
await page.evaluate((t) => { document.getAnimations().forEach(a => { a.currentTime = t; }); }, tMs);
await page.screenshot({ path: ... });
```

This is the same "single paused timeline, seek-safe" principle HyperFrames uses. The full runnable script is
`scripts/render_scene.js` — copy it, point it at your HTML file and duration, done. See
`references/rendering-playbook.md` for the reasoning and gotchas (especially the CSS-specificity bug below —
it will bite you if you skip it).

## The one bug you will hit: combined animations vs modifier classes

If you give elements a shared "idle drift" class separately from their per-element "fly to position" class
(e.g. `class="icon i1 settle"`), and both classes set `animation-name`, **whichever rule is lower in the
stylesheet wins for ALL of them** — equal specificity (two classes each) means source order decides, not which
one is "more specific" to that element. Every icon ends up drifting on icon-1's flight path.

Fix: don't split fly + idle into separate classes. Write them together on the same specific selector:

```css
.icon.i1 { animation: fly1 0.6s ease forwards, drift1 2.6s ease-in-out infinite alternate; animation-delay: 0.3s, 0.9s; }
.icon.i2 { animation: fly2 0.6s ease forwards, drift2 2.9s ease-in-out infinite alternate; animation-delay: 0.42s, 1.02s; }
```

Multi-value `animation` shorthand lets one element run two independent animations at once — that's the
mechanism you want, not a shared modifier class.

## Nothing may ever go fully static

If every element settles into a motionless end state, the scene reads as "not motion design" even though
it's technically animated — this is exactly what happened on the first pass of the Instagram video opener,
and the user called it out immediately. Every element that holds on screen for more than ~1s needs a small
`infinite alternate` animation running under it for the whole duration it's visible — a few px of drift, a
brightness pulse, anything. It costs nothing and it's the difference between "graphic" and "motion graphic."

## Quick reference

- Render script: `scripts/render_scene.js`
- Working CDN hosts + fallbacks: `references/asset-sources.md`
- Frame-seeked rendering details + the specificity bug in full: `references/rendering-playbook.md`
- Muxing graphics+VO audio, hiding fake-alpha checkerboard, two-tier ASS captions: `references/compositing-playbook.md`
