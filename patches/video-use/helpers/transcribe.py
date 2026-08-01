"""Transcribe a video locally with faster-whisper (no external API).

Extracts mono 16kHz audio via ffmpeg, runs faster-whisper with word-level
timestamps, writes the result to <edit_dir>/transcripts/<video_stem>.json
in the same words-list shape the rest of the pipeline (pack_transcripts.py
etc.) already expects: {"words": [{"type": "word", "text", "start", "end",
"speaker_id"}, ...]}.

Runs fully offline once the model weights are cached locally — no API key,
no per-minute cost. faster-whisper has no diarization; speaker_id is always
null. VAD filtering is off by default because it can swallow short filler
words ("эм", "ну", "вот") that the edit pipeline needs to find and cut.

Cached: if the output file already exists, transcription is skipped.

Usage:
    python helpers/transcribe.py <video_path>
    python helpers/transcribe.py <video_path> --edit-dir /custom/edit
    python helpers/transcribe.py <video_path> --language ru
    python helpers/transcribe.py <video_path> --model medium
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from faster_whisper import WhisperModel

DEFAULT_MODEL = "medium"
DEFAULT_LANGUAGE = "ru"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"

_model_cache: dict[tuple[str, str, str], WhisperModel] = {}


def get_model(
    model_size: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> WhisperModel:
    key = (model_size, device, compute_type)
    if key not in _model_cache:
        _model_cache[key] = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model_cache[key]


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def call_faster_whisper(
    audio_path: Path,
    model_size: str = DEFAULT_MODEL,
    language: str | None = DEFAULT_LANGUAGE,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> dict:
    model = get_model(model_size, device, compute_type)
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
    )

    words: list[dict] = []
    for segment in segments:
        for w in segment.words or []:
            text = w.word.strip()
            if not text:
                continue
            words.append({
                "type": "word",
                "text": text,
                "start": w.start,
                "end": w.end,
                "speaker_id": None,
            })

    return {
        "language_code": info.language,
        "language_probability": info.language_probability,
        "model": model_size,
        "words": words,
    }


def transcribe_one(
    video: Path,
    edit_dir: Path,
    model_size: str = DEFAULT_MODEL,
    language: str | None = DEFAULT_LANGUAGE,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    verbose: bool = True,
) -> Path:
    """Transcribe a single video. Returns path to transcript JSON.

    Cached: returns existing path immediately if the transcript already exists.
    """
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  transcribing {video.stem}.wav ({size_mb:.1f} MB) with faster-whisper ({model_size})", flush=True)
        payload = call_faster_whisper(audio, model_size, language, device, compute_type)

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        print(f"    words: {len(payload['words'])}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video locally with faster-whisper")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir",
        type=Path,
        default=None,
        help="Edit output directory (default: <video_parent>/edit)",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=DEFAULT_LANGUAGE,
        help=f"ISO language code (default: {DEFAULT_LANGUAGE}). Pass an empty string to auto-detect.",
    )
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"faster-whisper model size (default: {DEFAULT_MODEL})")
    ap.add_argument("--device", type=str, default=DEFAULT_DEVICE, help=f"cpu or cuda (default: {DEFAULT_DEVICE})")
    ap.add_argument(
        "--compute-type",
        type=str,
        default=DEFAULT_COMPUTE_TYPE,
        help=f"ctranslate2 compute type, e.g. int8/float16/float32 (default: {DEFAULT_COMPUTE_TYPE})",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        model_size=args.model,
        language=args.language or None,
        device=args.device,
        compute_type=args.compute_type,
    )


if __name__ == "__main__":
    main()
