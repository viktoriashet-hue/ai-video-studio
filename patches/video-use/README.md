# video-use patch: local faster-whisper instead of ElevenLabs Scribe

`video-use` ([browser-use/video-use](https://github.com/browser-use/video-use)) lives
**outside** this repo — it's cloned to `~/Developer/video-use` and symlinked into
`~/.claude/skills/video-use` per `CLAUDE.md`. That means any edits made directly on the
clone are lost whenever the environment is rebuilt from a fresh `git clone`.

`video-use` ships hardcoded to ElevenLabs Scribe for transcription (`helpers/transcribe.py`
calls the Scribe REST API directly) with **no pluggable transcriber hook** — its own
`SKILL.md` even listed local Whisper as an anti-pattern ("Slow and it normalizes fillers.
Use hosted Scribe."). Since there's nothing to plug into, this directory vendors a patched
copy of the affected files so the swap to local `faster-whisper` (model `medium`, language
`ru`, no API key, no per-call cost) survives environment resets.

## What's patched

| File | Change |
|---|---|
| `helpers/transcribe.py` | Scribe HTTP call → local `faster-whisper` call. Same output JSON shape (`words: [{type, text, start, end, speaker_id}]`) so `pack_transcripts.py` needs no changes. `vad_filter=False` so short filler words ("эм", "ну", "вот") aren't swallowed by VAD before the edit pipeline can find and cut them. No diarization (faster-whisper doesn't do it) — `speaker_id` is always `null`. |
| `helpers/transcribe_batch.py` | Same backend swap; preloads the model once before spinning up the worker pool instead of loading an API key. |
| `SKILL.md` | Updated setup checklist, helper descriptions, and the anti-patterns list (dropped the old "use hosted Scribe" entry, added a note about `vad_filter`) to match the new backend. |
| `install.md` | Replaced the ElevenLabs API key section (step 5) with faster-whisper install/verification steps; updated the prerequisites list and cold-start reminders. |
| `.env.example` | No longer needs `ELEVENLABS_API_KEY`. |

## How to apply

After `video-use` has been freshly cloned (see the root `CLAUDE.md` for the clone/symlink/`uv sync` steps):

```bash
patches/video-use/apply.sh
# or, if video-use lives somewhere other than ~/Developer/video-use:
patches/video-use/apply.sh /path/to/video-use
```

The script copies the five files above into place and runs `uv add faster-whisper`
(falls back to `pip install faster-whisper` if `uv` isn't available) inside the target
clone. It's safe to re-run.

## Known limitations

- **No diarization.** `--num-speakers` is gone; `speaker_id` is always `null`. Fine for
  single-speaker talking-head footage, a regression for multi-speaker interviews.
- **Model download needs network access to Hugging Face Hub.** The first `transcribe.py`
  run downloads the `medium` model weights and caches them under `~/.cache/huggingface/`.
  Beyond the `huggingface.co` host itself, the actual weight bytes are served from CDN
  redirect hosts (observed: `cas-server.xethub.hf.co` for the Xet transfer path, and
  `us.aws.cdn.hf.co` as the plain-LFS fallback when Xet is disabled via
  `HF_HUB_DISABLE_XET=1`). A network policy that only allowlists `huggingface.co` itself
  will still fail at the download step — both CDN hosts need to be reachable too.
- **CPU inference is slow.** `medium` on CPU takes noticeably longer than the old hosted
  Scribe call. Consider `--model small` for faster iteration if quality allows, or `--device
  cuda` if a GPU is available.

## If upstream video-use changes

This patch is a snapshot, not a diff against a pinned upstream commit. If `browser-use/video-use`
changes these files significantly, re-apply by hand: diff the new upstream file against the
last-vendored copy here, carry the faster-whisper logic over, and re-copy into `patches/video-use/`.
