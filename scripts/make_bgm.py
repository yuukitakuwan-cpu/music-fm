#!/usr/bin/env python3
"""番組BGM（オリジナル、著作権フリー）を合成して assets/bgm_loop.wav に書き出す。

ローファイ寄りの、朝に合うゆったりしたループ（88BPM・8小節）。
コード: Fmaj7 | Em7 | Am7 | G6 を2周（ちょっと哀愁のある明るさ）。
エレピ風コード + ベース + やわらかいドラム。声の邪魔をしないよう中低域は控えめ。
    python3 scripts/make_bgm.py
"""
import os
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "bgm_loop.wav")
SR = 44100
BPM = 88
BEAT = 60 / BPM
BARS = 8
N = int(SR * BEAT * 4 * BARS)
rng = np.random.default_rng(7)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def place(buf, sig, t):
    i = int(t * SR)
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def epiano(freq, dur):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 200))
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    s = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 4)
         + 0.12 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 7))
    return s * env * trem


def bass(freq, dur):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 3) * (1 - np.exp(-t * 300))
    return (np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * 2 * freq * t)) * env


def kick():
    t = np.arange(int(SR * 0.35)) / SR
    f = 110 * np.exp(-t * 25) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def noise_hit(dur, decay, hp):
    n = rng.standard_normal(int(SR * dur))
    # 簡易ハイパス（差分）を hp 回
    for _ in range(hp):
        n = np.diff(n, prepend=0)
    t = np.arange(len(n)) / SR
    return n / (np.abs(n).max() + 1e-9) * np.exp(-t * decay)


# Fmaj7, Em7, Am7, G6（ボイシングは中音域）
chords = [[53, 57, 60, 64], [52, 55, 59, 62], [57, 60, 64, 67], [55, 59, 62, 64]]
roots = [41, 40, 45, 43]

keys = np.zeros(N)
bs = np.zeros(N)
dr = np.zeros(N)
for bar in range(BARS):
    c = chords[bar % 4]
    r = roots[bar % 4]
    t0 = bar * 4 * BEAT
    # コード：1拍目と2拍目裏（シンコペーション）
    for off, vel in ((0, 1.0), (1.5 * BEAT, 0.6), (3 * BEAT, 0.45)):
        for k, n in enumerate(c):
            place(keys, vel * epiano(midi(n), 2.2) * 0.22, t0 + off + k * 0.012)
    # ベース：1拍目と3拍目、4拍目裏に経過音
    place(bs, bass(midi(r), 1.2) * 0.5, t0)
    place(bs, bass(midi(r), 0.9) * 0.4, t0 + 2 * BEAT)
    place(bs, bass(midi(r + 7), 0.4) * 0.25, t0 + 3.5 * BEAT)
    # ドラム
    for b in range(4):
        tb = t0 + b * BEAT
        if b in (0, 2):
            place(dr, kick() * 0.55, tb)
        if b in (1, 3):
            place(dr, noise_hit(0.25, 18, 1) * 0.16, tb)
        for e in (0, 0.5):
            place(dr, noise_hit(0.05, 70, 2) * (0.06 if e else 0.09), tb + e * BEAT + (0.012 if e else 0))

mix = keys + bs + dr
# 軽いローパス（移動平均）で角を取る
k = 4
mix = np.convolve(mix, np.ones(k) / k, mode="same")
# ループのつなぎ目をなめらかに：末尾の余韻を先頭に足し込む
mix = mix / (np.abs(mix).max() + 1e-9) * 0.8
stereo = np.stack([mix, np.roll(mix, int(SR * 0.008))], axis=1)  # わずかに広げる
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype("<i2").tobytes())
print("wrote", OUT, f"{N / SR:.1f}s")
