"""Diabetic Eats reel renderer.
Usage: python3 render.py script.json out.mp4
script.json: {"voice": "af_heart", "speed": 1.05, "scenes": [ {"say": "...", "headline": "...", "sub": "...", "emoji": ["🍯"], "stat": [["HONEY","17g"],["SUGAR","12g"]], "accent": "#FFC93C"} ]}
"""
import json, sys, os, subprocess, math, re
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
TTS = os.environ.get("TTS_DIR", "/home/claude/tts")
FONT_HEAD = "/usr/share/fonts/truetype/google-fonts/ofl/anton/Anton-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_MED = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
BG1, BG2 = (10, 52, 40), (4, 28, 22)
WHITE = (255, 255, 255)
CREAM = (255, 248, 230)

def hex2rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

_emoji_cache = {}
def emoji_img(ch, size):
    key = (ch, size)
    if key not in _emoji_cache:
        f = ImageFont.truetype(FONT_EMOJI, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
        bb = im.getbbox() or (0, 0, 160, 160)
        im = im.crop(bb)
        s = size / max(im.size)
        _emoji_cache[key] = im.resize((max(1, int(im.width*s)), max(1, int(im.height*s))), Image.LANCZOS)
    return _emoji_cache[key]

def ease_out_back(t):
    t = max(0.0, min(1.0, t)); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3*(t-1)**3 + c1*(t-1)**2

def ease_out(t):
    t = max(0.0, min(1.0, t)); return 1 - (1-t)**3

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
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    g = np.clip(y*0.8 + (x-0.5)**2*0.6, 0, 1)
    arr = np.zeros((H, W, 3), np.float32)
    for i in range(3): arr[..., i] = BG1[i]*(1-g) + BG2[i]*g
    # soft glow circle
    d = np.sqrt((x-0.5)**2 + ((y-0.36)*0.56)**2)
    glow = np.clip(1 - d/0.45, 0, 1)**2 * 38
    arr += glow[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

BG = make_bg()

def render_scene(sc, idx, n, dur, total_before, total, out):
    accent = hex2rgb(sc.get("accent", "#B6F35C"))
    nf = int(round(dur*FPS))
    tmp = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
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
    ftag = ImageFont.truetype(FONT_BOLD, 40); ffoot = ImageFont.truetype(FONT_MED, 30)
    emojis = sc.get("emoji", [])
    for fi in range(nf):
        t = fi/FPS
        im = BG.copy(); dr = ImageDraw.Draw(im)
        # progress bar
        prog = (total_before + t)/total
        dr.rounded_rectangle([60, 70, W-60, 82], 6, fill=(255, 255, 255, 60) if False else (40, 80, 66))
        dr.rounded_rectangle([60, 70, 60 + int((W-120)*prog), 82], 6, fill=accent)
        dr.text((W//2, 135), "@DiabeticEats", font=ftag, fill=(200, 230, 215), anchor="mm")
        # emoji row / stat block
        top = 330
        if sc.get("stat"):
            st = sc["stat"]; colw = (W-120)//len(st)
            for k, (lab, val) in enumerate(st):
                a = ease_out_back((t - 0.15 - k*0.35)/0.45)
                if a <= 0: continue
                cx = 60 + colw*k + colw//2
                box = [cx-colw//2+20, top, cx+colw//2-20, top+430]
                col = accent if k == 0 else (235, 235, 235)
                card = Image.new("RGBA", (box[2]-box[0], box[3]-box[1]), (0, 0, 0, 0))
                cd = ImageDraw.Draw(card)
                cd.rounded_rectangle([0, 0, card.width-1, card.height-1], 40, fill=(255, 255, 255, 30), outline=col + (255,), width=6)
                cd.text((card.width//2, 90), lab, font=fstat_l, fill=col, anchor="mm")
                cd.text((card.width//2, 260), val, font=fstat_v, fill=WHITE, anchor="mm")
                s = max(0.01, a)
                card = card.resize((max(1, int(card.width*s)), max(1, int(card.height*s))))
                im.paste(card, (cx - card.width//2, top + 215 - card.height//2), card)
            top_text = top + 500
        elif emojis:
            n_e = len(emojis); size = 300 if n_e == 1 else (240 if n_e == 2 else 190 if n_e == 3 else 170)
            gap = 30; tot = n_e*size + (n_e-1)*gap; x0 = (W - tot)//2
            for k, e in enumerate(emojis):
                a = ease_out_back((t - 0.1 - k*0.15)/0.5)
                if a <= 0: continue
                bob = math.sin(t*2.2 + k)*10
                ei = emoji_img(e, max(1, int(size*a)))
                cx = x0 + k*(size+gap) + size//2
                im.paste(ei, (cx - ei.width//2, int(top + 160 - ei.height//2 + bob)), ei)
            top_text = top + 400
        else:
            top_text = 520
        # headline
        a = ease_out((t - 0.25)/0.45)
        if a > 0:
            y = top_text + int((1-a)*60)
            lh = fh.size*1.12
            layer = Image.new("RGBA", (W, int(lh*len(hlines))+40), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            for li, line in enumerate(hlines):
                col = accent if li == len(hlines)-1 and len(hlines) > 1 else CREAM
                ld.text((W//2+5, int(li*lh)+5), line, font=fh, fill=(0, 0, 0, 120), anchor="mt")
                ld.text((W//2, int(li*lh)), line, font=fh, fill=col, anchor="mt")
            if a < 1: layer.putalpha(layer.getchannel("A").point(lambda v: int(v*a)))
            im.paste(layer, (0, y), layer)
            yb = y + int(lh*len(hlines)) + 20
            for li, line in enumerate(slines):
                dr.text((W//2, yb + li*68), line, font=fsub, fill=(210, 235, 222), anchor="mt")
        # caption box with word reveal
        frac = min(1.0, t/max(0.1, speak_end))
        shown = int(np.searchsorted(cum, frac, side="right")) + 1
        clines = wrap(dr, sc["say"], fcap, W-200)
        # pick a window of up to 3 lines around current word
        wi = 0; line_of = []
        for li, l in enumerate(clines):
            for _ in l.split(): line_of.append(li)
        cur_line = line_of[min(shown, len(words))-1]
        start = max(0, min(cur_line, len(clines)-2)) if len(clines) > 2 else 0
        win = clines[start:start+2]
        by = 1340; boxh = 84*len(win)+60
        dr.rounded_rectangle([70, by, W-70, by+boxh], 36, fill=(0, 0, 0))
        wcount = sum(len(l.split()) for l in clines[:start])
        for li, l in enumerate(win):
            ws = l.split(); lw = dr.textlength(l, font=fcap); x = (W-lw)/2
            for w in ws:
                wcount += 1
                col = accent if wcount == shown else (WHITE if wcount < shown else (120, 140, 132))
                dr.text((x, by+30+li*84), w, font=fcap, fill=col)
                x += dr.textlength(w + " ", font=fcap)
        if sc.get("footer"):
            dr.text((W//2, 1830), sc["footer"], font=ffoot, fill=(170, 200, 188), anchor="mm")
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait()
    if p.returncode == 0: os.replace(tmp, out)
    else: raise SystemExit("ffmpeg failed")

def main(script_path, out_path):
    sc = json.load(open(script_path))
    work = os.path.splitext(out_path)[0] + "_work"; os.makedirs(work, exist_ok=True)
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(TTS, "kokoro.onnx"), os.path.join(TTS, "voices.bin"))
    durs, auds, sr = [], [], 24000
    for i, s in enumerate(sc["scenes"]):
        a, sr = k.create(s["say"], voice=sc.get("voice", "af_heart"), speed=sc.get("speed", 1.05), lang="en-us")
        pad = np.zeros(int(sr*0.3), np.float32)
        a = np.concatenate([np.zeros(int(sr*0.05), np.float32), a, pad])
        auds.append(a); durs.append(round(len(a)/sr*FPS)/FPS)
    # trim/pad audio to exact frame durations
    full = np.concatenate([np.pad(a, (0, max(0, int(d*sr)-len(a))))[:int(d*sr)] for a, d in zip(auds, durs)])
    sf.write(f"{work}/voice.wav", full, sr)
    total = sum(durs); before = 0; files = []
    only = os.environ.get("ONLY")
    for i, s in enumerate(sc["scenes"]):
        f = f"{work}/s{i:02d}.mp4"; files.append(f)
        if only is None or str(i) in only.split(","):
            render_scene(s, i, len(sc["scenes"]), durs[i], before, total, f)
        before += durs[i]
    with open(f"{work}/list.txt", "w") as fl:
        for f in files: fl.write(f"file '{os.path.abspath(f)}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt",
        "-i", f"{work}/voice.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-movflags", "+faststart", "-shortest", out_path], check=True)
    print("done", out_path, round(total, 2), "s")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
