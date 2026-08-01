#!/usr/bin/env bash
# Apply the faster-whisper transcription patch onto a fresh video-use clone.
#
# Usage:
#   patches/video-use/apply.sh [path-to-video-use-clone]
#
# Defaults to ~/Developer/video-use (the path used by CLAUDE.md's setup steps).

set -euo pipefail

PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$HOME/Developer/video-use}"

if [ ! -d "$TARGET" ]; then
    echo "error: video-use clone not found at $TARGET" >&2
    echo "clone it first, e.g.: git clone https://github.com/browser-use/video-use $TARGET" >&2
    exit 1
fi

if [ ! -f "$TARGET/SKILL.md" ]; then
    echo "error: $TARGET does not look like a video-use clone (no SKILL.md)" >&2
    exit 1
fi

echo "applying faster-whisper patch to $TARGET"

cp "$PATCH_DIR/helpers/transcribe.py" "$TARGET/helpers/transcribe.py"
cp "$PATCH_DIR/helpers/transcribe_batch.py" "$TARGET/helpers/transcribe_batch.py"
cp "$PATCH_DIR/SKILL.md" "$TARGET/SKILL.md"
cp "$PATCH_DIR/install.md" "$TARGET/install.md"
cp "$PATCH_DIR/.env.example" "$TARGET/.env.example"

echo "copied 5 files"

if command -v uv >/dev/null 2>&1; then
    (cd "$TARGET" && uv add faster-whisper)
else
    echo "uv not found, falling back to pip"
    (cd "$TARGET" && pip install faster-whisper)
fi

echo "done. faster-whisper (model medium, language ru) is now the transcription backend."
