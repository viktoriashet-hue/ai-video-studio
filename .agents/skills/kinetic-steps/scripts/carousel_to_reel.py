"""Шаблон-генератор kinetic-steps: рилс из скриншотов карусели + стрелки, обводки, галочки, зум камеры.
Пример: карусель corka_freuda «Как настроить ChatGPT для создания видео» (Dehu4hNAFm1). Меняй SHOTS, STEPS, тексты HOOK/RESULT/CTA."""
import json

W, H = 1080, 1920
INK, CREAM, BLUE, SKY = "#17181f", "#f5efe7", "#1a6aff", "#56b6fd"

# размеры кропов (px исходника)
SHOTS = {
    "shot1": (543, 869), "shot2": (658, 933), "shot3": (940, 633),
    "shot4": (598, 869), "shot5": (940, 414),
}

# Шаги: фон, заголовок (2 строки), скрин, аннотации в координатах скрина
STEPS = [
    dict(bg="cream", n=1, a="открой", b="«плагины»", note="в ChatGPT", shot="shot1",
         circle=(2, 38, 100, 30), arrow=((640, 40), (122, 50)),
         circle2=(6, 104, 531, 28), zoom=(0, 0, 543, 420)),
    dict(bg="blue", n=2, a="найди", b="remotion", note="и жми плюсик", shot="shot2",
         circle=(4, 160, 150, 46), arrow=((770, 330), (585, 196)),
         circle2=(430, 158, 140, 32), zoom=(0, 60, 658, 380)),
    dict(bg="ink", n=3, a="второй", b="hyperframes", note="by HeyGen", shot="shot3",
         circle=(655, 228, 285, 60), arrow=((470, 580), (700, 300)),
         circle2=(36, 128, 160, 50), zoom=(380, 100, 560, 260)),
    dict(bg="cream", n=4, a="обнови", b="окно", note="оба плагина в «Установленных»", shot="shot4",
         circle=(10, 118, 190, 40), arrow=((700, 330), (215, 150)),
         check=(62, 68), zoom=(0, 40, 598, 400)),
    dict(bg="blue", n=5, a="добавь", b="видео", note="они станут референсом", shot="shot5",
         circle=(128, 125, 336, 125), arrow=((720, -120), (472, 160)),
         zoom=(100, 100, 500, 200)),
    dict(bg="ink", n=6, a="напиши", b="задачу", note="и ChatGPT сам собирает ролик", shot="shot5",
         circle=(132, 276, 576, 28), arrow=((620, -110), (866, 312)),
         circle2=(846, 318, 52, 52), zoom=(120, 230, 800, 150),
         chips=["20-секундный промо", "субтитры к видео", "заставка с текстом"]),
]

HOOK = 3.2
STEP = 3.9
RESULT = 2.6
CTA = 4.2
T_STEPS = HOOK
T_RESULT = HOOK + STEP * len(STEPS)
T_CTA = T_RESULT + RESULT
TOTAL = round(T_CTA + CTA, 2)

FILL = {"ink": INK, "cream": CREAM, "blue": BLUE}
TEXT = {"ink": "#ffffff", "cream": INK, "blue": "#ffffff"}
ACC = {"ink": SKY, "cream": BLUE, "blue": "#ffffff"}
ANN = {"ink": SKY, "cream": BLUE, "blue": "#ffd84d"}  # цвет стрелок/обводок вне скрина


def card_geom(shot):
    w, h = SHOTS[shot]
    s = min(900 / w, 880 / h)
    cw, ch = round(w * s), round(h * s)
    left = (W - cw) // 2
    top = 700 + (880 - ch) // 2 if ch > 700 else 1100 - ch // 2 - 90
    return s, cw, ch, left, top


css = f"""
:root {{ --ink:{INK}; --cream:{CREAM}; --blue:{BLUE}; --sky:{SKY}; --muted:#8b8c96; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--ink); font-family:"Inter","Helvetica Neue",sans-serif; }}
#root {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; background:var(--ink); }}
.scene {{ position:absolute; inset:0; width:{W}px; height:{H}px; overflow:hidden; }}
.fill {{ position:absolute; inset:0; }}
.grid {{ position:absolute; inset:0; opacity:.07; background-image:linear-gradient(to right,#fff 1px,transparent 1px),linear-gradient(to bottom,#fff 1px,transparent 1px); background-size:135px 135px; }}
.w {{ display:block; font-weight:900; text-transform:uppercase; letter-spacing:-0.035em; line-height:.95; }}
.serif {{ font-family:"Playfair Display",Georgia,serif; font-style:italic; font-weight:400; text-transform:none; letter-spacing:0; }}
.hl {{ display:inline-block; }}
.uline {{ display:block; height:8px; border-radius:8px; background:currentColor; transform-origin:left center; margin:14px auto 0; }}
.head {{ position:absolute; left:90px; right:90px; top:250px; text-align:center; }}
.kick {{ font-size:30px; font-weight:900; letter-spacing:.3em; }}
.big {{ font-size:128px; margin-top:16px; }}
.mid {{ font-size:80px; }}
.note {{ font-size:40px; font-weight:700; margin-top:22px; letter-spacing:-0.01em; }}
.card {{ position:absolute; border-radius:34px; overflow:visible; }}
.cam {{ position:absolute; inset:0; }}
.shot {{ position:absolute; inset:0; border-radius:34px; overflow:hidden; box-shadow:0 40px 90px rgba(0,0,0,.35); background:#fff; }}
.shot img {{ display:block; width:100%; height:100%; }}
.ann {{ position:absolute; left:0; top:0; overflow:visible; }}
.chips {{ position:absolute; left:90px; right:90px; top:1400px; display:flex; flex-wrap:wrap; gap:18px; justify-content:center; }}
.chip {{ height:78px; padding:0 30px; border-radius:40px; background:#fff; color:var(--ink); font-size:32px; font-weight:800; display:flex; align-items:center; }}
.chrome {{ position:absolute; inset:0; pointer-events:none; }}
.kicker {{ position:absolute; top:96px; left:72px; font-size:22px; font-weight:700; letter-spacing:.32em; color:var(--muted); }}
.footer {{ position:absolute; bottom:150px; left:72px; font-size:20px; font-weight:700; letter-spacing:.32em; color:var(--muted); }}
.pill {{ position:absolute; top:70px; right:60px; height:76px; padding:0 30px 0 12px; display:flex; align-items:center; gap:16px; border-radius:40px; background:#1f2330; border:2px solid #2f3a5c; }}
.pill .ava {{ width:52px; height:52px; border-radius:50%; background:var(--blue); display:grid; place-items:center; color:#fff; font-weight:900; font-size:26px; }}
.pill .meta {{ display:flex; flex-direction:column; }}
.pill .lab {{ font-size:15px; color:#8fa0c8; }}
.pill .handle {{ font-size:22px; font-weight:700; color:#fff; }}
.wipe {{ position:absolute; inset:0; }}
.col {{ position:absolute; bottom:0; height:{H}px; width:216px; transform-origin:center bottom; }}
.iris {{ position:absolute; left:50%; top:50%; width:2400px; height:2400px; margin:-1200px 0 0 -1200px; border-radius:50%; background:var(--cream); }}
.hero {{ position:absolute; left:0; top:150px; width:{W}px; height:790px; overflow:hidden; }}
.hero img {{ display:block; width:100%; height:100%; transform-origin:50% 35%; }}
.hero-fade {{ position:absolute; left:0; right:0; top:640px; height:320px; background:linear-gradient(to bottom, rgba(23,24,31,0), var(--ink)); }}
.hook {{ position:absolute; left:80px; right:80px; top:1000px; text-align:center; }}
.spark {{ position:absolute; width:56px; height:56px; }}
.spark svg {{ width:100%; height:100%; display:block; }}
"""

SPARK = '<svg viewBox="0 0 40 40"><path d="M20 0 C22 14 26 18 40 20 C26 22 22 26 20 40 C18 26 14 22 0 20 C14 18 18 14 20 0Z" fill="none" stroke="{c}" stroke-width="2.4"/></svg>'

html, js = [], []
J = js.append

# ---------- HOOK ----------
html.append(f"""
<section id="hook" class="scene clip" data-start="0" data-duration="{HOOK}" data-track-index="1">
  <div class="fill" style="background:{INK}"></div><div class="grid"></div>
  <div class="hero"><img id="hook-img" src="assets/hero.jpg" alt=""></div>
  <div class="hero-fade"></div>
  <div class="hook">
    <span id="h1" class="w on" style="font-size:78px;color:#fff">как настроить</span>
    <span id="h2" class="w" style="font-size:190px;color:{SKY};margin-top:10px">chatgpt</span>
    <span id="h3" class="w" style="font-size:78px;color:#fff;margin-top:14px">для создания</span>
    <span id="h4" class="w" style="font-size:170px;color:{SKY};margin-top:10px">видео</span>
  </div>
</section>""")
J(f'tl.fromTo("#hook-img",{{scale:1.18}},{{scale:1.0,duration:{HOOK},ease:"power1.out"}},0);')
for i, t in enumerate([0.05, 0.4, 0.95, 1.3]):
    J(f'tl.fromTo("#h{i+1}",{{y:70,opacity:0,scale:.9}},{{y:0,opacity:1,scale:1,duration:.34,ease:"power3.out"}},{t});')

# ---------- STEPS ----------
wipes = []
for idx, st in enumerate(STEPS):
    t0 = round(T_STEPS + idx * STEP, 2)
    sid = f"st{idx+1}"
    bg = st["bg"]
    s, cw, ch, left, top = card_geom(st["shot"])
    tc, ac, an = TEXT[bg], ACC[bg], ANN[bg]
    grid = '<div class="grid"></div>' if bg == "ink" else ""
    sw, sh = SHOTS[st["shot"]]
    # аннотации в координатах скрина (viewBox = размер исходника)
    parts = []
    def ell(cid, r, color):
        x, y, w, h = r
        pad = 14
        cx, cy, rx, ry = x + w / 2, y + h / 2, w / 2 + pad, h / 2 + pad
        return (f'<ellipse id="{cid}" cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{color}" '
                f'stroke-width="{6/s:.2f}" stroke-linecap="round" transform="rotate(-2 {cx} {cy})"/>')
    parts.append(ell(f"{sid}-c1", st["circle"], BLUE))
    if "circle2" in st:
        parts.append(ell(f"{sid}-c2", st["circle2"], BLUE))
    (ax, ay), (bx, by) = st["arrow"]
    mx, my = (ax + bx) / 2 + (by - ay) * 0.25, (ay + by) / 2 - (bx - ax) * 0.25
    # наконечник
    import math
    ang = math.atan2(by - my, bx - mx)
    L = 34 / s
    h1 = (bx - L * math.cos(ang - 0.5), by - L * math.sin(ang - 0.5))
    h2 = (bx - L * math.cos(ang + 0.5), by - L * math.sin(ang + 0.5))
    sw_ = 9 / s
    parts.append(f'<path id="{sid}-ar" d="M{ax} {ay} Q{mx:.1f} {my:.1f} {bx} {by}" fill="none" stroke="{an}" stroke-width="{sw_:.2f}" stroke-linecap="round"/>')
    parts.append(f'<path id="{sid}-ah" d="M{h1[0]:.1f} {h1[1]:.1f} L{bx} {by} L{h2[0]:.1f} {h2[1]:.1f}" fill="none" stroke="{an}" stroke-width="{sw_:.2f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if "check" in st:
        cx, cy = st["check"]
        r = 30 / s
        parts.append(f'<g id="{sid}-ck"><circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="#22c55e"/>'
                     f'<path d="M{cx-r*0.45:.1f} {cy:.1f} L{cx-r*0.1:.1f} {cy+r*0.35:.1f} L{cx+r*0.5:.1f} {cy-r*0.35:.1f}" fill="none" stroke="#fff" stroke-width="{7/s:.2f}" stroke-linecap="round" stroke-linejoin="round"/></g>')
    svg = (f'<svg class="ann" width="{cw}" height="{ch}" viewBox="0 0 {sw} {sh}">' + "".join(parts) + "</svg>")
    chips = ""
    if st.get("chips"):
        chips = '<div class="chips">' + "".join(f'<div id="{sid}-k{i}" class="chip">«{c}»</div>' for i, c in enumerate(st["chips"])) + "</div>"
    spark = f'<div id="{sid}-sp" class="spark" style="left:{left+cw-30}px;top:{top-70}px">{SPARK.format(c=ac)}</div>'
    html.append(f"""
<section id="{sid}" class="scene clip" data-start="{t0}" data-duration="{STEP}" data-track-index="1">
  <div class="fill" style="background:{FILL[bg]}"></div>{grid}
  <div class="head">
    <span id="{sid}-n" class="kick" style="color:{ac}">ШАГ {st['n']}</span>
    <span id="{sid}-a" class="w mid" style="color:{tc};margin-top:20px">{st['a']}</span>
    <span id="{sid}-b" class="w big" style="color:{ac}">{st['b']}</span>
    <div id="{sid}-note" class="note" style="color:{tc}">{st['note']}</div>
  </div>
  <div id="{sid}-card" class="card" style="left:{left}px;top:{top+90}px;width:{cw}px;height:{ch}px">
    <div id="{sid}-cam" class="cam">
      <div class="shot"><img src="assets/{st['shot']}.jpg" alt=""></div>
      {svg}
    </div>
  </div>
  {chips}{spark}
</section>""")
    # анимация шага
    J(f'tl.fromTo("#{sid}-n",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.3}},{t0+0.02});')
    J(f'tl.fromTo("#{sid}-a",{{y:50,opacity:0}},{{y:0,opacity:1,duration:.32,ease:"power3.out"}},{t0+0.08});')
    J(f'tl.fromTo("#{sid}-b",{{y:80,opacity:0,scale:.88}},{{y:0,opacity:1,scale:1,duration:.34,ease:"power3.out"}},{t0+0.3});')
    J(f'tl.fromTo("#{sid}-note",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.3}},{t0+0.55});')
    J(f'tl.fromTo("#{sid}-card",{{y:300,opacity:0,rotation:-3}},{{y:0,opacity:1,rotation:0,duration:.55,ease:"back.out(1.3)"}},{t0+0.45});')
    # обводки и стрелка
    J(f'draw("#{sid}-c1",{t0+1.15},.45);')
    if "circle2" in st:
        J(f'draw("#{sid}-c2",{t0+2.05},.4);')
    J(f'draw("#{sid}-ar",{t0+1.4},.45);')
    J(f'tl.fromTo("#{sid}-ah",{{opacity:0,scale:.3,transformOrigin:"{bx}px {by}px"}},{{opacity:1,scale:1,duration:.22,ease:"back.out(3)"}},{t0+1.8});')
    if "check" in st:
        cx, cy = st["check"]
        J(f'tl.fromTo("#{sid}-ck",{{scale:0,transformOrigin:"{cx}px {cy}px"}},{{scale:1,duration:.35,ease:"back.out(2.5)"}},{t0+2.1});')
    # зум камеры к цели
    zx, zy, zw, zh = st["zoom"]
    zs = 1.18 if cw > 800 else 1.38
    ox, oy = (zx + zw / 2) * s, (zy + zh / 2) * s
    J(f'tl.to("#{sid}-cam",{{scale:{zs:.2f},transformOrigin:"{ox:.0f}px {oy:.0f}px",duration:.7,ease:"power2.inOut"}},{t0+2.3});')
    J(f'tl.fromTo("#{sid}-sp",{{scale:0,rotation:-90}},{{scale:1,rotation:0,duration:.45,ease:"back.out(2)"}},{t0+1.0});')
    J(f'tl.to("#{sid}-sp",{{rotation:90,duration:{STEP-1.6:.2f},ease:"none"}},{t0+1.5});')
    if st.get("chips"):
        for i in range(len(st["chips"])):
            J(f'tl.fromTo("#{sid}-k{i}",{{scale:.6,opacity:0}},{{scale:1,opacity:1,duration:.32,ease:"back.out(1.8)"}},{t0+2.6+i*0.16:.2f});')
    # переход в следующую сцену
    nxt = STEPS[idx + 1]["bg"] if idx + 1 < len(STEPS) else "ink"
    wipes.append((round(t0 + STEP - 0.35, 2), FILL[nxt], "step"))

# hook -> step1
wipes.insert(0, (round(HOOK - 0.35, 2), FILL[STEPS[0]["bg"]], "step"))

# ---------- RESULT ----------
html.append(f"""
<section id="res" class="scene clip" data-start="{T_RESULT}" data-duration="{RESULT}" data-track-index="1">
  <div class="fill" style="background:{INK}"></div><div class="grid"></div>
  <div style="position:absolute;left:80px;right:80px;top:700px;text-align:center">
    <span id="r1" class="w" style="font-size:150px;color:#fff">монтаж</span>
    <span id="r2" class="w" style="font-size:60px;color:#fff;margin-top:30px">больше не съедает</span>
    <span id="r3" class="w serif" style="font-size:130px;color:{SKY};margin-top:24px"><span class="hl">вечера<span id="r3u" class="uline"></span></span></span>
  </div>
</section>""")
J(f'tl.fromTo("#r1",{{y:80,opacity:0,scale:.88}},{{y:0,opacity:1,scale:1,duration:.34,ease:"power3.out"}},{T_RESULT+0.03});')
J(f'tl.fromTo("#r2",{{y:40,opacity:0}},{{y:0,opacity:1,duration:.32,ease:"power3.out"}},{T_RESULT+0.45});')
J(f'tl.fromTo("#r3",{{y:60,opacity:0}},{{y:0,opacity:1,duration:.34,ease:"power3.out"}},{T_RESULT+0.85});')
J(f'tl.fromTo("#r3u",{{scaleX:0}},{{scaleX:1,duration:.4,ease:"power2.out"}},{T_RESULT+1.05});')
wipes.append((round(T_CTA - 0.4, 2), CREAM, "iris"))
# у последнего шага переход в ink (результат) — уже добавлен как step

# ---------- CTA ----------
html.append(f"""
<section id="cta" class="scene clip" data-start="{T_CTA}" data-duration="{CTA}" data-track-index="1">
  <div class="fill" style="background:{CREAM}"></div>
  <div style="position:absolute;left:80px;right:80px;top:640px;text-align:center">
    <span id="c1" class="w" style="font-size:62px;color:{INK}">пиши слово</span>
    <span id="c2" class="w" style="font-size:200px;color:{BLUE};margin-top:30px">канал</span>
    <span id="c3" class="w" style="font-size:46px;color:{INK};margin-top:30px">в комментариях</span>
    <span id="c4" class="w" style="font-size:42px;color:#8b8c96;margin-top:110px;line-height:1.15"><span class="hl">получи инструкцию<br>по созданию ИИ-агента<span id="c4u" class="uline" style="background:{BLUE}"></span></span></span>
  </div>
  <div id="c-sp" class="spark" style="left:110px;top:860px">{SPARK.format(c=BLUE)}</div>
</section>""")
J(f'tl.fromTo("#c1",{{y:40,opacity:0}},{{y:0,opacity:1,duration:.32,ease:"power3.out"}},{T_CTA+0.03});')
J(f'tl.fromTo("#c2",{{y:90,opacity:0,scale:.85}},{{y:0,opacity:1,scale:1,duration:.4,ease:"back.out(1.6)"}},{T_CTA+0.25});')
J(f'tl.fromTo("#c3",{{y:40,opacity:0}},{{y:0,opacity:1,duration:.32,ease:"power3.out"}},{T_CTA+0.6});')
J(f'tl.fromTo("#c-sp",{{scale:0,rotation:-90}},{{scale:1,rotation:0,duration:.45,ease:"back.out(2)"}},{T_CTA+0.7});')
J(f'tl.fromTo("#c4",{{opacity:0}},{{opacity:1,duration:.3}},{T_CTA+1.0});')
J(f'tl.to("#c4",{{color:"{INK}",duration:.25}},{T_CTA+1.8});')
J(f'tl.fromTo("#c4u",{{scaleX:0}},{{scaleX:1,duration:.45,ease:"power2.out"}},{T_CTA+1.9});')
J(f'tl.to("#c-sp",{{rotation:90,duration:2,ease:"none"}},{T_CTA+1.2});')

# ---------- WIPES ----------
for i, (t, color, kind) in enumerate(wipes):
    wid = f"w{i}"
    if kind == "step":
        cols = "".join(f'<div class="col" style="left:{c*216}px;background:{color}"></div>' for c in range(5))
        html.append(f'<div id="{wid}" class="wipe clip" data-start="{t}" data-duration="0.35" data-track-index="5">{cols}</div>')
        J(f'tl.fromTo("#{wid} .col",{{scaleY:0}},{{scaleY:1,duration:.26,ease:"power3.inOut",stagger:.02}},{t});')
    else:
        html.append(f'<div id="{wid}" class="wipe clip" data-start="{t}" data-duration="0.4" data-track-index="5"><div class="iris"></div></div>')
        J(f'tl.fromTo("#{wid} .iris",{{scale:0}},{{scale:1,duration:.38,ease:"power3.in"}},{t});')

# ---------- CHROME ----------
html.append(f"""
<div id="chrome" class="chrome clip" data-start="0" data-duration="{TOTAL}" data-track-index="9">
  <div id="kicker" class="kicker">CHATGPT × ВИДЕО</div>
  <div id="pill" class="pill"><div class="ava">В</div><div class="meta"><span class="lab">автор</span><span class="handle">@corka_freuda</span></div></div>
  <div id="footer" class="footer">REMOTION + HYPERFRAMES</div>
</div>""")
J('tl.fromTo("#pill",{y:-30,opacity:0},{y:0,opacity:1,duration:.32,ease:"power3.out"},.05);')
J('tl.fromTo(["#kicker","#footer"],{opacity:0},{opacity:1,duration:.4},.1);')

page = f"""<!doctype html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width={W}, height={H}">
<title>ChatGPT монтирует видео — рилс</title>
<script src="gsap.min.js"></script>
<style>{css}</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}" data-duration="{TOTAL}">
{''.join(html)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
function draw(sel, t, d) {{
  const el = document.querySelector(sel);
  const len = el.getTotalLength();
  el.style.strokeDasharray = len;
  el.style.strokeDashoffset = len;
  tl.to(el, {{ strokeDashoffset: 0, duration: d, ease: "power2.out" }}, t);
}}
{chr(10).join(js)}
window.__timelines["main"] = tl;
</script>
</body></html>"""
open("build/index.html", "w").write(page)
print("TOTAL", TOTAL)
