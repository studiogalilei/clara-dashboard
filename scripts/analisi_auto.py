#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ANALISI, DENTRO IL WORKFLOW (Dre, 23/9/2026).

«Dario ha risposto e Clara non ha generato l'analisi... rendi piu' semplice
questa cosa perche' sta nel workflow.» Fino a oggi l'analisi Google Ads viveva
solo sul Mac, nel comando /analisi fatto a mano. Da qui gira in cloud, dopo il
Google Fit e prima delle bozze: chi ha risposto e passa il fit riceve l'analisi
in PDF nella sua scheda, e la bozza in Posta la trova gia' pronta.

COSA FA, per ogni persona che aspetta una risposta e ha il fit letto (non NO):
  1. raccoglie i fatti veri che abbiamo gia': il sito letto, gli annunci
     (Transparency), le recensioni su Maps, i tag del sito (tabella raccolta),
     il Google Fit (settore, provincia, ticket, due cose scomode) e i volumi
     settore x provincia precalcolati (base_analisi.json);
  2. chiede al cervello l'analisi nella struttura Canossa (8 sezioni), col
     playbook e l'esempio di qualita' che stanno nel bucket privato;
  3. la passa dal cancello (le regole di lint_analisi, murate qui);
  4. prende logo e colori del brand, renderizza il PDF col guscio grafico;
  5. carica il PDF nel bucket, mette il link nella scheda (analysis_pdf) e lo
     scrive nella proposta aperta in Posta, cosi' Dre lo trova accanto alla bozza.

IL METODO NON STA NEL REPO (il repo e' pubblico dal 22/9): playbook, esempio,
volumi e guscio grafico stanno in vault/riservato/ su Supabase Storage e si
scaricano a ogni corsa.

Non invia niente: il PDF e la bozza aspettano l'ok di Dre nella Posta.

USO
  analisi_auto.py                       chi e' dovuto (max QUANTI per giro)
  analisi_auto.py --email x@y.it        solo lei, anche se non dovuta
  analisi_auto.py --prova --email ...   fa tutto ma non scrive su Supabase
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import env, sb                                 # noqa: E402
import cervello                                            # noqa: E402
import brand_assets                                        # noqa: E402

PROVA = "--prova" in sys.argv
QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else 4
MODELLO = os.environ.get("MODELLO_ANALISI", "gpt-5")
SB = env("VITE_SUPABASE_URL")
SK = env("SUPABASE_SERVICE_KEY")
CACHE = os.path.join(tempfile.gettempdir(), "odyn-analisi")
VALIDITA_LINK = 60 * 60 * 24 * 365 * 10     # dieci anni (Dre, 24/9: «non voglio analisi che scadono»); prima erano due mesi
# la cartella del vault, se questo gira sul Mac di Dre: copia del PDF anche li'
VAULT_ANALISI = os.path.expanduser("~/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/Analisi")
# come in bozze.py: chi ha chiesto di non essere contattato non riceve niente
NON_TOCCARE = re.compile(r"rimuov|cancell|non (vogliamo|voglio|desider)|non (ci|mi) contatt|non (ci|mi) scriv|privacy|gdpr|"
                         r"diffid|denunc|garante|spam|molest|smett|basta\b|lasciateci|lasciatemi|opt.?out|unsubscribe|disiscri", re.I)
GENERICHE = re.compile(r"^(info|contatti|contact|amministrazione|commerciale|vendite|segreteria|ufficio|mail|posta|direzione|hello|sales|marketing|ordini|preventivi|reception|booking|prenotazioni)@", re.I)


# ── il materiale riservato, dal bucket ──────────────────────────────
def riservato(nome):
    os.makedirs(CACHE, exist_ok=True)
    loc = os.path.join(CACHE, nome)
    if os.path.exists(loc) and time.time() - os.path.getmtime(loc) < 3600:
        return loc
    req = urllib.request.Request(f"{SB}/storage/v1/object/vault/riservato/{nome}",
                                 headers={"apikey": SK, "Authorization": f"Bearer {SK}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        open(loc, "wb").write(r.read())
    return loc


def guscio():
    """Il renderer col suo logo e i font, scompattato una volta."""
    d = os.path.join(CACHE, "renderer")
    if not os.path.exists(os.path.join(d, "render_analisi.py")):
        with zipfile.ZipFile(riservato("renderer.zip")) as z:
            z.extractall(d)
    return d


def python_render():
    """Chi ha weasyprint: il venv sul Mac di Dre, o il python di sistema in cloud."""
    venv = os.path.expanduser("~/.falcon-render-venv/bin/python3")
    return venv if os.path.exists(venv) else sys.executable


# ── i fatti ─────────────────────────────────────────────────────────
def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def dominio(url):
    d = re.sub(r"^https?://", "", (url or "").lower().strip()).split("/")[0]
    return re.sub(r"^www\.", "", d)


def base_volumi():
    return json.load(open(riservato("base_analisi.json"), encoding="utf-8"))


def volumi(settore, provincia):
    for k, v in base_volumi().items():
        s, p = k.split("|", 1)
        if norm(s) == norm(settore) and norm(p) == norm(provincia):
            return v
    return None


def provincia_dal_testo(*testi):
    """Quando il fit non ha la provincia: la piu' citata fra quelle che conosciamo
    (sito, nome su Maps, recensioni). Dario di Pavia ne e' il caso: il fit l'aveva vuota."""
    province = {k.split("|", 1)[1] for k in base_volumi()}
    testo = norm(" ".join(t for t in testi if t))
    conta = {p: len(re.findall(r"\b" + re.escape(norm(p)) + r"\b", testo)) for p in province}
    migliore = max(conta, key=conta.get) if conta else None
    return migliore if migliore and conta[migliore] > 0 else ""


def data_it(iso):
    mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    try:
        d = datetime.date.fromisoformat((iso or "")[:10])
        return f"{d.day} {mesi[d.month - 1]} {d.year}"
    except Exception:
        return "di recente"


def persona(p):
    if p.get("name"):
        return p["name"].strip()
    mail = (p.get("email") or "").lower()
    if GENERICHE.match(mail):
        return ""
    m = re.match(r"^([a-z]+)\.([a-z]+)@", mail)
    return f"{m.group(1).capitalize()} {m.group(2).capitalize()}" if m else ""


def scheda(p):
    dom = dominio(p.get("website"))
    fit = (p.get("enriched") or {}).get("google_fit") or {}
    racc = (sb("GET", f"/rest/v1/raccolta?select=azienda,fa_ads,annunci,giorni_ads,inserzionista,maps_trovato,recensioni,voto,tipo_maps,"
                      f"recensioni_testi,sito_testo,raccolto_il,tag_google_ads,tag_analytics,tag_tag_manager,tag_clarity,tag_meta_pixel"
                      f"&dominio=eq.{urllib.parse.quote(dom)}") or [{}])[0] if dom else {}
    ultime = sb("GET", f"/rest/v1/interactions?select=body,at&prospect_id=eq.{p['id']}&kind=eq.email_in&order=at.desc&limit=2") or []
    provincia = fit.get("provincia") or p.get("city") or ""
    if not provincia:
        provincia = provincia_dal_testo(racc.get("azienda"), racc.get("sito_testo"),
                                        " ".join((t.get("testo") or "") for t in (racc.get("recensioni_testi") or []) if isinstance(t, dict)))
    vol = volumi(fit.get("settore") or p.get("sector"), provincia) if provincia else None
    return {"dominio": dom, "fit": fit, "raccolta": racc, "ultime": ultime, "volumi": vol, "provincia": provincia}


def fatti_in_testo(s, p):
    r, fit, vol = s["raccolta"], s["fit"], s["volumi"]
    righe = [f"Azienda: {p.get('company') or r.get('azienda') or s['dominio']}",
             f"Sito: {s['dominio']}",
             f"Persona: {persona(p) or 'non nota (mail generica)'}",
             f"Settore (dal fit): {fit.get('settore')} | Provincia: {s['provincia'] or '?'} | Raggio: {fit.get('raggio')} | Tipo: {fit.get('tipo')}",
             f"Cosa fa (dal fit): {fit.get('cosa_fa')}",
             f"Ticket stimato: {fit.get('ticket')} | Vendita possibile online: {fit.get('vendita_possibile_online')}",
             f"Due cose scomode (dal fit): {fit.get('due_cose_scomode')}",
             f"Da sistemare (dal fit): {fit.get('da_sistemare')}",
             f"Verdetto fit: {fit.get('verdetto')} ({fit.get('motivo')})"]
    if r:
        quando = data_it(r.get("raccolto_il"))
        if r.get("fa_ads"):
            righe.append(f"ANNUNCI GOOGLE (Transparency Center, verificato il {quando}): {r.get('annunci')} annunci attivi, "
                         f"il piu' vecchio da {r.get('giorni_ads')} giorni, inserzionista «{r.get('inserzionista')}». TIPO A: fanno gia' pubblicita'.")
        else:
            righe.append(f"ANNUNCI GOOGLE (Transparency Center, verificato il {quando}): nessun annuncio attribuibile con certezza. TIPO B (assenza non vuol dire no).")
        if r.get("maps_trovato"):
            righe.append(f"GOOGLE MAPS (verificato il {quando}): {r.get('recensioni')} recensioni, voto {r.get('voto')}, categoria «{r.get('tipo_maps')}».")
            testi = [t for t in (r.get("recensioni_testi") or [])[:4] if isinstance(t, dict)]
            if testi:
                righe.append("Recensioni (estratti): " + " | ".join(f"[{t.get('voto')}★] {(t.get('testo') or '')[:160]}" for t in testi))
        tag = [n for n, k in (("Google Ads", "tag_google_ads"), ("Analytics", "tag_analytics"), ("Tag Manager", "tag_tag_manager"),
                              ("Clarity", "tag_clarity"), ("Meta Pixel", "tag_meta_pixel")) if r.get(k)]
        righe.append(f"TAG SUL SITO (verificato il {quando}): {', '.join(tag) if tag else 'nessuno rilevato'}.")
        if r.get("sito_testo"):
            righe.append("TESTO DEL SITO (estratto):\n" + r["sito_testo"][:3500])
    if vol:
        serie = vol.get("serie") or []
        righe.append(f"VOLUMI (Keyword Planner, settore x provincia, precalcolati): domanda {vol.get('tam'):,} ricerche/mese nella provincia, "
                     f"CPC medio cima pagina {vol.get('cpc_medio')} €, mesi vivi {vol.get('mesi_vivi')}/12. "
                     f"Serie mensile da settembre a agosto: {serie}. Cluster con volumi: "
                     + ", ".join(f"{t['k']} ({t['n']})" for t in (vol.get("top") or [])[:10]))
    else:
        righe.append("VOLUMI: non precalcolati per questa coppia settore/provincia. Non inventare numeri: parla di domanda in termini qualitativi e dichiara «valutazione di Studio Galilei sul settore».")
    if fit.get("esclusione") == "onlus":
        righe.append("ATTENZIONE: e' una ONLUS / ONG. L'angolo dell'analisi e' GOOGLE AD GRANTS (fino a 10.000 $ al mese di annunci Search gratis "
                     "per il no profit): donazioni, 5x1000, volontari, servizi ai beneficiari. Niente «ottimizzazione degli annunci a pagamento».")
    if s["ultime"]:
        righe.append("COSA CI HA SCRITTO (ultimo messaggio):\n" + (s["ultime"][0].get("body") or "")[:1200])
    return "\n".join(righe)


# ── il cervello ─────────────────────────────────────────────────────
CHIUSURA = "Non è una promessa di risultato, è una lettura concreta della domanda che oggi esiste intorno a voi."
ISTRUZIONE = """
Scrivi l'ANALISI GOOGLE ADS per questa azienda, seguendo il playbook e le linee
guida qui sopra e la qualita' dell'esempio. Registro «voi», tono da lettura
esterna competente: specifica su di loro, onesta, mai generica. Ogni sezione
aggiunge qualcosa, niente ripetizioni. Tipo A/B coerente coi fatti: se fanno
gia' annunci, il margine sta nella selezione; se no, di' che non si vede
pubblicita' attribuibile con certezza. I FATTI VERIFICATI vanno USATI nel testo
con le parole «verificato dal vivo il <data>» o «abbiamo controllato» (annunci,
recensioni, tag). I numeri li usi solo se stanno nei fatti: i volumi vanno
dichiarati «stima da Keyword Planner per il settore nella provincia». Niente
prima persona («io e Lorenzo», «insieme al mio collega»). MAI il trattino
lungo. Niente firma ne' inviti finali: la pagina finale la mette il guscio.
Apostrofi negli attributi HTML: singoli. Testo in italiano corretto con gli
accenti veri (è, più, città).

RISPONDI SOLO CON UN JSON (niente testo prima o dopo, niente ```), con:
{
 "type": "education" oppure "account" (account = fanno gia' pubblicita' e si lavora sul loro account),
 "intro": "2-3 frasi secche per la copertina, con l'obiettivo concreto del cliente, che chiudono ESATTAMENTE con: %s",
 "bars": [[altezza 0-100, hi 0/1] x 12, da gennaio a dicembre, sui picchi reali del settore],
 "body": "HTML delle 8 sezioni"
}
Il body: otto <section class='sec'> (dalla seconda in poi class='sec brk'), ognuna con
<div class='k'>N: Nome</div> con questi nomi esatti: 1: Lettura iniziale, 2: Domanda,
3: Filtro utile, 4: Percorsi, 5: Copertura e geografia, 6: Stagionalità, 7: Credibilità,
8: Osservazione finale. Poi <h2> a frase intera (l'insight, non un'etichetta),
<p class='dek'> sottotitolo, poi paragrafi <p>. La sezione 2 ha una <table> con
intestazioni Area di ricerca | Lettura utile | Priorità e in ogni riga
<span class='tag'>alta</span> / da qualificare / da filtrare / aziende / stagionale / difensiva
e la parola chiave in <span class='kw'>. La 4 ha un <ul>. La 6 contiene la riga
[[SEASON]] da sola, e una frase che dichiara il grafico «valutazione di Studio Galilei sul settore».
La 8 chiude con <div class='bomba'><p>la frase forte</p></div>.
Lunghezza: come l'esempio, 3-4 pagine di testo denso, frasi lunghe e naturali.
""" % CHIUSURA


def chiedi(p, s, correzioni=None):
    prompt = (cervello.manuale("testa", "analisi") + "\n\n" + ISTRUZIONE + "\n\nI FATTI:\n" + fatti_in_testo(s, p))
    if correzioni:
        prompt += "\n\nLA VERSIONE PRECEDENTE E' STATA BOCCIATA DAL CANCELLO. Correggi questi punti e rispondi di nuovo col JSON completo:\n- " + "\n- ".join(correzioni)
    grezzo = cervello._chiedi(prompt, MODELLO) or ""
    grezzo = grezzo.strip().strip("`")
    grezzo = re.sub(r"^json\s*", "", grezzo)
    try:
        return json.loads(grezzo)
    except Exception:
        m = re.search(r"\{.*\}", grezzo, re.S)
        return json.loads(m.group(0)) if m else None


# ── il cancello (lint_analisi.py, murato qui) ───────────────────────
SEZIONI = ["Lettura iniziale", "Domanda", "Filtro", "Percorsi", ["Copertura", "Geografia"], "Stagionalit", "Credibilit", "Osservazione finale"]


# I NUMERI LI DA' IL CODICE, NON IL MODELLO (da Galileo, 24/9). Ogni numero che
# compare nell'analisi deve stare nei fatti: volumi, CPC, recensioni, annunci,
# date. Se il modello ne inventa uno (un «30% delle ricerche», un «2.300
# aziende»), l'analisi si ferma e lo si dice. Passano i numeri piccoli (fino a
# 12: mesi, elenchi, sezioni), gli anni, e quello che sta nei fatti.
NUMERO = re.compile(r"(?<![\w/])(\d{1,3}(?:[.\s]\d{3})+|\d+(?:[.,]\d+)?)\s*(%|€|\$)?")


def _norma(n):
    n = n.replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", n):
        return n.replace(".", "").replace(",", "")   # 4.400 e 4,400 -> 4400
    return n.replace(",", ".")                        # 3,5 -> 3.5


def numeri_di(testo):
    return {(_norma(m.group(1)), m.group(2) or "") for m in NUMERO.finditer(testo)}


def numeri_non_nei_fatti(tutto, fatti):
    if not fatti:
        return []
    testo = re.sub(r"<[^>]+>", " ", tutto)
    noti = {n for n, _ in numeri_di(fatti)}
    # nei fatti le serie stanno anche come liste json: prendo tutte le cifre
    noti |= {_norma(x) for x in re.findall(r"\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?", fatti)}
    fuori = []
    for n, unita in sorted(numeri_di(testo)):
        try:
            v = float(n)
        except ValueError:
            continue
        if n in noti:
            continue
        if unita == "" and (v <= 12 or 2000 <= v <= 2035):
            continue
        fuori.append(f"{n}{unita}")
    return fuori


def cancello(an, fatti=""):
    errs = []
    intro, body = an.get("intro") or "", an.get("body") or ""
    tutto = intro + " " + body
    inventati = numeri_non_nei_fatti(tutto, fatti)
    if inventati:
        errs.append(f"numeri che non stanno nei fatti: {', '.join(inventati[:8])}. Toglili o usa solo i numeri dei fatti (i numeri li da' il codice, non tu)")
    if "—" in tutto:
        errs.append(f"trattino lungo presente {tutto.count('—')} volte: usa virgola, due punti, o riformula")
    if CHIUSURA.lower()[:40] not in intro.lower():
        errs.append(f"l'intro deve chiudere con: {CHIUSURA}")
    if re.search(r"\bio e (il mio|lorenzo)|\binsieme al mio collega|\bnoi guardiamo\b", tutto, re.I):
        errs.append("prima persona trovata (io e Lorenzo / insieme al mio collega / noi guardiamo)")
    kick = re.findall(r"<div class='k'>\d+:\s*([^<]+)</div>", body)
    manc = [(x[0] if isinstance(x, list) else x) for x in SEZIONI
            if not any(v.lower() in k.lower() for v in (x if isinstance(x, list) else [x]) for k in kick)]
    if manc:
        errs.append(f"sezioni mancanti o rinominate: {manc} (trovate: {kick})")
    if "[[SEASON]]" not in body:
        errs.append("manca [[SEASON]] nella sezione 6")
    bars = an.get("bars")
    if not isinstance(bars, list) or len(bars) != 12 or not all(isinstance(b, list) and len(b) == 2 for b in bars):
        errs.append("bars deve essere una lista di 12 coppie [altezza, hi]")
    if "<table" in body and "<span class='tag'>" not in body:
        errs.append("nella tabella mancano i <span class='tag'> di priorità")
    if "<table" not in body:
        errs.append("manca la tabella della sezione 2 (Domanda)")
    if not re.search(r"verificat|controllo dal vivo|rilevat|abbiamo controllato", tutto, re.I):
        errs.append("i fatti verificati vanno citati nel testo («verificato dal vivo il ...», «abbiamo controllato»)")
    if "class='bomba'" not in body:
        errs.append("manca <div class='bomba'> nella sezione 8")
    if len(re.sub(r"<[^>]+>", "", body)) < 4500:
        errs.append("troppo corta: servono 3-4 pagine di testo denso come l'esempio")
    return errs


# ── il PDF ──────────────────────────────────────────────────────────
def slug_cc(s):
    return re.sub(r"[^A-Za-z0-9]", "", s)


def renderizza(an, p, s):
    dom = s["dominio"]
    logo = ""
    try:
        logo = brand_assets.fetch_client_logo(dom)
        pal = brand_assets.pick_palette(brand_assets.extract_brand_colors(dom, logo))
    except Exception as e:                                   # noqa: BLE001
        print(f"    brand: ripiego sui colori SG ({str(e)[:60]})")
        pal = brand_assets.pick_palette([])
    azienda = p.get("company") or s["raccolta"].get("azienda") or dom
    out = os.path.join(CACHE, f"Analisi_GoogleAds_{slug_cc(azienda)}.pdf")
    cfg = {"company": azienda, "type": an.get("type") or "education", "person": persona(p),
           "intro": an["intro"], "bars": an["bars"], "body": an["body"], "client_logo": logo,
           "out": out, "assets_dir": guscio(), **pal}
    jp = os.path.join(CACHE, f"_render_{slug_cc(dom)}.json")
    json.dump(cfg, open(jp, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([python_render(), os.path.join(guscio(), "render_analisi.py"), jp], capture_output=True, text=True, timeout=300)
    if not os.path.exists(out):
        raise RuntimeError("render fallito: " + (r.stderr or r.stdout)[-300:])
    return out, azienda


def carica_pdf(percorso, dom):
    remoto = f"analisi/{slug_cc(dom)}.pdf"
    data = open(percorso, "rb").read()
    req = urllib.request.Request(f"{SB}/storage/v1/object/vault/{remoto}", data=data, method="POST",
                                 headers={"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/pdf", "x-upsert": "true"})
    with urllib.request.urlopen(req, timeout=300) as r:
        r.read()
    req = urllib.request.Request(f"{SB}/storage/v1/object/sign/vault/{remoto}", data=json.dumps({"expiresIn": VALIDITA_LINK}).encode(),
                                 method="POST", headers={"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        firmato = json.load(r).get("signedURL") or ""
    return f"{SB}/storage/v1{firmato}" if firmato.startswith("/") else firmato


# ── una persona ─────────────────────────────────────────────────────
def lavora(p):
    nome = (p.get("company") or p.get("email"))[:40]
    s = scheda(p)
    if not s["dominio"]:
        print(f"  salto {nome}: senza sito"); return False
    if s["ultime"] and NON_TOCCARE.search(s["ultime"][0].get("body") or ""):
        print(f"  salto {nome}: ha chiesto di non essere contattato"); return False
    an = chiedi(p, s)
    fatti = fatti_in_testo(s, p)
    errori = cancello(an, fatti) if an else ["risposta non in JSON"]
    if errori:
        print(f"    bocciata una volta: {'; '.join(errori)[:160]}")
        an = chiedi(p, s, errori)
        errori = cancello(an, fatti) if an else ["risposta non in JSON"]
    if errori:
        # TRATTENUTA CON MOTIVO (da Galileo): non si pubblica, e il motivo resta
        # nella scheda, cosi' nessuno aspetta un PDF che non arriva
        print(f"  {nome}: NON passa il cancello: {'; '.join(errori)[:200]}")
        try:
            arr = dict(p.get("enriched") or {})
            arr["analisi"] = {**(arr.get("analisi") or {}), "trattenuta": "; ".join(errori)[:300], "il": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": arr})
        except Exception as e:                                    # noqa: BLE001
            print(f"    (motivo non scritto: {str(e)[:60]})")
        return False
    pdf, azienda = renderizza(an, p, s)
    print(f"  {nome}: PDF pronto ({os.path.getsize(pdf) // 1024} KB) → {pdf}")
    if os.path.isdir(VAULT_ANALISI):
        shutil.copy(pdf, os.path.join(VAULT_ANALISI, os.path.basename(pdf)))
    if PROVA:
        return True
    link = carica_pdf(pdf, s["dominio"])
    bomba = re.search(r"class='bomba'>\s*<p>(.*?)</p>", an.get("body") or "", re.S)
    arr = dict(p.get("enriched") or {})
    arr["analisi"] = {"intro": re.sub(r"<[^>]+>", "", an.get("intro") or "")[:600], "frase_forte": re.sub(r"<[^>]+>", "", bomba.group(1) if bomba else "")[:300],
                      "tipo": an.get("type"), "fatta_il": datetime.date.today().isoformat()}
    sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"analysis_pdf": link, "enriched": arr})
    # la proposta aperta in Posta: il PDF sta accanto alla bozza
    for pr in sb("GET", f"/rest/v1/proposte?select=id,perche&prospect_id=eq.{p['id']}&tipo=eq.risposta&stato=eq.aperta&limit=3") or []:
        if "Analisi PDF pronta" not in (pr.get("perche") or ""):
            sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"perche": ("Analisi PDF pronta, nella scheda. " + (pr.get("perche") or ""))[:280]})
    return True


MAI = ("agenzia", "portale", "catena", "multinazionale", "privacy")   # franchising va bene (Dre 25/9), tranne i network Tecnocasa che il fit segna


def servita(p):
    """A chi si fa l'analisi (regola 5 di Dre: quando si risponde si manda SEMPRE l'analisi).
    Serve il sito letto e il fit. Il fit NO non ferma chi ha risposto positivo o tiepido:
    l'analisi dira' la verita' scomoda. Le ONLUS la ricevono con l'angolo Ad Grants.
    Mai ad agenzie, portali, catene, multinazionali, chi cita la privacy. Un affiliato in franchising (Century 21, RE/MAX) va bene."""
    fit = (p.get("enriched") or {}).get("google_fit") or {}
    if not fit or not fit.get("sito_letto"):
        return False
    if fit.get("esclusione") in MAI:
        return False
    if fit.get("verdetto") in ("SI", "SI'", "PARZIALE"):
        return True
    return (p.get("classificazione") or "") in ("positivo", "tiepido")


def main():
    a = sys.argv[1:]
    if "--email" in a:
        email = a[a.index("--email") + 1]
        righe = sb("GET", f"/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched,analysis_pdf,classificazione&email=eq.{urllib.parse.quote(email)}")
    else:
        righe = sb("GET", "/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched,analysis_pdf,classificazione"
                          "&fuori=eq.false&analysis_sent=eq.false&analysis_pdf=is.null&or=(awaiting_us.eq.true,coda.not.is.null)&stage=neq.nuovo&passato_a=is.null"
                          "&or=(classificazione.is.null,classificazione.not.in.(fuori_target,soppresso))"
                          "&order=last_reply_at.desc&limit=60") or []
        righe = [p for p in righe if servita(p)][:QUANTI]
    if not righe:
        print("analisi: nessuno da servire"); return
    fatte = 0
    for p in righe:
        try:
            fatte += bool(lavora(p))
        except Exception as e:                               # noqa: BLE001
            print(f"  {(p.get('company') or p.get('email'))[:40]}: errore {str(e)[:160]}")
    print(f"analisi: {fatte} pronte su {len(righe)}")


if __name__ == "__main__":
    main()
