#!/usr/bin/env python3
"""
sfx_mix.py — микс: голос (мастер, не трогаем) + звуковые эффекты + музыкальная подложка с дакингом.

Usage:
  python3 sfx_mix.py edit/cues.json [-o edit/final.mp4] [--lufs -14] [--draft]

cues.json:
{
  "video": "edit/spliced.mp4",
  "cues": [ {"t": 3.33, "sfx": "whoosh-short", "gain_db": -9, "align": "peak",
             "pan": "wide", "dur": 0.8}, ... ],
  "bgm":  {"file": "assets/bgm/track.mp3", "gain_db": -24, "duck": true,
           "spans": [[3.3, 20.9], [33, 46]], "fade": 0.35, "cuts": [[28.0, 29.4]]}
}
  align: "start" — звук начинается в t; "peak" — громкий пик звука ровно в t (whoosh, импакт);
         "end" — звук заканчивается в t (riser, reverse-whoosh «втягивают» в склейку)
  pan:   "wide" (стерео-расширение, как в референсе — эффекты живут по бокам, голос в центре),
         "center", "left", "right"
  sfx:   имя из библиотеки (media-use + sfx-extra) или путь к файлу
  bgm.cuts: окна полной тишины подложки (drop перед панчлайном)

Голос: динамика не меняется. Громкость всего микса приводится к цели (по умолчанию
-14 LUFS — Reels/TikTok/Shorts) ЛИНЕЙНЫМ гейном в два прохода + true-peak лимитер.
SFX нормализуются к общей опорной громкости, поэтому gain_db одинаково значим для любого файла.
"""
import json, subprocess, argparse, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
LIBS = [os.path.join(SKILL, "assets", "sfx-user"),   # свои звуки Вики — приоритет
        os.path.join(SKILL, "assets", "sfx-extra"),
        os.path.join(SKILL, "..", "..", "..", "agent", "skills", "media-use", "audio", "assets", "sfx"),
        os.path.join(SKILL, "..", "media-use", "audio", "assets", "sfx")]
SR = 48000


def find_sfx(name, base):
    if os.path.exists(name):
        return name
    p = os.path.join(base, name)
    if os.path.exists(p):
        return p
    for lib in LIBS:
        for ext in ("", ".wav", ".mp3"):
            p = os.path.join(lib, name + ext)
            if os.path.exists(p):
                return os.path.abspath(p)
    sys.exit(f"SFX не найден: {name}. Проверь имя или укажи путь к файлу. Библиотеки: {LIBS}")


_peak_cache = {}


def sfx_info(path):
    """(длительность, время пика огибающей, поправка нормализации dB)."""
    if path in _peak_cache:
        return _peak_cache[path]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.abs(np.frombuffer(raw, np.float32))
    win = int(SR * 0.02)
    env = np.convolve(x, np.ones(win) / win, "same") if len(x) > win else x
    # нормализация: самое громкое окно 50 мс приводим к -6 dBFS RMS,
    # чтобы gain_db в cues означал одно и то же для любого файла библиотеки
    w5 = int(SR * 0.05)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(w5) / w5, "same")) if len(x) > w5 else x
    norm = -6.0 - 20 * np.log10(float(rms.max()) + 1e-9)
    r = (len(x) / SR, float(np.argmax(env)) / SR if len(env) else 0.0, max(min(norm, 24.0), -24.0))
    _peak_cache[path] = r
    return r


def gate_expr(spans, fade, cuts):
    """выражение громкости 0..1 для подложки: вкл на spans с fade-in/out, 0 в cuts."""
    parts = []
    for a, b in spans:
        f = min(fade, (b - a) / 2)
        parts.append(f"between(t,{a:.3f},{b:.3f})*min(1,min((t-{a:.3f})/{f:.3f},({b:.3f}-t)/{f:.3f}))")
    on = "+".join(parts) if parts else "1"
    off = "*".join(f"(1-between(t,{a:.3f},{b:.3f}))" for a, b in (cuts or [])) or "1"
    return f"min(1,{on})*{off}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cues")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()

    base = os.path.dirname(os.path.abspath(a.cues))
    C = json.load(open(a.cues))
    def rp(p):
        if os.path.isabs(p) or os.path.exists(p):
            return p
        return os.path.join(base, p)
    video = rp(C["video"])
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True, check=True).stdout.strip())
    out = a.out or os.path.splitext(video)[0] + "_sfx.mp4"

    inputs = ["-i", video]
    fc = ["[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[voice][vkey]"]
    mix = ["[voice]"]
    file_idx = {}
    uses = {}
    cues = [c for c in C.get("cues", []) if 0 <= c["t"] < dur]
    for c in cues:
        p = find_sfx(c["sfx"], base)
        if p not in file_idx:
            inputs += ["-i", p]
            file_idx[p] = len(file_idx) + 1
        uses.setdefault(p, []).append(c)
    sfx_labels = []
    for p, cl in uses.items():
        k = file_idx[p]
        L, pk, norm = sfx_info(p)
        names = [f"s{k}_{j}" for j in range(len(cl))]
        fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,asplit={len(cl)}" + "".join(f"[{n}i]" for n in names))
        for n, c in zip(names, cl):
            d = min(float(c.get("dur", L)), L)
            align = c.get("align", "start")
            # окно исходника [s0, s0+d]; ref — точка исходника, которая должна совпасть с t
            if align == "peak":      # пик в t: 60% окна до пика, 40% — хвост после
                s0 = max(0.0, min(pk - 0.6 * d, L - d))
                ref = pk
            elif align == "end":     # нарастание, которое «приземляется» в t на своём пике
                s0 = max(0.0, pk - d)
                ref = pk
                d = min(d, pk - s0 + 0.08) if pk > 0.2 else d
            else:
                s0, ref = 0.0, 0.0
            start = c["t"] - (ref - s0)
            if start < 0:            # звук должен начаться до 0 — подрезаем начало
                s0 += -start
                d -= -start
                start = 0.0
            if d <= 0.02:
                fc.append(f"[{n}i]anullsink")
                continue
            fo = min(0.08, d / 3)
            fi = 0.01 if s0 > 0 else 0.0
            pan = c.get("pan", "center")
            pan_f = {"wide": ",extrastereo=m=2.2", "left": ",pan=stereo|c0=c0|c1=0.35*c1",
                     "right": ",pan=stereo|c0=0.35*c0|c1=c1"}.get(pan, "")
            ms = int(round(start * 1000))
            fc.append(f"[{n}i]atrim=start={s0:.3f}:duration={d:.3f},asetpts=PTS-STARTPTS,"
                      + (f"afade=t=in:d={fi},"if fi else "") +
                      f"afade=t=out:st={max(d - fo, 0):.3f}:d={fo:.3f},volume={c.get('gain_db', -12) + norm:.2f}dB"
                      f"{pan_f},adelay={ms}|{ms}[{n}]")
            sfx_labels.append(f"[{n}]")
    if sfx_labels:
        fc.append("".join(sfx_labels) + f"amix=inputs={len(sfx_labels)}:normalize=0:dropout_transition=0,"
                  f"apad=whole_dur={dur:.3f}[sfx]")
        mix.append("[sfx]")

    B = C.get("bgm")
    if B and B.get("file"):
        bp = rp(B["file"])
        inputs += ["-stream_loop", "-1", "-i", bp]
        k = len(file_idx) + 1
        g = gate_expr(B.get("spans", [[0, dur]]), float(B.get("fade", 0.35)), B.get("cuts"))
        fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
                  f"volume={B.get('gain_db', -24)}dB,volume='{g}':eval=frame[bgm0]")
        if B.get("duck", True):
            # дакинг: голос — ключ, музыка проседает на ~8-10 dB под словами и возвращается в паузах
            fc.append("[bgm0][vkey]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350:makeup=1[bgm]")
        else:
            fc.append("[bgm0]anull[bgm];[vkey]anullsink")
        mix.append("[bgm]")
    else:
        fc.append("[vkey]anullsink")

    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first[aout]")
    # проход 1: сводим в wav (32-bit float, без потерь)
    tmp = os.path.splitext(out)[0] + ".mix.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostats"] + inputs +
                   ["-filter_complex", ";".join(fc), "-map", "[aout]", "-c:a", "pcm_f32le",
                    "-t", f"{dur:.3f}", tmp], check=True)
    # проход 2: меряем громкость и поднимаем/опускаем ЛИНЕЙНО (динамику голоса не трогаем),
    # true-peak limiter ловит только редкие пики эффектов
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    I = float([l for l in meas.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    gain = a.lufs - I
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostats", "-i", video, "-i", tmp,
                    "-filter_complex", f"[1:a]volume={gain:.2f}dB,alimiter=limit=0.84:attack=1:release=50:level=disabled[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-t", f"{dur:.3f}", "-movflags", "+faststart", out], check=True)
    os.remove(tmp)
    print(f"OK → {out}  (эффектов: {len(sfx_labels)}, подложка: {'да' if B and B.get('file') else 'нет'}, "
          f"громкость {I:.1f} → {a.lufs} LUFS, gain {gain:+.1f} dB)")


if __name__ == "__main__":
    main()
