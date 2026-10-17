#!/usr/bin/env python3
"""
splice.py — склейка «живой человек + моушен» на ОДНОМ звуке.

Принцип: звук A-roll (голос спикера) — мастер-дорожка, он идёт без единого
разрыва от первого до последнего кадра. Меняется только картинка: на
отрезках из плана поверх A-roll кладётся моушен-клип (полностью перекрывает
кадр), на стыках — переход (cut / slide / flash / blur / glitch / zoom),
при возврате на лицо — punch-in (чередование масштаба), чтобы стык не читался
как «прыжок».

Звук НЕ перекодируется по смыслу: -map 0:a, голос побитово тот же
(перекодируется в AAC только если исходник не AAC).

Usage:
  python3 splice.py plan.json [--draft] [--dry-run]

Выход:
  <out>.mp4            — склейка
  <out>.seams.json     — все стыки и события моушена в абсолютном времени
                         (вход для sound-design/scripts/auto_cues.py)

Формат plan.json — см. ../examples/splice.plan.json и SKILL.md.
"""
import json, subprocess, sys, os, shlex, argparse

TRANS_D = {"cut": 0.0, "slide": 0.28, "slide_up": 0.28, "push": 0.28,
           "flash": 0.18, "blur": 0.24, "glitch": 0.20, "zoom": 0.30}


def ffprobe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def load_words(path):
    """video-use transcript ({words:[{type,text,start,end}]}) или список [start,end,text]."""
    if not path or not os.path.exists(path):
        return []
    d = json.load(open(path))
    W = d.get("words", d) if isinstance(d, dict) else d
    res = []
    for w in W:
        if isinstance(w, dict):
            if w.get("type", "word") != "word":
                continue
            res.append((float(w["start"]), float(w["end"])))
        else:
            res.append((float(w[0]), float(w[1])))
    return sorted(res)


def snap(t, words, fps, max_shift=0.25):
    """Стык ставим в паузу между словами (середина зазора) или на начало слова,
    но не дальше max_shift. Потом квантуем по кадру."""
    best = t
    if words:
        cands = []
        for i, (s, e) in enumerate(words):
            cands.append(s)  # начало слова — картинка меняется вместе со словом
            if i + 1 < len(words):
                ns = words[i + 1][0]
                if ns - e > 0.06:
                    cands.append((e + ns) / 2)
        c = min(cands, key=lambda x: abs(x - t))
        if abs(c - t) <= max_shift:
            best = c
    return round(best * fps) / fps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--draft", action="store_true", help="быстрый рендер (ultrafast, crf 28)")
    ap.add_argument("--dry-run", action="store_true", help="только напечатать команду ffmpeg")
    a = ap.parse_args()

    base_dir = os.path.dirname(os.path.abspath(a.plan))
    P = json.load(open(a.plan))
    rp = lambda p: p if os.path.isabs(p) else os.path.join(base_dir, p)

    aroll = rp(P["aroll"])
    W, H = P.get("size", [1080, 1920])
    fps = P.get("fps", 30)
    info = ffprobe(aroll)
    dur = float(info["format"]["duration"])
    acodec = next((s["codec_name"] for s in info["streams"] if s["codec_type"] == "audio"), None)
    if acodec is None:
        sys.exit("A-roll без звука — нечего держать мастер-дорожкой")
    words = load_words(rp(P["words"])) if P.get("words") else []
    out = rp(P.get("out", "edit/spliced.mp4"))
    os.makedirs(os.path.dirname(out), exist_ok=True)

    segs = sorted(P.get("segments", []), key=lambda s: s["start"])
    for s in segs:
        s["start"] = snap(s["start"], words, fps)
        s["end"] = min(snap(s["end"], words, fps), dur)
    for i in range(1, len(segs)):
        if segs[i]["start"] < segs[i - 1]["end"]:
            segs[i - 1]["end"] = segs[i]["start"]  # соседние моушены: стык встык

    inputs = ["-i", aroll]
    fc = []
    # 1) база: A-roll в нужный кадр (cover), фиксированный fps
    fc.append(f"[0:v]fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},setsar=1,format=yuv420p[a0]")
    cur = "a0"

    # 2) punch-in: на каждом возврате к лицу чередуем 1.0 / scale (по умолчанию 1.12)
    a_spans, t0 = [], 0.0
    for s in segs:
        if s["start"] - t0 > 0.05:
            a_spans.append([t0, s["start"]])
        t0 = s["end"]
    if dur - t0 > 0.05:
        a_spans.append([t0, dur])
    zoom_spans = list(P.get("punch_in", []))  # [[start,end,scale],...]
    if P.get("auto_punch", True):
        sc = float(P.get("punch_scale", 1.12))
        for i, (s0, s1) in enumerate(a_spans):
            if i % 2 == 1:
                zoom_spans.append([s0, s1, sc])
    if zoom_spans:
        n = len(zoom_spans)
        fc.append(f"[{cur}]split={n + 1}[zb]" + "".join(f"[zs{i}]" for i in range(n)))
        cur = "zb"
        fy = float(P.get("punch_focus_y", 0.38))  # точка фокуса — лицо (доля высоты)
        for i, (s0, s1, sc) in enumerate(zoom_spans):
            cw, ch = int(W / sc) // 2 * 2, int(H / sc) // 2 * 2
            fc.append(f"[zs{i}]crop={cw}:{ch}:(iw-{cw})/2:max(0\\,min(ih-{ch}\\,ih*{fy}-{ch}/2)),"
                      f"scale={W}:{H},setsar=1[zc{i}]")
            fc.append(f"[{cur}][zc{i}]overlay=enable='between(t,{s0:.3f},{s1:.3f})'[zo{i}]")
            cur = f"zo{i}"

    seams, events = [], []
    # 3) моушен-вставки
    for i, s in enumerate(segs):
        src = rp(s["src"])
        inputs += ["-i", src]
        k = len(inputs) // 2 - 1
        st, en = s["start"], s["end"]
        d = en - st
        cin = float(s.get("in", 0))
        fit = s.get("fit", "cover")
        if fit == "contain":
            sc = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                  f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={s.get('pad', 'black')}")
        else:
            sc = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        # клип короче окна — держим последний кадр (tpad clone)
        fc.append(f"[{k}:v]trim=start={cin}:duration={d:.3f},setpts=PTS-STARTPTS,fps={fps},{sc},"
                  f"setsar=1,format=yuva420p,tpad=stop_mode=clone:stop_duration={d:.3f},"
                  f"trim=duration={d:.3f},tpad=start_mode=clone:start_duration={2 / fps:.4f},"
                  f"setpts=PTS+{st - 2 / fps:.4f}/TB[m{i}]")  # +2 кадра запаса: без «дырки» на стыке
        enter = s.get("enter", "cut")
        td = TRANS_D.get(enter, 0)
        x, y = "0", "0"
        if enter in ("slide", "push"):     # въезд справа, easeOutCubic
            x = f"if(lt(t\\,{st + td:.3f})\\,W*pow(1-(t-{st:.3f})/{td}\\,3)\\,0)"
        elif enter == "slide_up":          # въезд снизу (как в референсе Молянова)
            y = f"if(lt(t\\,{st + td:.3f})\\,H*pow(1-(t-{st:.3f})/{td}\\,3)\\,0)"
        fc.append(f"[{cur}][m{i}]overlay=x='{x}':y='{y}':eof_action=pass:"
                  f"enable='between(t,{st:.3f},{en - 0.0001:.3f})'[v{i}]")
        cur = f"v{i}"
        prev_is_motion = i > 0 and abs(segs[i - 1]["end"] - st) < 0.02
        seams.append({"t": st, "from": "motion" if prev_is_motion else "aroll", "to": "motion",
                      "transition": enter, "segment": i})
        nxt_is_motion = i + 1 < len(segs) and abs(segs[i + 1]["start"] - en) < 0.02
        if not nxt_is_motion and en < dur - 0.05:
            seams.append({"t": en, "from": "motion", "to": "aroll",
                          "transition": s.get("exit", "cut"), "segment": i})
        # события внутри моушена (появления иконок, печать, счётчик) → абсолютное время
        ev_file = s.get("events")
        evs = s.get("events_inline", [])
        if ev_file and os.path.exists(rp(ev_file)):
            evs = evs + json.load(open(rp(ev_file)))
        for e in evs:
            tt = st + float(e["t"]) - cin
            if st <= tt < en:
                events.append({**e, "t": round(tt, 3), "segment": i})

    # 4) эффекты на стыках (поверх уже собранной картинки)
    fx_i = 0
    for sm in seams:
        tr, T = sm["transition"], sm["t"]
        if tr == "flash":
            fc.append(f"color=white:s={W}x{H}:d=0.26:r={fps},format=rgba,"
                      f"fade=t=in:st=0:d=0.06:alpha=1,fade=t=out:st=0.08:d=0.18:alpha=1,"
                      f"setpts=PTS+{max(T - 0.06, 0):.3f}/TB[fl{fx_i}]")
            fc.append(f"[{cur}][fl{fx_i}]overlay=eof_action=pass[fx{fx_i}]")
        elif tr == "blur":
            fc.append(f"[{cur}]split[bb{fx_i}][bs{fx_i}];[bs{fx_i}]gblur=sigma=28[bg{fx_i}];"
                      f"[bb{fx_i}][bg{fx_i}]overlay=enable='between(t,{T - 0.12:.3f},{T + 0.12:.3f})'[fx{fx_i}]")
        elif tr == "glitch":
            fc.append(f"[{cur}]split[gb{fx_i}][gs{fx_i}];[gs{fx_i}]rgbashift=rh=-28:bh=28:gv=6,"
                      f"noise=alls=45:allf=t,hue=s=1.4[gg{fx_i}];"
                      f"[gb{fx_i}][gg{fx_i}]overlay=x='if(lt(mod(n\\,3)\\,1)\\,-24\\,18)':"
                      f"enable='between(t,{T - 0.08:.3f},{T + 0.12:.3f})'[fx{fx_i}]")
        elif tr == "zoom":
            sc = 1.18
            cw, ch = int(W / sc) // 2 * 2, int(H / sc) // 2 * 2
            fc.append(f"[{cur}]split[zb{fx_i}][zz{fx_i}];[zz{fx_i}]crop={cw}:{ch},scale={W}:{H},"
                      f"gblur=sigma=6[zq{fx_i}];[zb{fx_i}][zq{fx_i}]overlay="
                      f"enable='between(t,{T - 0.1:.3f},{T + 0.1:.3f})'[fx{fx_i}]")
        else:
            continue
        cur = f"fx{fx_i}"
        fx_i += 1

    # 5) субтитры — ПОСЛЕДНИМ слоем, поверх и лица, и моушена (это и есть «клей»)
    if P.get("captions"):
        cap = rp(P["captions"]).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        filt = "ass" if cap.endswith(".ass") else "subtitles"
        fc.append(f"[{cur}]{filt}='{cap}'[cap]")
        cur = "cap"
    fc.append(f"[{cur}]format=yuv420p[vout]")

    enc = (["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"] if a.draft
           else ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high"])
    aenc = ["-c:a", "copy"] if acodec == "aac" else ["-c:a", "aac", "-b:a", "256k"]
    cmd = (["ffmpeg", "-y", "-v", "error", "-nostats"] + inputs +
           ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "0:a"] +
           enc + aenc + ["-t", f"{dur:.3f}", "-movflags", "+faststart", out])
    if a.dry_run:
        print(" ".join(shlex.quote(c) for c in cmd))
        return
    subprocess.run(cmd, check=True)
    meta = {"video": out, "duration": dur, "fps": fps, "segments": segs,
            "aroll_spans": a_spans, "seams": seams, "events": sorted(events, key=lambda e: e["t"])}
    json.dump(meta, open(os.path.splitext(out)[0] + ".seams.json", "w"), ensure_ascii=False, indent=2)
    print(f"OK → {out}\n   стыков: {len(seams)}, событий моушена: {len(events)}, "
          f"punch-in: {len(zoom_spans)}\n   seams → {os.path.splitext(out)[0]}.seams.json")


if __name__ == "__main__":
    main()
