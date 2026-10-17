#!/usr/bin/env python3
"""
gen_sfx.py — синтезирует недостающие звуки к библиотеке media-use (без сети, без лицензий).

Создаёт в assets/sfx-extra/:
  swipe.wav      — короткий воздушный свайп (0.35 с), для смены сцен внутри моушена
  tick.wav       — сухой тик счётчика (0.05 с)
  sub-drop.wav   — суб-удар вниз 80→35 Гц (1.2 с), под «тяжёлый» факт или тишину перед панчем
  blip.wav       — цифровой блип (0.12 с), для появления UI-элементов
  reverse-whoosh.wav — нарастающий «засос» в склейку (0.8 с)

Usage: python3 gen_sfx.py [out_dir]
"""
import numpy as np, wave, os, sys

SR = 48000
rng = np.random.default_rng(7)


def save(name, x, out):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    st = np.stack([x, np.roll(x, 14)], 1)  # лёгкий Haas → ширина
    with wave.open(os.path.join(out, name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def bandnoise(n, lo, hi):
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n)


def sweep_noise(d, f0, f1, bw=0.6):
    n = int(SR * d); out = np.zeros(n); blk = 1024
    for i in range(0, n, blk):
        fc = f0 * (f1 / f0) ** (i / n)
        out[i:i + blk] = bandnoise(blk * 4, fc * (1 - bw / 2), fc * (1 + bw / 2))[:min(blk, n - i)]
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "assets", "sfx-extra")
    os.makedirs(out, exist_ok=True)
    t = lambda d: np.linspace(0, d, int(SR * d), endpoint=False)

    d = 0.35; x = sweep_noise(d, 900, 5000); e = np.sin(np.pi * np.clip(t(d) / d, 0, 1)) ** 2
    save("swipe.wav", x * e, out)

    d = 0.05; tt = t(d); x = np.sin(2 * np.pi * 2400 * tt) * np.exp(-tt * 140) + bandnoise(len(tt), 3000, 9000) * np.exp(-tt * 300) * 0.4
    save("tick.wav", x, out)

    d = 1.2; tt = t(d); f = 80 * (35 / 80) ** (tt / d); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-tt * 2.6) * np.minimum(1, tt / 0.005)
    save("sub-drop.wav", np.tanh(x * 2.2), out)

    d = 0.12; tt = t(d); x = np.sign(np.sin(2 * np.pi * (1800 + 1600 * (tt < 0.05)) * tt)) * np.exp(-tt * 35) * 0.5
    save("blip.wav", x, out)

    d = 0.8; x = sweep_noise(d, 400, 7000, 0.8); e = (t(d) / d) ** 2.5
    x = x * e; x[-int(SR * 0.01):] *= np.linspace(1, 0, int(SR * 0.01))
    save("reverse-whoosh.wav", x, out)
    print("OK →", os.path.abspath(out))


if __name__ == "__main__":
    main()
