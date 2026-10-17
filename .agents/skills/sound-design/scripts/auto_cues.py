#!/usr/bin/env python3
"""
auto_cues.py — расставляет звуковые эффекты по стыкам и событиям моушена.

Вход:  <video>.seams.json от aroll-motion-splice/scripts/splice.py
Выход: cues.json для sfx_mix.py (можно править руками перед миксом)

Правила взяты из разбора референсов (references/reference-breakdown.md):
  • лицо → моушен      : whoosh, пик точно на кадре склейки, стерео-широко
  • моушен → моушен    : короткий swipe/whoosh тише
  • моушен → лицо      : мягкий swipe или тишина (лицо «возвращает» зрителя голосом)
  • glitch-переход     : glitch вместо whoosh
  • flash              : whoosh + bass-impact
  • первый моушен      : riser, который «приземляется» в склейку
  • появления иконок   : pop / click-soft (тихо, -16…-20 dB)
  • печать текста      : typing на длину печати
  • счётчик 0→84%      : тики, ускоряющиеся к концу
  • ключевой факт      : impact-bass
  • CTA / уведомление  : notification
Плотность: не больше одного «крупного» звука на 0.35 с; UI-щелчки не чаще 0.12 с.

Usage:
  python3 auto_cues.py edit/spliced.seams.json -o edit/cues.json [--bgm motion_only|full|none]
"""
import json, argparse, os

SEAM_RULES = {
    # (from, to, transition) → list of cues; transition "*" = любой
    ("aroll", "motion", "glitch"): [("glitch-1", -11, "peak", None)],
    ("motion", "motion", "glitch"): [("glitch-3", -12, "start", 0.6)],
    ("motion", "aroll", "glitch"): [("glitch-3", -13, "start", 0.5)],
    ("aroll", "motion", "flash"): [("whoosh-short", -9, "peak", None), ("impact-bass-1", -17, "start", 1.0)],
    ("aroll", "motion", "zoom"): [("whoosh-cinematic", -10, "peak", 1.4)],
    ("aroll", "motion", "*"): [("whoosh-short", -9, "peak", None)],
    ("motion", "motion", "*"): [("swipe", -13, "peak", None)],
    ("motion", "aroll", "*"): [("swipe", -16, "peak", None)],
}

EVENT_RULES = {
    "appear": ("pop", -17), "icon": ("pop", -17), "pop": ("pop", -16),
    "click": ("click-soft", -15), "select": ("click", -15), "cursor": ("click-soft", -16),
    "typing": ("typing", -19), "key": ("key-press", -16),
    "counter": ("tick", -15),
    "reveal": ("impact-bass-2", -16), "fact": ("impact-bass-1", -16), "slam": ("impact-bass-1", -14),
    "alert": ("notification", -15), "message": ("notification", -15), "cta": ("notification", -13),
    "error": ("error", -15), "negative": ("error", -15), "warning": ("error", -16),
    "success": ("chime", -16), "check": ("chime", -17),
    "sparkle": ("sparkle", -17), "glitch": ("glitch-3", -14), "drop": ("sub-drop", -14),
    "riser": ("riser", -12),
}
BIG = {"whoosh", "whoosh-short", "whoosh-cinematic", "swipe", "glitch-1", "glitch-2", "glitch-3",
       "impact-bass-1", "impact-bass-2", "riser", "sub-drop", "notification", "error", "chime"}


def rule_for(f, t, tr):
    return SEAM_RULES.get((f, t, tr)) or SEAM_RULES.get((f, t, "*"), [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seams")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--bgm", default="motion_only", choices=["motion_only", "full", "none"],
                    help="музыкальная подложка: только под моушеном (как в референсе), везде с дакингом, или без")
    ap.add_argument("--bgm-file", default=None)
    ap.add_argument("--no-opener", action="store_true", help="не ставить riser перед первым моушеном")
    ap.add_argument("--quiet-returns", action="store_true", help="без звука на возврате к лицу")
    a = ap.parse_args()

    M = json.load(open(a.seams))
    cues = []
    seams = M.get("seams", [])
    for i, s in enumerate(seams):
        if a.quiet_returns and s["to"] == "aroll":
            continue
        for sfx, g, align, dur in rule_for(s["from"], s["to"], s.get("transition", "cut")):
            cues.append({"t": s["t"], "sfx": sfx, "gain_db": g, "align": align, "pan": "wide",
                         **({"dur": dur} if dur else {}), "why": f"seam {s['from']}→{s['to']} ({s.get('transition')})"})
    first = next((s for s in seams if s["to"] == "motion"), None)
    if first and not a.no_opener and first["t"] > 1.0:
        cues.append({"t": first["t"], "sfx": "riser", "gain_db": -15, "align": "end", "pan": "wide",
                     "dur": 1.6, "why": "opener: riser lands on first motion"})

    for e in M.get("events", []):
        kind = e.get("type", "appear")
        if kind not in EVENT_RULES:
            continue
        sfx, g = EVENT_RULES[kind]
        g += float(e.get("gain_offset", 0))
        if kind == "typing":
            cues.append({"t": e["t"], "sfx": sfx, "gain_db": g, "align": "start",
                         "dur": float(e.get("dur", 1.0)), "pan": "center", "why": "typing"})
        elif kind == "counter":
            n = int(e.get("steps", 8)); d = float(e.get("dur", 1.0))
            for k in range(n):  # тики сгущаются к концу (ease-in)
                tt = e["t"] + d * (1 - (1 - (k / max(n - 1, 1))) ** 1.6)
                cues.append({"t": round(tt, 3), "sfx": sfx, "gain_db": g + (k == n - 1) * 3,
                             "align": "start", "pan": "center", "ui": True, "why": "counter tick"})
        else:
            cues.append({"t": e["t"], "sfx": e.get("sfx", sfx), "gain_db": g, "align": "start",
                         "pan": e.get("pan", "center"), "ui": sfx not in BIG, "why": kind})

    # плотность: крупные звуки ≥0.35 с друг от друга, UI ≥0.12 с; при конфликте громче побеждает
    cues.sort(key=lambda c: (c["t"], -c["gain_db"]))
    kept = []
    for c in cues:
        big = c["sfx"] in BIG and not c.get("ui")
        gap = 0.35 if big else 0.12
        clash = [k for k in kept if (k["sfx"] in BIG) == big and abs(k["t"] - c["t"]) < gap
                 and k["sfx"] != "riser" and c["sfx"] != "riser"]
        if clash and not (c["sfx"] in ("impact-bass-1",) and clash[0]["sfx"].startswith("whoosh")):
            continue
        kept.append(c)

    out = {"video": M["video"], "duration": M["duration"], "cues": kept}
    if a.bgm != "none":
        spans = []
        if a.bgm == "motion_only":
            # подложка только под моушен-блоками; соседние блоки сливаем
            for s in M.get("segments", []):
                if spans and s["start"] - spans[-1][1] < 1.2:
                    spans[-1][1] = s["end"]
                else:
                    spans.append([s["start"], s["end"]])
        else:
            spans = [[0, M["duration"]]]
        out["bgm"] = {"file": a.bgm_file, "gain_db": -24, "duck": True, "spans": spans,
                      "fade": 0.35, "note": "file=null → подставь трек (media-use resolve --type bgm) или оставь без музыки"}
    dst = a.out or os.path.join(os.path.dirname(a.seams), "cues.json")
    json.dump(out, open(dst, "w"), ensure_ascii=False, indent=2)
    print(f"OK → {dst}: {len(kept)} эффектов (отброшено по плотности: {len(cues) - len(kept)})")


if __name__ == "__main__":
    main()
