#!/usr/bin/env python3
"""番組アートワーク artwork.png（3000x3000, RGB）を生成する。
朝焼けの空の下、地層から掘り出されかけたレコード盤 = 「音楽の発掘」。"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 3000
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
random.seed(7)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


img = Image.new("RGB", (S, S))
d = ImageDraw.Draw(img)

# 朝焼けの空
horizon = 1900
stops = [(0, (24, 18, 54)), (0.45, (120, 48, 110)), (0.8, (246, 120, 92)), (1.0, (255, 196, 120))]
for y in range(S):
    t = min(y / horizon, 1.0)
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t0 <= t <= t1:
            d.line([(0, y), (S, y)], fill=lerp(c0, c1, (t - t0) / (t1 - t0)))
            break

# 星
for _ in range(140):
    x, y = random.randrange(S), random.randrange(0, 900)
    r = random.choice([2, 3, 4, 5])
    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 240, 220))

# 朝日
sun = Image.new("RGBA", (S, S), (0, 0, 0, 0))
sd = ImageDraw.Draw(sun)
for i in range(30, 0, -1):
    r = 330 + i * 22
    sd.ellipse([S // 2 - r, horizon - r, S // 2 + r, horizon + r], fill=(255, 200, 120, 6))
sd.ellipse([S // 2 - 330, horizon - 330, S // 2 + 330, horizon + 330], fill=(255, 226, 160, 255))
img.paste(sun, (0, 0), sun)

# レコード盤（地面から半分掘り出された）
cx, cy, R = S // 2, horizon + 120, 860
rec = Image.new("RGBA", (S, S), (0, 0, 0, 0))
rd = ImageDraw.Draw(rec)
rd.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(18, 18, 22, 255))
for r in range(R - 30, 330, -18):
    shade = 34 + (r // 18 % 3) * 6
    rd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(shade, shade, shade + 6, 255), width=3)
# 光の反射
for a in range(-58, -32, 2):
    t = math.radians(a)
    rd.line([(cx + 360 * math.cos(t), cy + 360 * math.sin(t)),
             (cx + (R - 40) * math.cos(t), cy + (R - 40) * math.sin(t))], fill=(255, 190, 140, 22), width=5)
# レーベル
rd.ellipse([cx - 320, cy - 320, cx + 320, cy + 320], fill=(255, 92, 72, 255))
rd.ellipse([cx - 300, cy - 300, cx + 300, cy + 300], outline=(255, 210, 120, 255), width=10)
rd.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=(24, 18, 54, 255))
img.paste(rec, (0, 0), rec)

# 地層
layers = [(255, 0, (92, 54, 38)), (170, 1, (122, 74, 48)), (190, 2, (74, 44, 34)),
          (210, 3, (140, 92, 58)), (400, 4, (52, 32, 28))]
y0 = horizon + 260
for h, k, col in layers:
    pts = [(0, S)]
    for x in range(0, S + 100, 100):
        pts.append((x, y0 + 30 * math.sin(x / 260 + k * 1.7) + random.randint(-8, 8)))
    pts.append((S, S))
    d.polygon(pts, fill=col)
    y0 += h
# 小石
for _ in range(220):
    x, y = random.randrange(S), random.randrange(horizon + 300, S)
    r = random.randint(6, 18)
    c = random.randint(150, 200)
    d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(c, c - 30, c - 60))

# きらめき（発掘の瞬間）
def sparkle(x, y, s, col=(255, 248, 220)):
    d.polygon([(x, y - s), (x + s * 0.18, y - s * 0.18), (x + s, y), (x + s * 0.18, y + s * 0.18),
               (x, y + s), (x - s * 0.18, y + s * 0.18), (x - s, y), (x - s * 0.18, y - s * 0.18)], fill=col)

sparkle(cx + 700, cy - 640, 120)
sparkle(cx - 760, cy - 520, 80)
sparkle(cx + 880, cy - 300, 50)

# タイトル
f_big = ImageFont.truetype(FONT, 400)
f_fm = ImageFont.truetype(FONT, 330)
f_sub = ImageFont.truetype(FONT, 120)


def text_center(y, txt, font, fill, stroke=0, stroke_fill=None):
    w = d.textlength(txt, font=font)
    d.text(((S - w) / 2, y), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


shadow = img.copy()
text_center(250, "音楽の発掘", f_big, (255, 246, 230), stroke=14, stroke_fill=(40, 20, 60))
w = d.textlength("FM", font=f_fm)
pill_w = w + 160
d.rounded_rectangle([(S - pill_w) / 2, 740, (S + pill_w) / 2, 1130], radius=190, fill=(255, 92, 72))
text_center(750, "FM", f_fm, (255, 246, 230))
text_center(1210, "MORNING  DIG  RADIO", f_sub, (255, 226, 190))

img = img.filter(ImageFilter.SMOOTH)
out = os.path.join(ROOT, "artwork.png")
img.quantize(colors=256, method=Image.Quantize.MEDIANCUT).convert("RGB").save(out, optimize=True)
print("wrote", out, os.path.getsize(out) // 1024, "KB")
