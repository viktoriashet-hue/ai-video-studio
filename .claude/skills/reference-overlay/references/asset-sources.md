# Asset sources: what actually works in this environment

The network policy here blocks several of the "default" icon/asset CDNs outright. Don't spend time retrying
a blocked host — switch to the raw-GitHub fallback immediately, it consistently works.

## Known blocked (403 at the proxy, confirmed this session)

- `cdn.jsdelivr.net`
- `api.iconify.design`
- `unpkg.com`

Don't retry these more than once per session — a 403 here is a policy decision, not a flaky network blip.
(General rule from the environment: never spam-retry a 403/407.)

## Known working: `raw.githubusercontent.com`

This host is consistently reachable and hosts the raw source of most icon libraries directly. Use it as the
default, not the fallback.

**Material Design Icons** (huge set, one file per icon, this is what covers "lock", "eye", "cookie",
"gesture-tap", etc.):
```
https://raw.githubusercontent.com/Templarian/MaterialDesign-SVG/master/svg/<icon-name>.svg
```
Icon names match the MDI catalog (e.g. `lock`, `eye-off`, `shield-check`, `delete-sweep`, `bell-ring`,
`magnify`, `map-marker`, `message-text`, `camera`, `cookie`, `apps`, `heart`, `gesture-tap`).

**Twemoji** (for literal emoji glyphs, e.g. a pointing finger):
```
https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/<codepoint>.svg
```
Codepoint is the lowercase hex Unicode codepoint, e.g. `1f447` for 👇. Look it up if unsure rather than guessing.

**Brand/company logos** (official glyph versions, not the full-color wordmark — usually what you want on a
dark background anyway):
```
https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/<slug>.svg
```
e.g. `instagram`, `tiktok`, `youtube`. These are monochrome by design — recolor via CSS `fill`.

## Batch downloads

Fetch several icons in parallel with backgrounded curls, then `wait`:

```bash
declare -A ICONS=(["lock"]="lock" ["eye"]="eye" ["cookie"]="cookie")
for name in "${!ICONS[@]}"; do
  curl -sS -f -o "${name}.svg" "https://raw.githubusercontent.com/Templarian/MaterialDesign-SVG/master/svg/${ICONS[$name]}.svg" &
done
wait
```

## Inlining into HTML

Fetch the raw SVG text and substitute it directly into the HTML (a placeholder token like `ICON_HEART` swapped
via Python/sed) rather than referencing external `<img src="...svg">` — Playwright will need to resolve the
path correctly either way, and inlining sidesteps that entirely plus lets you set `fill` via CSS on the
injected `<svg>`/`<path>` since there's no `<img>` tag boundary blocking style inheritance.

## Verify before trusting

Always render a quick PNG preview of a freshly downloaded/inlined icon before wiring it into the full scene —
`ffmpeg -i icon.svg -vf scale=256:256 preview.png` works fine since ffmpeg's SVG decode goes through librsvg.
Check the shape actually looks like what the filename claims; icon-set naming isn't always self-evident.
