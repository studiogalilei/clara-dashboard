# -*- coding: utf-8 -*-
"""Estrae logo (data URI) + palette REGOLA COLORI per ogni dominio — porting verbatim da falcon_bridge.py."""
import re, json, os, base64, io
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from collections import Counter
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def fetch_client_logo(domain):
    if not domain: return ""
    u = domain if domain.startswith("http") else "https://" + domain
    pr = urlparse(u); base = f"{pr.scheme}://{pr.netloc}"
    def _get(url, timeout=8):
        req = Request(url, headers={"User-Agent": BROWSER_UA, "Accept-Language": "it-IT,it;q=0.9"})
        with urlopen(req, timeout=timeout) as resp: return resp.read(), (resp.headers.get("Content-Type","") or "")
    def _abs(src):
        if not src: return None
        src = src.strip().strip('"').strip("'")
        if src.startswith("data:"): return src
        if src.startswith("//"): return pr.scheme + ":" + src
        if src.startswith("http"): return src
        if src.startswith("/"): return base + src
        return base + "/" + src
    def _to_data_uri(url):
        if url.startswith("data:"): return url if len(url) < 600000 else None
        try: data, ct = _get(url)
        except Exception: return None
        if not data or len(data) < 400 or len(data) > 600000: return None
        ct = ct.split(";")[0].strip().lower()
        if not ct.startswith("image/"):
            ext = os.path.splitext(urlparse(url).path)[1].lower()
            ct = {".svg":"image/svg+xml",".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp",".ico":"image/x-icon",".gif":"image/gif"}.get(ext,"")
            if not ct: return None
        return f"data:{ct};base64," + base64.b64encode(data).decode("ascii")
    candidates = []
    try:
        raw, _ = _get(u, timeout=10); html = raw.decode("utf-8","ignore")
    except Exception: html = ""
    if html:
        for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S|re.I):
            try: obj = json.loads(block.strip())
            except Exception: continue
            stack=[obj]
            while stack:
                it=stack.pop()
                if isinstance(it,dict):
                    lg=it.get("logo")
                    if isinstance(lg,str): candidates.append(lg)
                    elif isinstance(lg,dict) and lg.get("url"): candidates.append(lg["url"])
                    stack.extend(v for v in it.values() if isinstance(v,(dict,list)))
                elif isinstance(it,list): stack.extend(it)
        for m in re.finditer(r'<link[^>]+apple-touch-icon[^>]*>', html, re.I):
            hm=re.search(r'href=["\']([^"\']+)["\']', m.group(0), re.I)
            if hm: candidates.append(hm.group(1))
        for m in re.finditer(r'<img[^>]+>', html, re.I):
            tag=m.group(0)
            if re.search(r'logo', tag, re.I):
                sm=re.search(r'\bsrc=["\']([^"\']+)["\']', tag, re.I)
                if sm: candidates.append(sm.group(1))
        for m in re.finditer(r'<link[^>]+rel=["\'][^"\']*icon[^"\']*["\'][^>]*>', html, re.I):
            hm=re.search(r'href=["\']([^"\']+)["\']', m.group(0), re.I)
            if hm: candidates.append(hm.group(1))
    candidates.append(f"https://www.google.com/s2/favicons?domain={pr.netloc}&sz=128")
    seen=set()
    for c in candidates:
        url=_abs(c)
        if not url or url in seen: continue
        seen.add(url); du=_to_data_uri(url)
        if du: return du
    return ""

def _hx_rgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def _rgb_hx(r,g,b): return "#%02X%02X%02X"%(max(0,min(255,int(r))),max(0,min(255,int(g))),max(0,min(255,int(b))))
def _rgb_hsl(r,g,b):
    r,g,b=r/255,g/255,b/255; mx,mn=max(r,g,b),min(r,g,b); l=(mx+mn)/2
    if mx==mn: return 0.0,0.0,l
    d=mx-mn; s=d/(2-mx-mn) if l>0.5 else d/(mx+mn)
    if mx==r: hh=(g-b)/d+(6 if g<b else 0)
    elif mx==g: hh=(b-r)/d+2
    else: hh=(r-g)/d+4
    return hh/6,s,l
def _hsl_rgb(h,s,l):
    if s==0: v=l*255; return v,v,v
    def _hue(p,q,t):
        t%=1
        if t<1/6: return p+(q-p)*6*t
        if t<1/2: return q
        if t<2/3: return p+(q-p)*(2/3-t)*6
        return p
    q=l*(1+s) if l<0.5 else l+s-l*s; p=2*l-q
    return _hue(p,q,h+1/3)*255,_hue(p,q,h)*255,_hue(p,q,h-1/3)*255
def _lum(h): r,g,b=_hx_rgb(h); return (0.299*r+0.587*g+0.114*b)/255
def _set_l(h,newl): hh,s,l=_rgb_hsl(*_hx_rgb(h)); return _rgb_hx(*_hsl_rgb(hh,max(0.05,s),newl))
def _rel_lum(h):
    def f(c): c=c/255.0; return c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    r,g,b=_hx_rgb(h); return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def _contrast(a,b): la,lb=_rel_lum(a)+0.05,_rel_lum(b)+0.05; return max(la,lb)/min(la,lb)
def _readable_on(color,bg="#FAF8F4",target=4.2):
    hh,s,l=_rgb_hsl(*_hx_rgb(color)); s=min(0.92,max(s,0.40)); out=color
    for _ in range(16):
        if _contrast(out,bg)>=target: return out
        l=max(0.05,l-0.05); out=_rgb_hx(*_hsl_rgb(hh,s,l))
    return out
def _readable_on_dark(color,bg,target=3.4):
    hh,s,l=_rgb_hsl(*_hx_rgb(color)); s=min(0.95,max(s,0.45)); out=color
    for _ in range(18):
        if _contrast(out,bg)>=target: return out
        l=min(0.92,l+0.05); out=_rgb_hx(*_hsl_rgb(hh,s,l))
    return out
def extract_brand_colors(domain,logo_uri=""):
    cands=Counter()
    try:
        u=domain if domain.startswith("http") else "https://"+domain
        html=urlopen(Request(u,headers={"User-Agent":BROWSER_UA}),timeout=10).read().decode("utf-8","ignore")
    except Exception: html=""
    for h in re.findall(r'#([0-9a-fA-F]{6})\b',html): cands["#"+h.lower()]+=1
    for r_,g_,b_ in re.findall(r'rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})',html): cands[_rgb_hx(int(r_),int(g_),int(b_)).lower()]+=1
    if logo_uri and ";base64," in logo_uri:
        b64=logo_uri.split(";base64,",1)[1]
        if "svg" in logo_uri[:30].lower():
            try:
                svg=base64.b64decode(b64).decode("utf-8","ignore")
                for h in re.findall(r'#([0-9a-fA-F]{6})\b',svg): cands["#"+h.lower()]+=10
            except Exception: pass
        else:
            try:
                from PIL import Image
                im=Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA").resize((64,64))
                for cnt,px in (im.getcolors(64*64) or []):
                    r_,g_,b_,a=px
                    if a>=128: cands[_rgb_hx(r_,g_,b_).lower()]+=cnt//15+6
            except Exception: pass
    good=[]
    for hexc,_s in cands.most_common(60):
        try: rr,gg,bb=_hx_rgb(hexc)
        except Exception: continue
        _h,s,l=_rgb_hsl(rr,gg,bb)
        if l>0.92 or l<0.06 or s<0.18: continue
        if any(abs(rr-_hx_rgb(g)[0])+abs(gg-_hx_rgb(g)[1])+abs(bb-_hx_rgb(g)[2])<45 for g in good): continue
        good.append(hexc.upper())
        if len(good)>=5: break
    return good
def pick_palette(colors):
    base={"crema":"#FAF8F4","ink":"#1f2024","line":"#E0DDD5"}
    if not colors: return {"scuro":"#1C2E6E","accento":"#5C9EDD","accento_testo":"#1F5BD0","grad1":"#34386E","grad2":"#1C1E40",**base}
    primary=colors[0]; ph,ps,pl=_rgb_hsl(*_hx_rgb(primary))
    second=next((c for c in colors[1:] if abs(_rgb_hsl(*_hx_rgb(c))[0]-ph)>0.06),None)
    if second is None and ps>0.65:
        scuro=_rgb_hx(*_hsl_rgb(ph,0.16,0.12)); accento=primary if 0.32<=pl<=0.60 else _set_l(primary,0.46)
    else:
        scuro=_rgb_hx(*_hsl_rgb(ph,min(ps,0.50),min(pl,0.18)))
        if second is not None:
            sl=_rgb_hsl(*_hx_rgb(second))[2]; accento=second if 0.32<=sl<=0.62 else _set_l(second,0.48)
        else: accento=_set_l(primary,0.50)
    if _lum(accento)>0.66: accento=_set_l(accento,0.50)
    grad1,grad2=_set_l(scuro,0.27),_set_l(scuro,0.12)
    _g=0
    while _contrast(base["crema"],grad1)<6.0 and _rgb_hsl(*_hx_rgb(scuro))[2]>0.07 and _g<8:
        scuro=_set_l(scuro,max(0.06,_rgb_hsl(*_hx_rgb(scuro))[2]-0.04)); grad1,grad2=_set_l(scuro,0.27),_set_l(scuro,0.12); _g+=1
    if _contrast(accento,grad1)<3.0: accento=_readable_on_dark(accento,grad1,3.4)
    if _rgb_hsl(*_hx_rgb(accento))[1]<0.20 or _contrast(accento,grad1)<2.4:
        return {"scuro":"#1C2E6E","accento":"#5C9EDD","accento_testo":"#1F5BD0","grad1":"#34386E","grad2":"#1C1E40",**base}
    accento_testo=_readable_on(accento,base["crema"])
    return {"scuro":scuro,"accento":accento,"accento_testo":accento_testo,"grad1":grad1,"grad2":grad2,**base}

# USO COME LIBRERIA: import brand_assets → fetch_client_logo/extract_brand_colors/pick_palette.
# Il blocco sotto rigenera /tmp/brand_assets.json SOLO se lanciato direttamente: prima girava
# anche all'import e cancellava gli asset aggiunti dopo (bug 2/7, persi abiovet/hidron/benegas...).
if __name__ == "__main__":
    TARGETS=[
     ("primary-security-key","primarysecuritykey.it","Primary Security Key",""),
     ("bank-station","bankstation.it","Bank Station","Francesco Namari"),
     ("mmbf","mmbf.it","MMBF","Mauro Braghetto"),
     ("jaam","justaboutaminute.com","Jaam Italia","Roberto Gugliermetto"),
     ("remoove","re-moove.it","REMOOVE","Mattia Bonanome"),
     ("say-cheese","saycheesebistrot.com","Say CHEESE Bistrot","Claudio Laurentiis"),
     ("maisons-fatales","maisonsfatales.com","Maisons Fatales","Lidia Roscelli"),
     ("mamashy","mamashy.com","Mamashy","Paulina Switek"),
    ]
    try: out=json.load(open("/tmp/brand_assets.json"))
    except Exception: out={}
    for slug,dom,comp,person in TARGETS:
        logo=fetch_client_logo(dom)
        pal=pick_palette(extract_brand_colors(dom,logo))
        out[slug]={"company":comp,"domain":dom,"person":person,"logo":logo,"palette":pal}
        print(f"{slug:22} logo={'sì' if logo else 'NO':3} scuro={pal['scuro']} accento={pal['accento']}", flush=True)
    json.dump(out,open("/tmp/brand_assets.json","w"))
    print("salvato /tmp/brand_assets.json")
