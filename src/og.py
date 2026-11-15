"""OG image + touch icon for The Radio Wheel: an original radio wheel on a dashboard. No game art, logos or brand assets."""
import math, os, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
H = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("RW_OUT", "/home/claude/radiowheel")
T = lambda n, s: ImageFont.truetype(f"{H}/ttf/{n}.ttf", s)
W, Hh = 1200, 630
DASH, LINE, INK, MUTED, LCD, ACC, WEDGE = (13, 14, 18), (42, 46, 56), (233, 227, 214), (143, 136, 153), (255, 180, 58), (232, 70, 27), (30, 33, 42)
im = Image.new("RGB", (W, Hh), DASH)
glow = Image.new("RGB", (W, Hh), (0, 0, 0)); ImageDraw.Draw(glow).ellipse([700, -200, 1400, 500], fill=(34, 36, 48)); im = Image.blend(im, glow.filter(ImageFilter.GaussianBlur(120)), .7)
d = ImageDraw.Draw(im)
# tuner scale along the top
x0, x1, y = 60, 1140, 44
d.line([(x0, y), (x1, y)], fill=LINE, width=1); d.line([(x0, y + 34), (x1, y + 34)], fill=LINE, width=1)
for i, f in enumerate(range(88, 109)):
    x = x0 + (x1 - x0) * i / 20
    d.line([(x, y), (x, y + (12 if f % 2 == 0 else 7))], fill=MUTED, width=1)
    if f % 2 == 0:
        d.text((x, y + 16), str(f), font=T("vt323-latin-400-normal", 18), fill=MUTED, anchor="mt")
nx = x0 + (x1 - x0) * (102.5 - 88) / 20
d.line([(nx, y - 8), (nx, y + 42)], fill=ACC, width=3)
# wheel
cx, cy, ro, ri = 905, 360, 228, 108
names = ["NSP", "WCC", "FLYL", "LSR", "SOUL", "BLUE", "WWFM", "CX", "LAB", "MIRR", "SPAC", "LOWD", "KULT", "VINE", "EL", "REBE"]
n = len(names)
wl = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); q = ImageDraw.Draw(wl)
q.ellipse([cx - ro - 6, cy - ro - 6, cx + ro + 6, cy + ro + 6], fill=(8, 9, 12, 255), outline=LINE + (255,))
for i, nm in enumerate(names):
    a0, a1 = -90 + i * 360 / n + .9, -90 + (i + 1) * 360 / n - .9
    pts = [(cx + ro * math.cos(math.radians(a0 + (a1 - a0) * k / 12)), cy + ro * math.sin(math.radians(a0 + (a1 - a0) * k / 12))) for k in range(13)]
    pts += [(cx + ri * math.cos(math.radians(a1 - (a1 - a0) * k / 12)), cy + ri * math.sin(math.radians(a1 - (a1 - a0) * k / 12))) for k in range(13)]
    q.polygon(pts, fill=(ACC if i == 0 else WEDGE) + (255,))
    am = math.radians((a0 + a1) / 2); rm = (ro + ri) / 2
    q.text((cx + rm * math.cos(am), cy + rm * math.sin(am)), nm, font=T("bungee-latin-400-normal", 19), fill=(255, 255, 255, 255) if i == 0 else INK + (255,), anchor="mm")
q.ellipse([cx - ri + 8, cy - ri + 8, cx + ri - 8, cy + ri - 8], fill=(18, 15, 8, 255), outline=(43, 35, 18, 255), width=2)
q.text((cx, cy - 26), "NON-STOP", font=T("vt323-latin-400-normal", 36), fill=LCD + (255,), anchor="mm")
q.text((cx, cy + 6), "POP FM", font=T("vt323-latin-400-normal", 36), fill=LCD + (255,), anchor="mm")
q.text((cx, cy + 40), "42 SONGS", font=T("vt323-latin-400-normal", 22), fill=(185, 134, 44, 255), anchor="mm")
sh = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([cx - ro, cy - ro + 24, cx + ro, cy + ro + 24], fill=(0, 0, 0, 160))
im = im.convert("RGBA"); im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22))); im.alpha_composite(wl)
d = ImageDraw.Draw(im)
n_src = sys.argv[1] if len(sys.argv) > 1 else ""
n_songs = sys.argv[2] if len(sys.argv) > 2 else ""
d.text((60, 130), "COLD.FYI DEEP DIVE NO. 10", font=T("ibm-plex-mono-latin-600-normal", 20), fill=LCD)
d.text((56, 170), "THE RADIO", font=T("bungee-latin-400-normal", 92), fill=(255, 255, 255))
d.text((56, 268), "WHEEL", font=T("bungee-latin-400-normal", 92), fill=(255, 255, 255))
d.text((60, 392), "How Rockstar Games does music: every", font=T("source-serif-4-latin-400-italic", 30), fill=INK)
d.text((60, 432), "station, host, song and talk show.", font=T("source-serif-4-latin-400-italic", 30), fill=INK)
d.rectangle([0, Hh - 10, W, Hh], fill=ACC)
foot = "RADIOWHEEL.COLD.FYI" + (f"  ·  {n_songs} SONGS" if n_songs else "") + (f"  ·  {n_src} SOURCES" if n_src else "")
d.text((60, 540), foot, font=T("ibm-plex-mono-latin-600-normal", 20), fill=MUTED)
im.convert("RGB").save(f"{OUT}/og.png", optimize=True)
ic = Image.new("RGB", (180, 180), DASH); z = ImageDraw.Draw(ic)
for i in range(8):
    a0, a1 = -90 + i * 45 + 2, -90 + (i + 1) * 45 - 2
    pts = [(90 + 82 * math.cos(math.radians(a0 + (a1 - a0) * k / 8)), 90 + 82 * math.sin(math.radians(a0 + (a1 - a0) * k / 8))) for k in range(9)]
    pts += [(90 + 42 * math.cos(math.radians(a1 - (a1 - a0) * k / 8)), 90 + 42 * math.sin(math.radians(a1 - (a1 - a0) * k / 8))) for k in range(9)]
    z.polygon(pts, fill=ACC if i == 0 else WEDGE)
z.ellipse([56, 56, 124, 124], fill=LCD)
ic.save(f"{OUT}/apple-touch-icon.png")
print("og ok")
