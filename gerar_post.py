#!/usr/bin/env python3
"""Pega frase do gerar_frase.py, monta o PNG (papel + texto, dia/noite) e salva em out/."""
import random, json, sys
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import gerar_frase

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
OUT = BASE / "out"
OUT.mkdir(exist_ok=True)
F_HAND = str(ASSETS / "Caveat.ttf")
F_SIG = str(ASSETS / "DancingScript.ttf")

W, H = 1080, 1350

PAL_DIA = [
    {"top": (58,40,30), "bot": (232,168,92), "bokeh": (255,214,150), "ink": (38,50,78)},
    {"top": (74,47,58), "bot": (232,160,176), "bokeh": (255,200,214), "ink": (60,38,56)},
    {"top": (34,48,42), "bot": (158,184,156), "bokeh": (205,228,205), "ink": (38,55,46)},
    {"top": (70,44,38), "bot": (240,182,150), "bokeh": (255,212,182), "ink": (70,45,40)},
]

def vgradient(top, bot):
    base = Image.new("RGB", (W, H), top); d = ImageDraw.Draw(base)
    for y in range(H):
        t = (y/H) ** 1.4
        d.line([(0,y),(W,y)], fill=tuple(int(top[i]+(bot[i]-top[i])*t) for i in range(3)))
    return base.convert("RGBA")

def add_bokeh(img, color, n=14):
    layer = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(layer)
    for _ in range(n):
        x=random.randint(-40,W+40); y=random.randint(int(H*0.4),H+40)
        r=random.randint(30,130); a=random.randint(16,50)
        d.ellipse([x-r,y-r,x+r,y+r], fill=color+(a,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(18))); return img

def night_bg():
    top=(11,13,20); bot=(26,20,38)
    base=Image.new("RGB",(W,H),top); dd=ImageDraw.Draw(base)
    for y in range(H):
        t=(y/H)**1.2
        dd.line([(0,y),(W,y)],fill=tuple(int(top[i]+(bot[i]-top[i])*t) for i in range(3)))
    base=base.convert("RGBA")
    glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
    gd.ellipse([W*0.66,120,W*0.66+150,270], fill=(220,225,210,120))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))
    return base

def heart(d,cx,cy,s,fill):
    r=s/2
    d.ellipse([cx-r,cy-r,cx,cy],fill=fill); d.ellipse([cx,cy-r,cx+r,cy],fill=fill)
    d.polygon([(cx-r,cy-r/4),(cx+r,cy-r/4),(cx,cy+r*0.9)],fill=fill)

def edge_mask(pw,ph):
    m=Image.new("L",(pw,ph),0); dm=ImageDraw.Draw(m)
    pts=[(x,random.randint(0,12)) for x in range(0,pw,4)] + \
        [(pw-1-random.randint(0,12),y) for y in range(0,ph,4)] + \
        [(x,ph-1-random.randint(0,12)) for x in range(pw-1,-1,-4)] + \
        [(random.randint(0,12),y) for y in range(ph-1,-1,-4)]
    dm.polygon(pts,fill=255); return m

def make_paper(frase, handle, ink):
    pw,ph=760,720
    paper=Image.new("RGBA",(pw,ph),(0,0,0,0)); d=ImageDraw.Draw(paper)
    d.rounded_rectangle([4,4,pw-4,ph-4],radius=12,fill=(247,242,232,255))
    for y in range(110,ph-70,60): d.line([(60,y),(pw-44,y)],fill=(120,120,140,16),width=1)
    fs=56; font=ImageFont.truetype(F_HAND,fs); maxw=pw-150; wrapped=[]
    for ln in frase.split("\n"):
        if not ln.strip(): wrapped.append(""); continue
        cur=""
        for w in ln.split():
            t=(cur+" "+w).strip()
            if d.textlength(t,font=font)<=maxw: cur=t
            else: wrapped.append(cur); cur=w
        wrapped.append(cur)
    lh=int(fs*1.32); y=(ph-lh*len(wrapped))//2-10
    for ln in wrapped:
        tw=d.textlength(ln,font=font); d.text(((pw-tw)//2,y),ln,font=font,fill=ink+(255,)); y+=lh
    heart(d,pw-130,90,30,ink+(200,)); heart(d,108,ph-118,22,ink+(150,))
    sig=ImageFont.truetype(F_SIG,34); sw=d.textlength(handle,font=sig)
    d.text(((pw-sw)//2,ph-70),handle,font=sig,fill=ink+(175,))
    paper.putalpha(Image.composite(paper.split()[3],Image.new("L",(pw,ph),0),edge_mask(pw,ph)))
    return paper

def compose(frase, handle, modo, outfile):
    if modo == "noite":
        bg = night_bg(); ink = (40,44,72)
    else:
        pal = random.choice(PAL_DIA)
        bg = add_bokeh(vgradient(pal["top"],pal["bot"]), pal["bokeh"]); ink = pal["ink"]
    paper = make_paper(frase, handle, ink).rotate(random.choice([-4,-3,-2,2,3]), expand=True, resample=Image.BICUBIC)
    px=(W-paper.width)//2; py=(H-paper.height)//2
    sh=Image.new("RGBA",bg.size,(0,0,0,0)); a=paper.split()[3].point(lambda v:int(v*0.45))
    sh.paste((0,0,0,255),(px+14,py+20),a); bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    bg.alpha_composite(paper,(px,py)); bg.convert("RGB").save(outfile,quality=92)

def main():
    banco = gerar_frase.carregar_banco()
    estado = gerar_frase.ler_estado()
    modo = gerar_frase.escolher_modo(sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--modo" else None)
    pauta = gerar_frase.escolher_pauta(banco, modo, estado["ultimo_id"])
    system, user = gerar_frase.montar_prompt(banco["config"], pauta, modo)
    print("Gerando frase (pauta", pauta["id"], "modo", modo + ")...")
    out = gerar_frase.gerar(system, user)
    gerar_frase.salvar_estado(pauta["id"])
    handle = banco["config"]["handle"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    png = OUT / ("post_" + ts + ".png")
    compose(out["frase"], handle, modo, str(png))
    (OUT / ("post_" + ts + ".txt")).write_text(out["legenda"] + "\n\n" + " ".join(out["hashtags"]), encoding="utf-8")
    print("FRASE:\n" + out["frase"])
    print("\nPNG salvo em:", png)
    print("Legenda salva em:", str(png).replace(".png", ".txt"))

if __name__ == "__main__":
    main()
