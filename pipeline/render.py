"""Diabetic Eats reel renderer (v3 — animated, instant hook on scene 0).
Usage: python3 render.py script.json out.mp4

script.json:
{"voice": "af_heart", "speed": 1.1, "bg_icons": ["🥦","🍎"], "scenes": [ SCENE, ... ]}

SCENE fields (all scenes): "say" (narration), "headline", optional "sub" (no emoji),
"accent" (hex), optional "footer". Then ONE visual:
  "emoji": ["🍯","🍬"]                         -> bouncing icons with glow
  "stat": [["HONEY","17g"],["SUGAR","12g"]]    -> cards with count-up numbers
  "items": [["✅","Turkey breast"],["❌","Candied yams"]]  -> checklist revealed as spoken (2-4 items)
  "swap": [["🥔","Mashed potatoes"],["🥦","Cauliflower mash"]] -> from ❌ -> to ✅
"""
import json, sys, os, subprocess, math, re, random
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
TTS = os.environ.get("TTS_DIR", "/home/claude/tts")
FONT_HEAD = "/usr/share/fonts/truetype/google-fonts/ofl/anton/Anton-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_MED = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
BG1, BG2 = (10, 52, 40), (4, 28, 22)
WHITE = (255, 255, 255)
CREAM = (255, 248, 230)
DEFAULT_BG_ICONS = ["🥦", "🍎", "🥑", "🥕", "🫐", "🥗", "🍋", "🥚"]

def hex2rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def clamp(t): return max(0.0, min(1.0, t))
def ease_out(t): t = clamp(t); return 1 - (1-t)**3
def ease_out_back(t):
    t = clamp(t); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3*(t-1)**3 + c1*(t-1)**2

_emoji_cache = {}
def emoji_img(ch, size, alpha=1.0):
    key = (ch, size, alpha)
    if key not in _emoji_cache:
        base_key = (ch, "base")
        if base_key not in _emoji_cache:
            f = ImageFont.truetype(FONT_EMOJI, 109)
            im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((90, 90), ch, font=f, embedded_color=True, anchor="mm")
            _emoji_cache[base_key] = im.crop(im.getbbox() or (0, 0, 180, 180))
        im = _emoji_cache[base_key]
        s = size / max(im.size)
        im = im.resize((max(1, int(im.width*s)), max(1, int(im.height*s))), Image.LANCZOS)
        if alpha < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v*alpha)))
        _emoji_cache[key] = im
    return _emoji_cache[key]

def scaled(img, s):
    s = max(0.01, s)
    if abs(s-1) < 0.01: return img
    return img.resize((max(1, int(img.width*s)), max(1, int(img.height*s))), Image.BILINEAR)

def paste_c(dst, img, cx, cy):
    dst.alpha_composite(img, (int(cx - img.width/2), int(cy - img.height/2)))

def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= maxw: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def fit_font(draw, text, path, start, maxw, maxlines):
    size = start
    while size > 40:
        f = ImageFont.truetype(path, size)
        if len(wrap(draw, text, f, maxw)) <= maxlines: return f
        size -= 6
    return ImageFont.truetype(path, size)

def make_bg():
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    g = np.clip(y*0.8 + (x-0.5)**2*0.6, 0, 1)
    arr = np.zeros((H, W, 3), np.float32)
    for i in range(3): arr[..., i] = BG1[i]*(1-g) + BG2[i]*g
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")

def make_glow(color, r=320):
    s = r*2
    yy, xx = np.mgrid[0:s, 0:s]
    d = np.sqrt((xx-r)**2 + (yy-r)**2)/r
    a = (np.clip(1-d, 0, 1)**2.2*150).astype(np.uint8)
    arr = np.zeros((s, s, 4), np.uint8); arr[..., :3] = color; arr[..., 3] = a
    return Image.fromarray(arr, "RGBA")

BG = make_bg()
_glow_cache = {}
def glow(color):
    if color not in _glow_cache: _glow_cache[color] = make_glow(color)
    return _glow_cache[color]

_text_cache = {}
def text_img(txt, font, fill, shadow=True):
    key = (txt, font.path, font.size, fill, shadow)
    if key not in _text_cache:
        bb = font.getbbox(txt)
        w, h = bb[2]-bb[0]+16, bb[3]-bb[1]+16
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        if shadow: d.text((8-bb[0]+5, 8-bb[1]+5), txt, font=font, fill=(0, 0, 0, 120))
        d.text((8-bb[0], 8-bb[1]), txt, font=font, fill=fill)
        _text_cache[key] = im
    return _text_cache[key]

class Particles:
    def __init__(self, icons, seed):
        rnd = random.Random(seed)
        self.p = []
        for i in range(11):
            self.p.append(dict(e=rnd.choice(icons), x=rnd.uniform(40, W-40), y=rnd.uniform(0, H),
                               v=rnd.uniform(25, 60), sw=rnd.uniform(15, 40), ph=rnd.uniform(0, 6.28),
                               size=rnd.randint(60, 110)))
    def draw(self, layer, t):
        for q in self.p:
            y = (q["y"] - q["v"]*t) % (H + 200) - 100
            x = q["x"] + math.sin(t*0.9 + q["ph"])*q["sw"]
            paste_c(layer, emoji_img(q["e"], q["size"], 0.16), x, y)

def render_scene(sc, idx, dur, total_before, total, out, bg_icons):
    accent = hex2rgb(sc.get("accent", "#B6F35C"))
    nf = int(round(dur*FPS))
    tmp = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    d0 = ImageDraw.Draw(BG.copy())
    head = sc.get("headline", "")
    fh = fit_font(d0, head, FONT_HEAD, 135, W-140, 3)
    hlines = wrap(d0, head, fh, W-140)
    fsub = ImageFont.truetype(FONT_MED, 52)
    slines = wrap(d0, sc.get("sub", ""), fsub, W-180) if sc.get("sub") else []
    fcap = ImageFont.truetype(FONT_BOLD, 58)
    words = sc["say"].split()
    clen = [len(w)+1 for w in words]; cum = np.cumsum(clen)/sum(clen)
    speak_end = dur - 0.35
    fstat_l = ImageFont.truetype(FONT_BOLD, 56); fstat_v = ImageFont.truetype(FONT_HEAD, 170)
    fitem = ImageFont.truetype(FONT_BOLD, 60); fswap = ImageFont.truetype(FONT_BOLD, 44)
    ftag = ImageFont.truetype(FONT_BOLD, 40); ffoot = ImageFont.truetype(FONT_MED, 30)
    emojis = sc.get("emoji", [])
    parts = Particles(bg_icons, idx*7 + 3)
    # headline word layout
    lh = fh.size*1.12
    hwords = []  # (word, color, x_center, y_top)
    for li, line in enumerate(hlines):
        col = accent if li == len(hlines)-1 and len(hlines) > 1 else CREAM
        ws = line.split(); space = d0.textlength(" ", font=fh)
        lw = d0.textlength(line, font=fh); x = (W-lw)/2
        for w in ws:
            ww = d0.textlength(w, font=fh)
            hwords.append((w, col, x + ww/2, li*lh)); x += ww + space

    for fi in range(nf):
        t = fi/FPS
        frame = BG.copy()
        parts.draw(frame, total_before + t)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(layer)
        ta = t + (2.0 if idx == 0 else 0.0)  # scene 0: hook fully visible from frame 0
        # --- visual block ---
        top = 330
        if sc.get("stat"):
            st = sc["stat"]; colw = (W-120)//len(st)
            for k, (lab, val) in enumerate(st):
                a = ease_out_back((ta - 0.15 - k*0.3)/0.45)
                if a <= 0: continue
                m = re.match(r"^(\d+)(.*)$", val)
                if m:
                    prog = ease_out((ta - 0.2 - k*0.3)/1.0)
                    val_s = f"{int(round(int(m.group(1))*prog))}{m.group(2)}"
                else: val_s = val
                cx = 60 + colw*k + colw//2
                cw, ch = colw-40, 430
                card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
                col = accent if k == 0 else (235, 235, 235)
                cd.rounded_rectangle([0, 0, cw-1, ch-1], 40, fill=(255, 255, 255, 30), outline=col + (255,), width=6)
                cd.text((cw//2, 90), lab, font=fstat_l, fill=col, anchor="mm")
                cd.text((cw//2, 260), val_s, font=fstat_v, fill=WHITE, anchor="mm")
                paste_c(layer, scaled(card, a), cx, top + 215)
            top_text = top + 500
        elif sc.get("items"):
            items = sc["items"]; n = len(items)
            frac = clamp(ta/max(0.1, speak_end))
            rowh = 150; y0 = 290
            for k, (ic, label) in enumerate(items):
                start = 0.2 + (k/n)*speak_end*0.75
                a = ease_out((ta - start)/0.35)
                if a <= 0: continue
                y = y0 + k*rowh
                x_off = int((1-a)*120)
                pill = Image.new("RGBA", (W-140, rowh-24), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill)
                pd.rounded_rectangle([0, 0, pill.width-1, pill.height-1], 34, fill=(255, 255, 255, int(34*a)))
                pd.text((150, pill.height//2), label, font=fitem, fill=CREAM + (int(255*a),), anchor="lm")
                layer.alpha_composite(pill, (70 + x_off, y))
                pop = ease_out_back((ta - start - 0.05)/0.4)
                if pop > 0: paste_c(layer, emoji_img(ic, max(1, int(90*pop))), 70 + 75 + x_off, y + (rowh-24)//2)
            top_text = y0 + n*rowh + 40
            hlines_use = True
        elif sc.get("swap"):
            (fe, fl), (te, tl) = sc["swap"]
            cy = top + 170
            a1 = ease_out_back((ta-0.1)/0.45); a2 = ease_out_back((ta-0.7)/0.45)
            for (e, lab, cx, a) in [(fe, fl, 250, a1), (te, tl, W-250, a2)]:
                if a <= 0: continue
                card = Image.new("RGBA", (380, 380), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
                cd.rounded_rectangle([0, 0, 379, 379], 44, fill=(255, 255, 255, 30))
                card.alpha_composite(emoji_img(e, 190), (95, 40))
                for li, ln in enumerate(wrap(cd, lab, fswap, 340)[:2]):
                    cd.text((190, 270 + li*52), ln, font=fswap, fill=CREAM, anchor="mm")
                paste_c(layer, scaled(card, a), cx, cy)
            # arrow slides in
            aa = ease_out((ta-0.45)/0.4)
            if aa > 0:
                ax = W//2 - 40 + int(math.sin(ta*5)*10*aa)
                paste_c(layer, emoji_img("➡️", int(110*aa)), ax + 40, cy)
            # stamps
            s1 = ease_out_back((ta-1.2)/0.35); s2 = ease_out_back((ta-1.5)/0.35)
            if s1 > 0: paste_c(layer, emoji_img("❌", int(100*s1)), 250+150, cy-150)
            if s2 > 0: paste_c(layer, emoji_img("✅", int(100*s2)), W-250+150, cy-150)
            top_text = top + 420
        elif emojis:
            n_e = len(emojis); size = 300 if n_e == 1 else (240 if n_e == 2 else 190 if n_e == 3 else 170)
            gap = 30; tot = n_e*size + (n_e-1)*gap; x0 = (W - tot)//2
            pulse = 1 + 0.06*math.sin(ta*3.2)
            gl = scaled(glow(accent), (0.9 if n_e == 1 else 1.25)*pulse*ease_out(ta/0.5))
            paste_c(layer, gl, W//2, top + 160)
            for k, e in enumerate(emojis):
                a = ease_out_back((ta - 0.1 - k*0.15)/0.5)
                if a <= 0: continue
                bob = math.sin(ta*2.4 + k*1.3)*14
                wob = math.sin(ta*1.8 + k)*6
                ei = emoji_img(e, max(1, int(size*a)))
                if abs(wob) > 0.5: ei = ei.rotate(wob, resample=Image.BICUBIC, expand=True)
                cx = x0 + k*(size+gap) + size//2
                paste_c(layer, ei, cx, top + 160 + bob)
            top_text = top + 400
        else:
            top_text = 520
        # --- headline: word-by-word pop ---
        for wi, (w, col, xc, yt) in enumerate(hwords):
            a = ease_out_back((ta - 0.25 - wi*0.07)/0.35)
            if a <= 0: continue
            img = scaled(text_img(w, fh, col), a)
            paste_c(layer, img, xc, top_text + yt + fh.size*0.62)
        a = ease_out((ta - 0.5)/0.4)
        if a > 0:
            yb = top_text + int(lh*len(hlines)) + 20 + int((1-a)*30)
            for li, line in enumerate(slines):
                dr.text((W//2, yb + li*68), line, font=fsub, fill=(210, 235, 222, int(255*a)), anchor="mt")
        # --- scene entry: slide + fade ---
        ea = 1.0 if idx == 0 else ease_out(t/0.2)
        if ea < 1:
            layer.putalpha(layer.getchannel("A").point(lambda v, ea=ea: int(v*ea)))
            frame.alpha_composite(layer, (int((1-ea)*90), 0))
        else:
            frame.alpha_composite(layer)
        fd = ImageDraw.Draw(frame)
        # --- progress bar + handle ---
        prog = (total_before + t)/total
        fd.rounded_rectangle([60, 70, W-60, 82], 6, fill=(40, 80, 66))
        fd.rounded_rectangle([60, 70, 60 + int((W-120)*prog), 82], 6, fill=accent)
        fd.text((W//2, 135), "@DiabeticEats", font=ftag, fill=(200, 230, 215), anchor="mm")
        # --- captions (karaoke) ---
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
            fd.text((W//2, 1830), sc["footer"], font=ffoot, fill=(170, 200, 188), anchor="mm")
        p.stdin.write(frame.tobytes())
    p.stdin.close(); p.wait()
    if p.returncode == 0: os.replace(tmp, out)
    else: raise SystemExit("ffmpeg failed")

def main(script_path, out_path):
    sc = json.load(open(script_path))
    work = os.path.splitext(out_path)[0] + "_work"; os.makedirs(work, exist_ok=True)
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(TTS, "kokoro.onnx"), os.path.join(TTS, "voices.bin"))
    durs, auds, sr = [], [], 24000
    for s in sc["scenes"]:
        a, sr = k.create(s["say"], voice=sc.get("voice", "af_heart"), speed=sc.get("speed", 1.1), lang="en-us")
        a = np.concatenate([np.zeros(int(sr*0.05), np.float32), a, np.zeros(int(sr*0.3), np.float32)])
        auds.append(a); durs.append(round(len(a)/sr*FPS)/FPS)
    full = np.concatenate([np.pad(a, (0, max(0, int(d*sr)-len(a))))[:int(d*sr)] for a, d in zip(auds, durs)])
    sf.write(f"{work}/voice.wav", full, sr)
    bg_icons = sc.get("bg_icons", DEFAULT_BG_ICONS)
    total = sum(durs); before = 0; files = []
    only = os.environ.get("ONLY")
    for i, s in enumerate(sc["scenes"]):
        f = f"{work}/s{i:02d}.mp4"; files.append(f)
        if only is None or str(i) in only.split(","):
            render_scene(s, i, durs[i], before, total, f, bg_icons)
        before += durs[i]
    with open(f"{work}/list.txt", "w") as fl:
        for f in files: fl.write(f"file '{os.path.abspath(f)}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt",
        "-i", f"{work}/voice.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-movflags", "+faststart", "-shortest", out_path], check=True)
    print("done", out_path, round(total, 2), "s")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
