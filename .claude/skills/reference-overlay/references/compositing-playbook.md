# Compositing playbook: getting the rendered scene into the real video

## Muxing a silent graphic clip with real voiceover audio

The most natural way to insert a motion-graphics beat into a talking-head edit without it feeling like a
disconnected insert: keep the speaker's real audio running underneath, muted video swapped for the graphic.
Don't re-record or re-type the line as new on-screen text if she already said it — extract the matching slice
of her real audio track and mux it onto the silent rendered clip:

```bash
# 1. encode the PNG sequence (silent)
ffmpeg -y -framerate 24 -i frames/%04d.png -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p scene_silent.mp4

# 2. pull the matching slice of real voiceover from the source footage
ffmpeg -y -ss <start> -i source.mov -t <duration> -vn -af "afade=t=in:st=0:d=0.03" -c:a aac -b:a 192k -ar 48000 scene_audio.m4a

# 3. mux them together
ffmpeg -y -i scene_silent.mp4 -i scene_audio.m4a -c:v copy -c:a copy -map 0:v:0 -map 1:a:0 -shortest scene_final.mp4
```

Match the rendered scene's duration to the audio slice's duration up front (compute frame count from the
audio length, not the other way around) — trimming video after the fact to fit audio looks worse than
designing the animation to the actual timing from the start.

## Fake transparency: source clips with a checkerboard background

Any clip exported from a design tool "for compositing" that shows a checkerboard pattern behind the subject is
almost always H.264 or a similarly alpha-incapable codec — **the checkerboard is baked into the pixels, it is
not real transparency**. Trying to key it out reliably (chroma-key on a checkerboard, not a solid color) is
fragile and not worth the effort. Two better options, in order of preference:

1. **Ask if a real-alpha version exists** (ProRes 4444 `.mov`, or WebM with VP9 alpha) — if so, use that
   instead and skip everything below.
2. **If not, crop tight and re-composite on your own background.** The card/subject is often not axis-aligned
   (slight 3D tilt), so a rectangular crop will leave slivers of checkerboard in the corners no matter how
   tight you crop. Don't chase pixel-perfect cropping — crop generously, scale the result down so it doesn't
   fill the frame (leaving real margin on all sides, not just top/bottom), and let it float on a plain black
   background matching the rest of the video. At a small enough scale the residual checkerboard corners
   become imperceptible, and a floating card on black reads as an intentional design choice rather than a
   compositing error:

```bash
ffmpeg -y -i source_with_checkerboard.mp4 \
  -vf "crop=<w>:<h>:<x>:<y>,scale=800:-2,pad=1080:1920:(1080-iw)/2:(1920-ih)/2:black" \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p out.mp4
```

Find the crop rectangle by trial: grab a single frame as a PNG, test-crop it with a few candidate rectangles,
and look at the result before committing to the full-video ffmpeg pass.

## Two-tier accented captions (plain white text + one glowing accent phrase per cue)

Video-use's built-in `subtitles` filter / `build_master_srt()` burns a single global style — fine for uniform
captions, not capable of a differently-sized/colored accent word within the same line. Don't fight that
pipeline; author an `.ass` file directly and burn it with ffmpeg's `subtitles` filter, which supports full ASS
override tags.

```
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: White,Arial,54,&H00FFFFFF,&H000000FF,&H00303030,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,70,70,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:07.45,0:00:12.37,White,,0,0,0,,Обычный текст {\c&H00FFB24F&\3c&H00FFB24F&\blur3\b1\fs76}АКЦЕНТНОЕ СЛОВО{\r}, и снова обычный.
```

**ASS colours are `&HAABBGGRR` — blue-green-red byte order, not RGB.** To turn a CSS/design-reference hex like
`#4FB2FF` into the ASS value: split into `RR=4F GG=B2 BB=FF`, then write bytes in reverse: `&H00FFB24F`. Getting
this backwards is the single most common mistake here — the accent renders as the wrong color and it's not
obvious why until you remember the byte order.

`\blur3` is what gives the neon-glow look (libass gaussian-blurs the glyph edges); `\c` sets fill,
`\3c` sets outline color to match so the blur doesn't look like a mismatched halo. `{\r}` resets back to the
cue's base style for the rest of the line.

Burn it in exactly like a normal SRT:

```bash
ffmpeg -y -i base.mp4 -vf "subtitles=captions.ass" -c:a copy out.mp4
```

Compute each cue's on-screen timestamp from the word-level transcript JSON (faster-whisper's output — see
`patches/video-use/helpers/transcribe.py`), applying whatever constant offset accounts for trimmed lead-in and
any inserted graphic segments before that point in the final timeline. Keep that offset as a single named
constant in your caption-generation script — every structural edit to the timeline (adding/removing a segment
before the captioned section) only requires updating that one number, not re-deriving every cue's timestamp
by hand.
