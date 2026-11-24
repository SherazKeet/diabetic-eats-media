"""Diabetic Eats reel renderer v4 — 5 styles, cartoon characters, phoneme lip sync.

Usage: python3 render.py script.json out.mp4

Top level of script.json:
  "style":   talk | fight | quiz | kitchen | countdown   (default talk)
  "voice":   "af_heart", "speed": 1.15
  "mascot":  "🥦" (small talking mascot, top-left; wears a chef hat in kitchen style)
  "bg_icons": ["🍿","🥜"]  (floating background icons)
  "scenes":  [SCENE, ...]

Every SCENE: "say" (narration), optional "headline", "sub", "accent" (hex), "footer",
"mood" (happy|sad|fight|surprised), and ONE visual:
  "character": "🥦", "with": ["🍿"]                 big talking cartoon food (+ props)
  "emoji": [...], "faces": true                      bouncing icons (faces: cartoon, first one talks)
  "items": [["✅","Label"], ...]                     checklist revealed as spoken
  "steps": [["🍳","Cook 3 min"], ...]                numbered recipe steps revealed as spoken
  "swap":  [["🥔","Chips"],["🍿","Popcorn"]]         this -> that with ❌/✅ stamps
  "stat":  [["HONEY","17g"],["SUGAR","12g"]]         count-up number cards
  "fight": {"left":["🍿","POPCORN"], "right":["🥔","CHIPS"],
            "bars":[["FIBER", 3.5, 1, "g", "high"]], "winner":"left"}   versus battle
  "quiz":  {"statement":"...", "label":"TRUE OR FALSE?", "character":["🍪","surprised"]}  question + 3-2-1 timer
  "reveal":{"answer":"myth"|"fact", "statement":"short version"}                          MYTH/FACT stamp
  "plate": {"items":[["🥚","2 eggs"], ...], "badges":[["PROTEIN","14g"]], "faces":true}    ingredients drop on a plate
  "rank":  {"n":3, "of":3, "item":"🥧", "mood":"sad"}                                     countdown rank card
"""
import json, sys, os, subprocess, math, random
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
TTS = os.environ.get("TTS_DIR", "/home/claude/tts")
FONT_HEAD = "/usr/share/fonts/truetype/google-fonts/ofl/anton/Anton-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_MED = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
WHITE = (255, 255, 255)
CREAM = (255, 248, 230)
INK = (30, 25, 25)
GOLD = (255, 214, 0)
GOOD = (110, 215, 100)
BAD = (255, 105, 90)
DEFAULT_BG_ICONS = ["🥦", "🍎", "🥑", "🥕", "🫐", "🥗", "🍋", "🥚"]

STYLES = {
    "talk":      dict(bg=((10, 52, 40), (4, 28, 22)), rays=None, head=CREAM, sub=(210, 235, 222),
                      tag=(200, 230, 215), track=(40, 80, 66), palpha=0.16, light=False, accent="#B6F35C"),
    "fight":     dict(bg="split", rays=(255, 255, 255, 14), head=CREAM, sub=(235, 228, 245),
                      tag=(240, 235, 250), track=(80, 55, 95), palpha=0.10, light=False, accent="#FFD600"),
    "quiz":      dict(bg=((34, 44, 128), (10, 12, 52)), rays=(255, 255, 255, 13), head=CREAM, sub=(210, 220, 255),
                      tag=(210, 220, 255), track=(55, 65, 140), palpha=0.12, light=False, accent="#FFD600"),
    "kitchen":   dict(bg=((255, 247, 234), (255, 216, 172)), rays=None, head=(78, 44, 20), sub=(125, 80, 45),
                      tag=(140, 92, 55), track=(240, 205, 165), palpha=0.24, light=True, accent="#E07B28"),
    "countdown": dict(bg=((255, 138, 60), (165, 28, 98)), rays=(255, 255, 255, 20), head=WHITE, sub=(255, 236, 226),
                      tag=(255, 236, 226), track=(200, 80, 95), palpha=0.14, light=False, accent="#FFD600"),
}

def hex2rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def clamp(t): return max(0.0, min(1.0, t))
def ease_out(t): t = clamp(t); return 1 - (1-t)**3
def ease_out_back(t):
    t = clamp(t); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3*(t-1)**3 + c1*(t-1)**2

_fonts = {}
def font(path, size):
    if (path, size) not in _fonts: _fonts[(path, size)] = ImageFont.truetype(path, size)
    return _fonts[(path, size)]

# ---------------- emoji / text helpers ----------------
_emoji_cache = {}
def emoji_img(ch, size, alpha=1.0):
    size = max(1, int(size))
    key = (ch, size, alpha)
    if key not in _emoji_cache:
        bk = (ch, "base")
        if bk not in _emoji_cache:
            f = ImageFont.truetype(FONT_EMOJI, 109)
            im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((90, 90), ch, font=f, embedded_color=True, anchor="mm")
            _emoji_cache[bk] = im.crop(im.getbbox() or (0, 0, 180, 180))
        im = _emoji_cache[bk]
        s = size / max(im.size)
        im = im.resize((max(1, int(im.width*s)), max(1, int(im.height*s))), Image.LANCZOS)
        if alpha < 1: im.putalpha(im.getchannel("A").point(lambda v: int(v*alpha)))
        _emoji_cache[key] = im
    return _emoji_cache[key]

def scaled(img, sx, sy=None):
    sy = sx if sy is None else sy
    sx, sy = max(0.01, sx), max(0.01, sy)
    if abs(sx-1) < 0.01 and abs(sy-1) < 0.01: return img
    return img.resize((max(1, int(img.width*sx)), max(1, int(img.height*sy))), Image.BILINEAR)

def paste_c(dst, img, cx, cy):
    dst.alpha_composite(img, (int(cx - img.width/2), int(cy - img.height/2)))

def wrap(draw, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= maxw: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

_cmaps = {}
def font_has(path, ch):
    if path not in _cmaps:
        try:
            from fontTools.ttLib import TTFont
            _cmaps[path] = set(TTFont(path).getBestCmap().keys())
        except Exception:
            _cmaps[path] = None
    cm = _cmaps[path]
    return True if cm is None else (ord(ch) in cm)

SYMBOL_WORDS = {"≠": " ISN'T ", "→": " TO ", "➜": " TO ", "➡": " TO ", "➡️": " TO ", "=": " = ", "&": " & ",
                "≈": " ~", "×": "X", "÷": "/", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"'}
def sanitize(text, path):
    """Replace symbols the font can't draw (so '≠' never renders as '=')."""
    text = text.replace("≠", " ISN'T ")          # always: a thin slash can vanish and flip the meaning
    for k, v in SYMBOL_WORDS.items():
        if k in text and not all(font_has(path, ch) for ch in k): text = text.replace(k, v)
    text = "".join(ch for ch in text if ch == " " or font_has(path, ch))
    return " ".join(text.split())

def fit_font(draw, text, path, start, maxw, maxlines):
    size = start
    while size > 40:
        f = font(path, size)
        if len(wrap(draw, text, f, maxw)) <= maxlines: return f
        size -= 6
    return font(path, size)

_text_cache = {}
def text_img(txt, fnt, fill, shadow=(0, 0, 0, 120), stroke=0, stroke_fill=None):
    key = (txt, fnt.path, fnt.size, fill, shadow, stroke, stroke_fill)
    if key not in _text_cache:
        bb = fnt.getbbox(txt, stroke_width=stroke)
        pad = 16 + stroke
        im = Image.new("RGBA", (bb[2]-bb[0]+pad*2, bb[3]-bb[1]+pad*2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        ox, oy = pad-bb[0], pad-bb[1]
        if shadow: d.text((ox+5, oy+6), txt, font=fnt, fill=shadow, stroke_width=stroke, stroke_fill=shadow)
        d.text((ox, oy), txt, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        _text_cache[key] = im
    return _text_cache[key]

def pill(text, fnt, fill, color, padx=30, h=None):
    tw = fnt.getlength(text); h = h or int(fnt.size*1.6)
    im = Image.new("RGBA", (int(tw + padx*2), h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width-1, h-1], h//2, fill=fill)
    d.text((im.width/2, h/2), text, font=fnt, fill=color, anchor="mm")
    return im

# ---------------- backgrounds ----------------
def make_bg(style):
    st = STYLES[style]
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    arr = np.zeros((H, W, 3), np.float32)
    if st["bg"] == "split":
        left, right, dark = np.array([175, 42, 58.]), np.array([38, 72, 178.]), np.array([18, 10, 28.])
        boundary = 0.62 - 0.24*y
        m = (x < boundary).astype(np.float32)
        g = np.clip(y*0.9, 0, 1)*0.65
        for i in range(3): arr[..., i] = (left[i]*m + right[i]*(1-m))*(1-g) + dark[i]*g
        glowl = np.clip(1 - np.abs(x - boundary)/0.010, 0, 1)
        arr += glowl[..., None]*np.array([255, 225, 120.])*0.9
    else:
        c1, c2 = st["bg"]
        g = np.clip(y*0.85 + (x-0.5)**2*0.6, 0, 1)
        for i in range(3): arr[..., i] = c1[i]*(1-g) + c2[i]*g
    if not st["light"]:
        v = np.clip(1 - 0.45*((x-0.5)**2*1.6 + (y-0.45)**2*0.9), 0.55, 1)
        arr *= v[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    if style == "kitchen":
        d = ImageDraw.Draw(im)
        for row, yy in enumerate(range(60, 1640, 110)):           # soft polka dots
            for xx in range(60 + (row % 2)*55, W, 110):
                d.ellipse([xx-9, yy-9, xx+9, yy+9], fill=(255, 226, 196))
        for yy in range(1660, H, 52):                              # gingham tablecloth strip
            for xx in range(0, W, 52):
                a = ((xx//52) + (yy//52)) % 2
                d.rectangle([xx, yy, xx+51, yy+51], fill=(235, 120, 110) if a else (250, 236, 226))
    return im

_bg_cache = {}
def bg(style):
    if style not in _bg_cache: _bg_cache[style] = make_bg(style)
    return _bg_cache[style]

def draw_rays(frame, col, t, cx=540, cy=600, n=16):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    rot = t*0.12; R = 2600
    for i in range(n):
        a0 = rot + i*2*math.pi/n; a1 = a0 + math.pi/n
        d.polygon([(cx, cy), (cx+R*math.cos(a0), cy+R*math.sin(a0)), (cx+R*math.cos(a1), cy+R*math.sin(a1))], fill=col)
    frame.alpha_composite(layer)

def make_glow(color, r=320):
    s = r*2
    yy, xx = np.mgrid[0:s, 0:s]
    dd = np.sqrt((xx-r)**2 + (yy-r)**2)/r
    a = (np.clip(1-dd, 0, 1)**2.2*150).astype(np.uint8)
    arr = np.zeros((s, s, 4), np.uint8); arr[..., :3] = color; arr[..., 3] = a
    return Image.fromarray(arr, "RGBA")

_glow_cache = {}
def glow(color):
    if color not in _glow_cache: _glow_cache[color] = make_glow(color)
    return _glow_cache[color]

class Particles:
    def __init__(self, icons, seed, alpha):
        rnd = random.Random(seed); self.alpha = alpha; self.p = []
        for _ in range(11):
            self.p.append(dict(e=rnd.choice(icons), x=rnd.uniform(40, W-40), y=rnd.uniform(0, H),
                               v=rnd.uniform(25, 60), sw=rnd.uniform(15, 40), ph=rnd.uniform(0, 6.28),
                               size=rnd.randint(60, 110)))
    def draw(self, layer, t):
        for q in self.p:
            y = (q["y"] - q["v"]*t) % (H + 200) - 100
            x = q["x"] + math.sin(t*0.9 + q["ph"])*q["sw"]
            paste_c(layer, emoji_img(q["e"], q["size"], self.alpha), x, y)

class Confetti:
    COLS = [(255, 214, 0), (255, 90, 90), (90, 200, 255), (120, 220, 100), (255, 140, 220), (255, 255, 255)]
    def __init__(self, x, y, seed, n=80):
        rnd = random.Random(seed); self.p = []
        for _ in range(n):
            ang = rnd.uniform(-math.pi*0.95, -math.pi*0.05); sp = rnd.uniform(500, 1150)
            self.p.append((x, y, math.cos(ang)*sp, math.sin(ang)*sp - 150, rnd.uniform(0, 6.28),
                           rnd.uniform(-9, 9), rnd.choice(self.COLS), rnd.randint(9, 17)))
    def draw(self, d, tt):
        if tt < 0 or tt > 2.6: return
        for (x, y, vx, vy, rot, vr, col, sz) in self.p:
            px = x + vx*tt*0.85; py = y + vy*tt + 700*tt*tt
            r = rot + vr*tt; c, s = math.cos(r), math.sin(r)
            pts = [(px + dx*c - dy*s, py + dx*s + dy*c) for dx, dy in ((-sz, -sz*0.5), (sz, -sz*0.5), (sz, sz*0.5), (-sz, sz*0.5))]
            d.polygon(pts, fill=col)

# ---------------- cartoon faces + lip sync ----------------
# (eye_y, mouth_y, eye_dx) as fractions of the icon box
FACE_POS = {"🥦": (0.36, 0.50, 0.15), "🥕": (0.50, 0.63, 0.12), "🍿": (0.66, 0.80, 0.14),
            "🥑": (0.40, 0.53, 0.14), "🍎": (0.55, 0.72, 0.15), "🍅": (0.55, 0.72, 0.15),
            "🥔": (0.48, 0.64, 0.15), "🍋": (0.50, 0.66, 0.15), "🫐": (0.55, 0.72, 0.14),
            "🍞": (0.52, 0.70, 0.15), "🥚": (0.52, 0.70, 0.13), "🍓": (0.50, 0.66, 0.13),
            "🧁": (0.66, 0.82, 0.13), "🍩": (0.40, 0.68, 0.17), "🍪": (0.48, 0.66, 0.15),
            "🍊": (0.55, 0.72, 0.15), "🍌": (0.50, 0.64, 0.12), "🥜": (0.45, 0.62, 0.12),
            "🍯": (0.62, 0.78, 0.14), "🥗": (0.50, 0.66, 0.15), "🍇": (0.50, 0.66, 0.14),
            "🌽": (0.50, 0.65, 0.12), "🥒": (0.50, 0.64, 0.12), "🍗": (0.45, 0.60, 0.13),
            "🥧": (0.55, 0.72, 0.15), "🍠": (0.50, 0.65, 0.14), "🫑": (0.55, 0.70, 0.14),
            "🍐": (0.58, 0.74, 0.13), "🍑": (0.55, 0.72, 0.15), "🥛": (0.58, 0.74, 0.12),
            "🧃": (0.55, 0.72, 0.13), "🥤": (0.58, 0.74, 0.13), "🍫": (0.48, 0.64, 0.15),
            "🍰": (0.60, 0.76, 0.14), "🥯": (0.42, 0.66, 0.16), "🥐": (0.50, 0.66, 0.15),
            "🍚": (0.60, 0.76, 0.15), "🍝": (0.58, 0.74, 0.15), "🍕": (0.45, 0.60, 0.13),
            "🍔": (0.52, 0.68, 0.15), "🍟": (0.62, 0.78, 0.14), "🥥": (0.52, 0.68, 0.15)}
DEFAULT_FACE = (0.55, 0.72, 0.15)

# mouth params: open, width, round, teeth_top, teeth_bottom, tongue
VIS = {"rest": (0.0, 1.0, 0.0, 0, 0, 0), "mbp": (0.0, 0.85, 0.0, 0, 0, 0),
       "aa": (1.0, 1.05, 0.0, 1, 0, 1), "eh": (0.62, 1.1, 0.0, 1, 0, 1),
       "ee": (0.38, 1.32, 0.0, 1, 1, 0), "oo": (0.62, 0.55, 1.0, 0, 0, 0),
       "r": (0.42, 0.75, 0.6, 0, 0, 0), "fv": (0.22, 1.0, 0.0, 1, 0, 0),
       "s": (0.28, 1.22, 0.0, 1, 1, 0), "t": (0.36, 1.05, 0.0, 1, 0, 1),
       "k": (0.46, 1.0, 0.0, 0, 0, 1)}
REST = np.array(VIS["rest"], np.float32)
PH2VIS = {}
for chs, v in [("pbm", "mbp"), ("fv", "fv"), ("szʃʒʧʤ", "s"), ("tdnlɾθðʔ", "t"), ("kɡgŋhxç", "k"),
               ("wʍ", "oo"), ("ɹr", "r"), ("j", "ee"), ("ɑaæʌɐIW", "aa"), ("ɛeəɚɝᵻA", "eh"),
               ("iɪ", "ee"), ("uʊoɔOYɒ", "oo")]:
    for ch in chs: PH2VIS[ch] = v

def mouth_track(timings, n_frames, offset, env):
    """Per-frame mouth parameters from phoneme timings (falls back to loudness)."""
    out, cur = [], REST.copy()
    if not timings:
        for fi in range(n_frames):
            lv = env[fi] if fi < len(env) else 0
            tgt = np.array(VIS["eh"] if lv > 0.12 else VIS["rest"], np.float32)
            tgt[0] *= lv
            cur[:3] += (tgt[:3]-cur[:3])*0.6; cur[3:] = tgt[3:]
            out.append(cur.copy())
        return out
    segs, tms = [], list(timings)
    for i, tm in enumerate(tms):
        p = tm.phoneme
        if p in "ˈˌ":
            v = "eh"
            for j in range(i+1, min(i+4, len(tms))):
                if tms[j].phoneme in PH2VIS: v = PH2VIS[tms[j].phoneme]; break
        elif p == "ː": v = segs[-1][2] if segs else "eh"
        elif p == " ": v = "gap"
        else: v = PH2VIS.get(p, "rest")
        segs.append((tm.start + offset, tm.end + offset, v))
    prev = "rest"
    for fi in range(n_frames):
        t = fi/FPS + 0.035                     # mouth leads the sound slightly, like hand animation
        v, sd = "rest", 0.0
        for (s0, s1, vv) in segs:
            if s0 <= t < s1: v, sd = vv, s1 - s0; break
        if v == "gap":
            tgt = np.array(VIS["rest"] if sd > 0.09 else VIS[prev], np.float32)
            if sd <= 0.09: tgt[0] *= 0.45
        else:
            tgt = np.array(VIS[v], np.float32)
            if v != "rest": prev = v
        lv = env[fi] if fi < len(env) else 0
        if tgt[0] > 0: tgt[0] *= (0.72 + 0.28*min(1.0, lv))
        k = 0.92 if v == "mbp" else 0.62
        cur[:3] += (tgt[:3]-cur[:3])*k; cur[3:] = tgt[3:]
        out.append(cur.copy())
    return out

def draw_mouth(im, cx, cy, S, prm, mood):
    op, wd, rd, tt, tb, tg = [float(v) for v in prm]
    d = ImageDraw.Draw(im)
    ol = max(2, int(S*0.016))
    mw = S*0.2*wd
    if op < 0.08:
        if mood == "sad":
            d.arc([cx-mw*0.45, cy, cx+mw*0.45, cy+S*0.12], 205, 335, fill=INK, width=ol+1)
        elif mood == "surprised":
            r = S*0.035; d.ellipse([cx-r, cy-r, cx+r, cy+r*1.3], fill=(96, 20, 32), outline=INK, width=ol)
        elif wd < 0.93:
            d.line([(cx-mw*0.42, cy+S*0.01), (cx+mw*0.42, cy+S*0.01)], fill=INK, width=ol+2)
        else:
            d.arc([cx-mw*0.5, cy-S*0.08, cx+mw*0.5, cy+S*0.06], 20, 160, fill=INK, width=ol+1)
        return
    mh = S*0.2*op; sq = 1 - 0.3*rd
    top, bot = [], []
    for i in range(21):
        x = -1 + 2*i/20; s = math.sqrt(max(0.0, 1-x*x))
        px = cx + x*mw/2*sq
        top.append((px, cy - mh*(0.12*(1-rd) + 0.5*rd)*s))
        bot.append((px, cy + mh*(0.88*(1-rd) + 0.5*rd)*s))
    poly = top + bot[::-1]
    x0, y0 = int(cx - mw/2 - 6), int(cy - mh*0.6 - 6)
    x1, y1 = int(cx + mw/2 + 6), int(cy + mh + 6)
    mask = Image.new("L", (x1-x0, y1-y0), 0)
    ImageDraw.Draw(mask).polygon([(px-x0, py-y0) for px, py in poly], fill=255)
    inner = Image.new("RGBA", (x1-x0, y1-y0), (96, 20, 32, 255)); di = ImageDraw.Draw(inner)
    cyl = cy - y0; top_y = cyl - mh*(0.12*(1-rd) + 0.5*rd)
    if tg: di.ellipse([inner.width/2 - mw*0.3*sq, cyl + mh*0.4, inner.width/2 + mw*0.3*sq, cyl + mh*1.15], fill=(236, 108, 128, 255))
    if tt: di.rectangle([0, 0, inner.width, top_y + mh*0.22], fill=(255, 255, 255, 255))
    if tb: di.rectangle([0, cyl + mh*0.62, inner.width, inner.height], fill=(255, 255, 255, 255))
    im.paste(inner, (x0, y0), mask)
    d.line(poly + [poly[0]], fill=INK, width=ol, joint="curve")

def draw_eyes(im, cx, ey, S, edx, t, seed, mood):
    d = ImageDraw.Draw(im)
    er = S*0.085*(1.15 if mood == "surprised" else 1.0)
    ol = max(2, int(S*0.014))
    period = 2.6 + (seed % 5)*0.2
    blink = ((t + seed*0.37) % period) < 0.12 and mood != "surprised"
    look = math.sin(t*0.8 + seed)*er*0.25
    for sx in (-1, 1):
        ex = cx + sx*S*edx
        if blink:
            d.arc([ex-er, ey-er*0.6, ex+er, ey+er*0.6], 200, 340, fill=INK, width=ol+1)
        else:
            d.ellipse([ex-er, ey-er*1.12, ex+er, ey+er*1.12], fill=WHITE, outline=INK, width=ol)
            pr = er*(0.42 if mood == "surprised" else 0.52); px = ex + look; py = ey + er*0.15
            d.ellipse([px-pr, py-pr, px+pr, py+pr], fill=(25, 22, 22))
            hr = pr*0.38
            d.ellipse([px-pr*0.35-hr, py-pr*0.4-hr, px-pr*0.35+hr, py-pr*0.4+hr], fill=WHITE)
        bw = max(3, int(S*0.03)); by = ey - er*1.5
        inner_x, outer_x = ex - sx*er*0.95, ex + sx*er*0.95
        if mood == "fight":
            d.line([(outer_x, by - er*0.2), (inner_x, by + er*0.4)], fill=INK, width=bw)
        elif mood == "sad":
            d.line([(outer_x, by + er*0.3), (inner_x, by - er*0.25)], fill=INK, width=bw)
        elif mood == "surprised":
            d.arc([ex-er, by-er*0.7, ex+er, by+er*0.5], 205, 335, fill=INK, width=bw)
    if mood != "sad":
        blush = Image.new("RGBA", im.size, (0, 0, 0, 0)); bd = ImageDraw.Draw(blush)
        for sx in (-1, 1):
            bx = cx + sx*(S*edx + er*0.9); by = ey + er*1.6
            bd.ellipse([bx-er*0.75, by-er*0.4, bx+er*0.75, by+er*0.4], fill=(255, 110, 140, 105))
        im.alpha_composite(blush)

def add_chef_hat(im):
    w, h = im.size; S = min(w, h); extra = int(S*0.45)
    can = Image.new("RGBA", (w, h + extra*2), (0, 0, 0, 0)); can.alpha_composite(im, (0, extra))
    d = ImageDraw.Draw(can); ol = max(2, int(S*0.012)); hx = w/2; hb = extra + h*0.10; bw = S*0.46
    for dx, dy, r in [(-0.15, -0.24, 0.14), (0.15, -0.24, 0.14), (0.0, -0.30, 0.17)]:
        d.ellipse([hx+dx*S-r*S, hb+dy*S-r*S, hx+dx*S+r*S, hb+dy*S+r*S], fill=WHITE, outline=(195, 195, 205), width=ol)
    d.rounded_rectangle([hx-bw/2, hb-S*0.16, hx+bw/2, hb], radius=int(S*0.03), fill=WHITE, outline=(195, 195, 205), width=ol)
    return can

HAS_OWN_FACE = set("🎃🦃🐔🐓🐟🐄🐖🐑🐐🐝🐻🐶🐱🐮🐷🌞🌝🌚⛄🤖👻💩") | {chr(c) for c in range(0x1F600, 0x1F650)} | {chr(c) for c in range(0x1F910, 0x1F930)}
def char_img(ch, size, t, prm=None, seed=0, mood="happy", hat=False, gray=0.0):
    if ch in HAS_OWN_FACE:   # already has a face: just animate it
        base = emoji_img(ch, size)
        if gray > 0: base = Image.blend(base, base.convert("LA").convert("RGBA"), gray)
        return scaled(base, 1 + 0.03*math.sin(t*5.0 + seed), 1 - 0.03*math.sin(t*5.0 + seed))
    base = emoji_img(ch, size).copy()
    w, h = base.size; S = min(w, h)
    ey, my, edx = FACE_POS.get(ch, DEFAULT_FACE)
    prm = REST if prm is None else prm
    draw_eyes(base, w/2, h*ey, S, edx, t, seed, mood)
    draw_mouth(base, w/2, h*my, S, prm, mood)
    if gray > 0:
        g = base.convert("LA").convert("RGBA")
        base = Image.blend(base, g, gray)
    if hat: base = add_chef_hat(base)
    op = float(prm[0])
    sx = 1 + 0.03*math.sin(t*5.0 + seed) - 0.03*op
    sy = 1 - 0.03*math.sin(t*5.0 + seed) + 0.05*op
    return scaled(base, sx, sy)

# ---------------- scene context ----------------
class Ctx: pass

def item_colors(c):
    if c.st["light"]: return (255, 255, 255, 215), (70, 40, 20)
    return (255, 255, 255, 34), CREAM

def sc_character(c):
    ch = c.sc["character"]; props = c.sc.get("with", []); top = 330; cy = top + 210
    a = ease_out_back((c.ta - 0.05)/0.5)
    if not c.st["light"]: paste_c(c.layer, scaled(glow(c.accent), (1 + 0.06*math.sin(c.ta*3.2))*ease_out(c.ta/0.5)), W//2, cy)
    if a > 0:
        ci = char_img(ch, 400*a, c.ta, c.mouth, c.idx, c.mood, hat=c.style == "kitchen")
        paste_c(c.layer, ci, W//2, cy - abs(math.sin(c.ta*3.0))*18)
    for k, e in enumerate(props[:2]):
        pa = ease_out_back((c.ta - 0.35 - k*0.2)/0.45)
        if pa <= 0: continue
        pi = emoji_img(e, 170*pa).rotate(math.sin(c.ta*2 + k)*10, resample=Image.BICUBIC, expand=True)
        paste_c(c.layer, pi, W//2 + (-1 if k == 0 else 1)*330, cy + 90 + math.sin(c.ta*2.6 + k)*12)
    return top + 470

def sc_emoji(c):
    emojis = c.sc["emoji"]; faces = c.sc.get("faces", False); top = 330
    n_e = len(emojis); size = 300 if n_e == 1 else (240 if n_e == 2 else 190 if n_e == 3 else 170)
    gap = 30; tot = n_e*size + (n_e-1)*gap; x0 = (W - tot)//2
    gl = scaled(glow(c.accent), (0.9 if n_e == 1 else 1.25)*(1 + 0.06*math.sin(c.ta*3.2))*ease_out(c.ta/0.5))
    if not c.st["light"]: paste_c(c.layer, gl, W//2, top + 160)
    for k, e in enumerate(emojis):
        a = ease_out_back((c.ta - 0.1 - k*0.15)/0.5)
        if a <= 0: continue
        bob = math.sin(c.ta*2.4 + k*1.3)*14; wob = math.sin(c.ta*1.8 + k)*6
        if faces: ei = char_img(e, size*a, c.ta, c.mouth if k == 0 else None, c.idx*3+k, c.mood)
        else: ei = emoji_img(e, size*a)
        if abs(wob) > 0.5: ei = ei.rotate(wob, resample=Image.BICUBIC, expand=True)
        paste_c(c.layer, ei, x0 + k*(size+gap) + size//2, top + 160 + bob)
    return top + 400

def sc_items(c, numbered=False):
    items = c.sc["steps"] if numbered else c.sc["items"]; n = len(items)
    rowh, y0 = 150, 290; fill, tcol = item_colors(c); fitem = font(FONT_BOLD, 56 if numbered else 60)
    for k, (ic, label) in enumerate(items):
        start = 0.2 + (k/n)*c.speak_end*0.75
        a = ease_out((c.ta - start)/0.35)
        if a <= 0: continue
        y = y0 + k*rowh; xo = int((1-a)*120)
        p = Image.new("RGBA", (W-140, rowh-24), (0, 0, 0, 0)); pd = ImageDraw.Draw(p)
        pd.rounded_rectangle([0, 0, p.width-1, p.height-1], 34, fill=fill[:3] + (int(fill[3]*a),))
        pd.text((150, p.height//2), label, font=fitem, fill=tcol + (int(255*a),), anchor="lm")
        c.layer.alpha_composite(p, (70 + xo, y))
        pop = ease_out_back((c.ta - start - 0.05)/0.4)
        if pop <= 0: continue
        if numbered:
            r = 44*pop; cxn, cyn = 70 + 75 + xo, y + (rowh-24)//2
            c.dr.ellipse([cxn-r, cyn-r, cxn+r, cyn+r], fill=c.accent)
            c.dr.text((cxn, cyn+2), str(k+1), font=font(FONT_HEAD, int(62*pop)+1), fill=INK, anchor="mm")
            paste_c(c.layer, emoji_img(ic, 88*pop), W - 140, cyn)
        else:
            paste_c(c.layer, emoji_img(ic, 90*pop), 70 + 75 + xo, y + (rowh-24)//2)
    return y0 + n*rowh + 40

def sc_swap(c):
    (fe, fl), (te, tl) = c.sc["swap"]; top = 330; cy = top + 170
    fill, tcol = item_colors(c); fs = font(FONT_BOLD, 44)
    a1 = ease_out_back((c.ta-0.1)/0.45); a2 = ease_out_back((c.ta-0.7)/0.45)
    for (e, lab, cx, a, good) in [(fe, fl, 250, a1, False), (te, tl, W-250, a2, True)]:
        if a <= 0: continue
        card = Image.new("RGBA", (380, 380), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, 379, 379], 44, fill=fill if not c.st["light"] else (255, 255, 255, 225))
        ci = char_img(e, 190, c.ta, None, c.idx + (5 if good else 0), "happy" if good else "sad") if c.sc.get("faces") else emoji_img(e, 190)
        card.alpha_composite(ci, ((380 - ci.width)//2, max(0, 135 - ci.height//2)))
        for li, ln in enumerate(wrap(cd, lab, fs, 340)[:2]):
            cd.text((190, 280 + li*52), ln, font=fs, fill=tcol, anchor="mm")
        paste_c(c.layer, scaled(card, a), cx, cy)
    aa = ease_out((c.ta-0.45)/0.4)
    if aa > 0: paste_c(c.layer, emoji_img("➡️", 110*aa), W//2 + int(math.sin(c.ta*5)*10*aa), cy)
    s1 = ease_out_back((c.ta-1.2)/0.35); s2 = ease_out_back((c.ta-1.5)/0.35)
    if s1 > 0: paste_c(c.layer, emoji_img("❌", 100*s1), 250+150, cy-150)
    if s2 > 0: paste_c(c.layer, emoji_img("✅", 100*s2), W-250+150, cy-150)
    return top + 420

def sc_stat(c):
    st = c.sc["stat"]; top = 330; colw = (W-120)//len(st)
    fl, fv = font(FONT_BOLD, 56), font(FONT_HEAD, 170)
    light = c.st["light"]
    for k, (lab, val) in enumerate(st):
        a = ease_out_back((c.ta - 0.15 - k*0.3)/0.45)
        if a <= 0: continue
        num = "".join(ch for ch in val if ch.isdigit()); rest = val[len(num):] if val.startswith(num) and num else None
        if rest is not None:
            prog = ease_out((c.ta - 0.2 - k*0.3)/1.0); val_s = f"{int(round(int(num)*prog))}{rest}"
        else: val_s = val
        cw, ch = colw-40, 430
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        col = c.accent if k == 0 else ((120, 90, 70) if light else (235, 235, 235))
        cd.rounded_rectangle([0, 0, cw-1, ch-1], 40, fill=(255, 255, 255, 215 if light else 30), outline=col + (255,), width=6)
        cd.text((cw//2, 90), lab, font=fl, fill=col, anchor="mm")
        cd.text((cw//2, 260), val_s, font=fv, fill=(70, 40, 20) if light else WHITE, anchor="mm")
        paste_c(c.layer, scaled(card, a), 60 + colw*k + colw//2, top + 215)
    return top + 500

def fmt_num(v):
    return f"{v:.1f}".rstrip("0").rstrip(".") if abs(v - round(v)) > 1e-6 else str(int(round(v)))

def sc_fight(c):
    f = c.sc["fight"]; bars = f.get("bars", []); win = f.get("winner"); ta = c.ta; cy = 500
    LCOL, RCOL = (235, 70, 80), (60, 120, 240)
    fname = font(FONT_BOLD, 42)
    for side, (e, name), x0, col, sgn in [("left", f["left"], 270, LCOL, -1), ("right", f["right"], 810, RCOL, 1)]:
        a = ease_out(ta/0.45); x = x0 + sgn*(1-a)*520
        is_w = (win == side); is_l = bool(win) and not is_w
        mood = "happy" if is_w else ("sad" if is_l else "fight")
        scale = 1.15 if is_w else (0.84 if is_l else 1.0)
        bob = math.sin(ta*5 + (0 if side == "left" else 1.5))*10
        if is_w: paste_c(c.layer, scaled(glow(GOLD), 1.0 + 0.06*math.sin(ta*4)), x, cy)
        ci = char_img(e, 290*scale, ta, c.mouth if is_w else None, c.idx*7 + (1 if side == "left" else 2), mood, gray=0.6 if is_l else 0)
        paste_c(c.layer, ci, x, cy + bob)
        if not win:
            g = emoji_img("🥊", 105)
            if side == "right": g = g.transpose(Image.FLIP_LEFT_RIGHT)
            punch = max(0.0, math.sin(ta*6 + (0 if side == "left" else math.pi)))*30
            paste_c(c.layer, g, x - sgn*150 - sgn*punch, cy + 70 + bob)
        if is_w:
            dta = (ta - 0.35)/0.45
            if dta > 0:
                yy = (cy - 600) + ((cy - 190*scale) - (cy - 600))*ease_out_back(dta)
                paste_c(c.layer, emoji_img("👑", 150).rotate(-8, resample=Image.BICUBIC, expand=True), x, yy + bob)
            if "conf" not in c.cache: c.cache["conf"] = Confetti(x, cy - 120, c.idx)
            c.confetti.append((c.cache["conf"], 0.6))
        label = ("WINNER!" if is_w else name)
        p = pill(label, fname, GOLD if is_w else col, INK if is_w else WHITE)
        paste_c(c.layer, scaled(p, ease_out_back((ta - 0.2)/0.4)), x, cy + 205)
    if not win and ta >= 0.25:
        s = 1 + 1.6*(1 - ease_out((ta - 0.25)/0.22))
        vs = text_img("VS", font(FONT_HEAD, 200), GOLD, (0, 0, 0, 140), stroke=10, stroke_fill=(50, 20, 10))
        if ta > 0.4:
            for k, dx in enumerate((-95, 95)):
                if math.sin(ta*22 + k*2) > -0.3:
                    paste_c(c.layer, emoji_img("⚡", 90).rotate(15 if k else -15, expand=True), 540 + dx, cy - 120)
        paste_c(c.layer, scaled(vs, s), 540, cy - 10)
        c.shake_at = c.flash_at = 0.47
    y_bars = 780 + c.head_h + (25 if c.head_h else 0)
    flab = font(FONT_BOLD, 38); fval = font(FONT_HEAD, 58); maxlen = 330
    for k, bar in enumerate(bars[:3]):
        label, lv, rv = bar[0], float(bar[1]), float(bar[2])
        unit = bar[3] if len(bar) > 3 else ""; better = bar[4] if len(bar) > 4 else "high"
        p = ease_out((ta - 0.35 - k*0.45)/0.8)
        if p <= 0: continue
        y = y_bars + k*128
        c.dr.text((540, y + 18), label, font=flab, fill=c.st["sub"], anchor="mm")
        mx = max(lv, rv) or 1.0
        lgood = (lv >= rv) if better == "high" else (lv <= rv)
        cl, cr = (GOOD, BAD) if lgood else (BAD, GOOD)
        if lv == rv: cl = cr = GOLD
        yb0, yb1 = y + 45, y + 97
        c.dr.rounded_rectangle([525 - maxlen, yb0, 525, yb1], 26, fill=(0, 0, 0, 90))
        c.dr.rounded_rectangle([555, yb0, 555 + maxlen, yb1], 26, fill=(0, 0, 0, 90))
        lw_, rw_ = max(52, maxlen*lv/mx*p), max(52, maxlen*rv/mx*p)
        c.dr.rounded_rectangle([525 - lw_, yb0, 525, yb1], 26, fill=cl)
        c.dr.rounded_rectangle([555, yb0, 555 + rw_, yb1], 26, fill=cr)
        c.dr.text((525 - maxlen - 12, (yb0+yb1)//2), fmt_num(lv*p) + unit, font=fval, fill=WHITE, anchor="rm")
        c.dr.text((555 + maxlen + 12, (yb0+yb1)//2), fmt_num(rv*p) + unit, font=fval, fill=WHITE, anchor="lm")
    return 780

def sc_quiz(c):
    q = c.sc["quiz"]; ta = c.ta
    lab = pill(q.get("label", "TRUE OR FALSE?"), font(FONT_HEAD, 62), GOLD, INK, padx=40, h=104)
    paste_c(c.layer, scaled(lab, ease_out_back(ta/0.4)), 540, 300)
    fcard = font(FONT_BOLD, 60)
    lines = wrap(c.dr, q["statement"], fcard, 800)
    y0 = 390; card_h = len(lines)*80 + 90
    a = ease_out((ta - 0.15)/0.4); yo = int((1-a)*60)
    card = Image.new("RGBA", (920, card_h + 14), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 14, 919, card_h + 13], 40, fill=(0, 0, 0, 90))
    cd.rounded_rectangle([0, 0, 919, card_h - 1], 40, fill=WHITE)
    for li, ln in enumerate(lines):
        cd.text((460, 45 + li*80 + 40), ln, font=fcard, fill=INK, anchor="mm")
    if a < 1: card.putalpha(card.getchannel("A").point(lambda v: int(v*a)))
    c.layer.alpha_composite(card, (80, y0 + yo))
    if q.get("character"):
        qc = q["character"] if isinstance(q["character"], list) else [q["character"]]
        ch, mood = (qc + ["surprised"])[:2]
        pa = ease_out_back((ta - 0.4)/0.45)
        if pa > 0: paste_c(c.layer, char_img(ch, 190*pa, ta, None, c.idx, mood), 930, y0 + card_h - 10 + math.sin(ta*3)*8)
    cyT = y0 + card_h + 165; r = 88
    frac = clamp(c.t / max(0.1, c.dur - 0.25)); rem = 1 - frac
    c.dr.ellipse([540-r, cyT-r, 540+r, cyT+r], fill=(0, 0, 0, 110))
    c.dr.arc([540-r+9, cyT-r+9, 540+r-9, cyT+r-9], -90, -90 + 360*rem if rem > 0.002 else -89.9, fill=c.accent, width=18)
    num = str(max(1, math.ceil(rem*3))) if rem > 0.02 else "?"
    pulse = 1 + 0.25*(1 - ease_out(((frac*3) % 1)/0.25))
    paste_c(c.layer, scaled(text_img(num, font(FONT_HEAD, 100), WHITE, (0, 0, 0, 100)), pulse), 540, cyT)
    return cyT + 150

def sc_reveal(c):
    rv = c.sc["reveal"]; ta = c.ta
    is_myth = rv["answer"].lower() in ("myth", "false")
    col = (255, 77, 77) if is_myth else (80, 215, 110)
    word = rv.get("word", "MYTH" if is_myth else "FACT")
    if rv.get("statement"):
        fs = font(FONT_BOLD, 44); lines = wrap(c.dr, rv["statement"], fs, 820)[:2]
        ch_ = len(lines)*58 + 50
        c.dr.rounded_rectangle([110, 290, 970, 290 + ch_], 30, fill=(255, 255, 255, 200))
        for li, ln in enumerate(lines):
            c.dr.text((540, 290 + 25 + li*58 + 29), ln, font=fs, fill=(90, 85, 90), anchor="mm")
            if is_myth:
                p = ease_out((ta - 0.55 - li*0.15)/0.3)
                if p > 0:
                    lw_ = fs.getlength(ln); yy = 290 + 25 + li*58 + 31
                    c.dr.line([(540 - lw_/2 - 10, yy), (540 - lw_/2 - 10 + (lw_ + 20)*p, yy)], fill=(230, 40, 40), width=9)
    if "stamp" not in c.cache:
        f = font(FONT_HEAD, 230); tw = f.getlength(word)
        st_ = Image.new("RGBA", (int(tw + 120), 330), (0, 0, 0, 0)); sd = ImageDraw.Draw(st_)
        sd.rounded_rectangle([8, 8, st_.width-9, st_.height-9], 40, outline=col, width=16)
        sd.text((st_.width/2, st_.height/2), word, font=f, fill=col, anchor="mm")
        c.cache["stamp"] = st_.rotate(-8, resample=Image.BICUBIC, expand=True)
    if ta >= 0.15:
        s = 1 + 1.4*(1 - ease_out((ta - 0.15)/0.2))
        img = scaled(c.cache["stamp"], s)
        if s > 1.05: img.putalpha(img.getchannel("A").point(lambda v: int(v*clamp((ta-0.15)/0.12))))
        paste_c(c.layer, img, 540, 640)
        c.shake_at = c.flash_at = 0.35
    ia = ease_out_back((ta - 0.45)/0.4)
    if ia > 0: paste_c(c.layer, emoji_img("❌" if is_myth else "✅", 160*ia).rotate(12, expand=True), 905, 505)
    return 850

_plate_cache = {}
def plate_img(R):
    if R not in _plate_cache:
        s = 2*R + 60; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c0 = s//2
        d.ellipse([c0-R+10, c0-R+26, c0+R+10, c0+R+26], fill=(120, 70, 30, 60))
        d.ellipse([c0-R, c0-R, c0+R, c0+R], fill=(250, 250, 250), outline=(215, 210, 205), width=4)
        r2 = int(R*0.78)
        d.ellipse([c0-r2-6, c0-r2-6, c0+r2+6, c0+r2+6], fill=(236, 233, 230))
        d.ellipse([c0-r2, c0-r2, c0+r2, c0+r2], fill=WHITE)
        _plate_cache[R] = im
    return _plate_cache[R]

def sc_plate(c):
    p = c.sc["plate"]; items = p.get("items", []); badges = p.get("badges", []); ta = c.ta
    cx, cy, R = 540, 600, 285
    paste_c(c.layer, scaled(plate_img(R), ease_out_back(ta/0.4)), cx, cy)
    n = len(items); rad = 0 if n == 1 else (130 if n <= 3 else 150); size = 175 if n <= 3 else 150
    ftag = font(FONT_BOLD, 30)
    span = max(0.6, c.speak_end*0.75)
    last_land = 0
    for k, (e, lab) in enumerate(items):
        ang = -math.pi/2 + k*2*math.pi/max(1, n)
        px, py = cx + rad*math.cos(ang), cy + rad*math.sin(ang)
        st0 = 0.25 + k*span/max(1, n); last_land = st0 + 0.5
        dd = (ta - st0)/0.5
        if dd <= 0: continue
        yoff = -650*(1 - ease_out_back(dd))
        land = clamp((ta - st0 - 0.42)/0.18); squash = 0.12*math.sin(land*math.pi)
        img = char_img(e, size, ta, None, c.idx*5 + k, "happy") if p.get("faces") else emoji_img(e, size)
        img = scaled(img, 1 + squash, 1 - squash)
        paste_c(c.layer, img, px, py + yoff)
        if dd > 0.7 and lab:
            tg = pill(lab, ftag, (255, 255, 255, 235), (70, 40, 20), padx=18, h=48)
            paste_c(c.layer, scaled(tg, ease_out_back((dd - 0.7)/0.5)), px, py + size*0.5 + 22)
    fb = font(FONT_BOLD, 38)
    for k, (lab, val) in enumerate(badges[:3]):
        ba = ease_out_back((ta - last_land - 0.1 - k*0.15)/0.4)
        if ba <= 0: continue
        bimg = pill(f"{lab} {val}", fb, c.accent, WHITE if c.st["light"] else INK, padx=28, h=66)
        tot = len(badges[:3]); x = 540 + (k - (tot-1)/2)*320
        paste_c(c.layer, scaled(bimg, ba), x, cy + R + 55)
    return cy + R + (135 if badges else 60)

def sc_rank(c):
    r = c.sc["rank"]; n = int(r["n"]); of = int(r.get("of", 3)); ta = c.ta
    gold = (n == 1); fl = font(FONT_BOLD, 30)
    xs = [540 + (j - (of-1)/2)*120 for j in range(of)]
    for j, k in enumerate(range(of, 0, -1)):
        active, done = (k == n), (k > n)
        rr = 46 if active else 36
        fill = (GOLD if gold else c.accent) if active else ((255, 255, 255, 70) if done else (0, 0, 0, 70))
        c.dr.ellipse([xs[j]-rr, 300-rr, xs[j]+rr, 300+rr], fill=fill)
        c.dr.text((xs[j], 302), f"#{k}", font=fl, fill=INK if active else WHITE, anchor="mm")
    fnum = text_img(f"#{n}", font(FONT_HEAD, 300), GOLD if gold else WHITE, (0, 0, 0, 120), stroke=10, stroke_fill=(70, 20, 50))
    fa = ease_out_back((ta - 0.05)/0.5)
    if fa > 0: paste_c(c.layer, scaled(fnum, fa, 1.0), 300, 620)
    a = ease_out_back((ta - 0.25)/0.5)
    if gold: paste_c(c.layer, scaled(glow(GOLD), 1.05 + 0.06*math.sin(ta*4)), 760, 610)
    if a > 0:
        ci = char_img(r["item"], 320*a, ta, c.mouth if r.get("talk") else None, c.idx*3, r.get("mood", "happy"))
        paste_c(c.layer, ci, 760, 610 + math.sin(ta*3)*10)
    if gold:
        dta = (ta - 0.45)/0.45
        if dta > 0:
            yy = 40 + (430 - 40)*ease_out_back(dta)
            paste_c(c.layer, emoji_img("👑", 150).rotate(-8, resample=Image.BICUBIC, expand=True), 760, yy)
        if "conf" not in c.cache: c.cache["conf"] = Confetti(760, 470, c.idx + 11)
        c.confetti.append((c.cache["conf"], 0.6))
    return 850

SCENES = [("character", sc_character), ("fight", sc_fight), ("quiz", sc_quiz), ("reveal", sc_reveal),
          ("plate", sc_plate), ("rank", sc_rank), ("steps", lambda c: sc_items(c, True)),
          ("items", sc_items), ("swap", sc_swap), ("stat", sc_stat), ("emoji", sc_emoji)]
HEAD_FIT = {"fight": (110, 2), "rank": (120, 2), "plate": (110, 2), "reveal": (120, 2), "quiz": (100, 2)}

def speaker_in_scene(sc):
    if sc.get("character"): return True
    if sc.get("emoji") and sc.get("faces"): return True
    if sc.get("fight", {}).get("winner"): return True
    if sc.get("rank", {}).get("talk"): return True
    return False

# ---------------- scene render loop ----------------
def render_scene(sc, idx, dur, total_before, total, out, style, bg_icons, mouth, mascot):
    st = STYLES[style]
    accent = hex2rgb(sc.get("accent", st["accent"]))
    nf = int(round(dur*FPS)); tmp = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    d0 = ImageDraw.Draw(Image.new("RGBA", (W, H)))
    kind = next((k for k, _ in SCENES if k in sc), None)
    fn = dict(SCENES).get(kind)
    head = sanitize(sc.get("headline", ""), FONT_HEAD)
    hstart, hmax = HEAD_FIT.get(kind, (135, 3))
    fh = fit_font(d0, head, FONT_HEAD, hstart, W-140, hmax) if head else font(FONT_HEAD, 120)
    hlines = wrap(d0, head, fh, W-140) if head else []
    lh = fh.size*1.12
    fsub = font(FONT_MED, 52)
    slines = wrap(d0, sc.get("sub", ""), fsub, W-180) if sc.get("sub") else []
    fcap = font(FONT_BOLD, 58)
    words = sc["say"].split()
    clen = [len(w)+1 for w in words]; cum = np.cumsum(clen)/sum(clen)
    speak_end = dur - 0.35
    ftag, ffoot = font(FONT_BOLD, 40), font(FONT_MED, 30)
    parts = Particles(bg_icons, idx*7 + 3, st["palpha"])
    head_shadow = (120, 70, 30, 55) if st["light"] else (0, 0, 0, 120)
    hwords = []
    for li, line in enumerate(hlines):
        col = accent if li == len(hlines)-1 and len(hlines) > 1 else st["head"]
        sp = d0.textlength(" ", font=fh); lw = d0.textlength(line, font=fh); x = (W-lw)/2
        for w in line.split():
            ww = d0.textlength(w, font=fh); hwords.append((w, col, x + ww/2, li*lh)); x += ww + sp
    c = Ctx(); c.sc, c.idx, c.st, c.style, c.accent = sc, idx, st, style, accent
    c.dur, c.speak_end, c.mood, c.cache = dur, speak_end, sc.get("mood", "happy"), {}
    c.head_h = int(lh*len(hlines)) if hlines else 0
    show_mascot = mascot and not speaker_in_scene(sc)
    for fi in range(nf):
        t = fi/FPS
        c.t, c.ta = t, t + (2.0 if idx == 0 else 0.0)
        c.mouth = mouth[min(fi, len(mouth)-1)] if mouth else REST
        c.shake_at = c.flash_at = None; c.confetti = []
        frame = bg(style).copy()
        if st["rays"]: draw_rays(frame, st["rays"], total_before + t)
        parts.draw(frame, total_before + t)
        c.layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); c.dr = ImageDraw.Draw(c.layer)
        top_text = fn(c) if fn else 520
        if show_mascot:
            mi = char_img(mascot, 120, t + total_before, c.mouth, 99, "happy", hat=(style == "kitchen"))
            paste_c(c.layer, mi, 100, 200 + math.sin((t+total_before)*2.2)*5)
        for wi, (w, col, xc, yt) in enumerate(hwords):
            a = ease_out_back((c.ta - 0.25 - wi*0.07)/0.35)
            if a <= 0: continue
            paste_c(c.layer, scaled(text_img(w, fh, col, head_shadow), a), xc, top_text + yt + fh.size*0.62)
        a = ease_out((c.ta - 0.5)/0.4)
        if a > 0:
            yb = top_text + int(lh*len(hlines)) + 20 + int((1-a)*30)
            for li, line in enumerate(slines):
                c.dr.text((W//2, yb + li*68), line, font=fsub, fill=st["sub"] + (int(255*a),), anchor="mt")
        for conf, t0 in c.confetti: conf.draw(c.dr, c.ta - t0)
        ea = 1.0 if idx == 0 else ease_out(t/0.2)
        dx = dy = 0
        if c.shake_at is not None and 0 <= c.ta - c.shake_at < 0.3:
            amp = 22*(1 - (c.ta - c.shake_at)/0.3); dx, dy = int(amp*math.sin(c.ta*95)), int(amp*math.cos(c.ta*83))
        if ea < 1:
            c.layer.putalpha(c.layer.getchannel("A").point(lambda v, ea=ea: int(v*ea)))
            frame.alpha_composite(c.layer, (int((1-ea)*90), 0))
        else:
            src = c.layer.crop((max(-dx, 0), max(-dy, 0), W, H)) if (dx < 0 or dy < 0) else c.layer
            frame.alpha_composite(src, (max(dx, 0), max(dy, 0)))
        if c.flash_at is not None and 0 <= c.ta - c.flash_at < 0.2:
            fa = int(150*(1 - (c.ta - c.flash_at)/0.2))
            frame.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, fa)))
        fd = ImageDraw.Draw(frame)
        prog = (total_before + t)/total
        fd.rounded_rectangle([60, 70, W-60, 82], 6, fill=st["track"])
        fd.rounded_rectangle([60, 70, 60 + int((W-120)*prog), 82], 6, fill=accent)
        fd.text((W//2, 135), "@DiabeticEats", font=ftag, fill=st["tag"], anchor="mm")
        frac = min(1.0, t/max(0.1, speak_end))
        shown = int(np.searchsorted(cum, frac, side="right")) + 1
        clines = wrap(fd, sc["say"], fcap, W-200)
        line_of = [li for li, l in enumerate(clines) for _ in l.split()]
        cur_line = line_of[min(shown, len(words))-1]
        start = max(0, min(cur_line, len(clines)-2)) if len(clines) > 2 else 0
        win = clines[start:start+2]
        by = 1340; boxh = 84*len(win)+60
        fd.rounded_rectangle([70, by, W-70, by+boxh], 36, fill=(0, 0, 0))
        wcount = sum(len(l.split()) for l in clines[:start])
        for li, l in enumerate(win):
            lw = fd.textlength(l, font=fcap); x = (W-lw)/2
            for w in l.split():
                wcount += 1
                col = accent if wcount == shown else (WHITE if wcount < shown else (120, 140, 132))
                fd.text((x, by+30+li*84), w, font=fcap, fill=col)
                x += fd.textlength(w + " ", font=fcap)
        if sc.get("footer"):
            fd.text((W//2, 1830), sc["footer"], font=ffoot, fill=(90, 60, 40) if st["light"] else (170, 200, 188), anchor="mm")
        p.stdin.write(frame.tobytes())
    p.stdin.close(); p.wait()
    if p.returncode == 0: os.replace(tmp, out)
    else: raise SystemExit("ffmpeg failed")

def main(script_path, out_path):
    sc = json.load(open(script_path))
    style = sc.get("style", "talk")
    if style not in STYLES: raise SystemExit(f"unknown style {style}")
    work = os.path.splitext(out_path)[0] + "_work"; os.makedirs(work, exist_ok=True)
    from kokoro_onnx import Kokoro
    timed = os.path.join(TTS, "kokoro-timed.onnx")
    k = Kokoro(timed if os.path.exists(timed) else os.path.join(TTS, "kokoro.onnx"), os.path.join(TTS, "voices.bin"))
    if not k.has_timings: print("WARNING: no phoneme timings (run pipeline/setup.sh) — using loudness lip sync")
    durs, auds, tims, sr, lead = [], [], [], 24000, 0.05
    for s in sc["scenes"]:
        if k.has_timings:
            a, sr, tm = k.create_timed(s["say"], voice=sc.get("voice", "af_heart"), speed=sc.get("speed", 1.15), lang="en-us")
        else:
            a, sr = k.create(s["say"], voice=sc.get("voice", "af_heart"), speed=sc.get("speed", 1.15), lang="en-us"); tm = []
        a = np.concatenate([np.zeros(int(sr*lead), np.float32), a, np.zeros(int(sr*0.3), np.float32)])
        auds.append(a); tims.append(tm); durs.append(round(len(a)/sr*FPS)/FPS)
    mouths = []
    for a, d, tm in zip(auds, durs, tims):
        n = int(round(d*FPS)); hop = sr/FPS
        e = np.array([np.sqrt(np.mean(a[int(i*hop):int((i+1)*hop)]**2)) if int(i*hop) < len(a) else 0.0 for i in range(n)])
        ref = np.percentile(e[e > 0], 90) if np.any(e > 0) else 1.0
        e = np.clip(e/ref, 0, 1)
        mouths.append(mouth_track(tm, n, lead, e))
    full = np.concatenate([np.pad(a, (0, max(0, int(d*sr)-len(a))))[:int(d*sr)] for a, d in zip(auds, durs)])
    sf.write(f"{work}/voice.wav", full, sr)
    bg_icons = sc.get("bg_icons", DEFAULT_BG_ICONS)
    total = sum(durs); before = 0; files = []
    only = os.environ.get("ONLY")
    for i, s in enumerate(sc["scenes"]):
        f = f"{work}/s{i:02d}.mp4"; files.append(f)
        if only is None or str(i) in only.split(","):
            render_scene(s, i, durs[i], before, total, f, style, bg_icons, mouths[i], sc.get("mascot"))
        before += durs[i]
    with open(f"{work}/list.txt", "w") as fl:
        for f in files: fl.write(f"file '{os.path.abspath(f)}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt",
        "-i", f"{work}/voice.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-movflags", "+faststart", "-shortest", out_path], check=True)
    print("done", out_path, round(total, 2), "s")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
