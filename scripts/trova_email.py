#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TROVA L'EMAIL GIUSTA per le aziende scartate dal verificatore (Dre, 23/9/2026:
«per le altre usiamo un tool affidabile per trovare le mail»).

Per ogni riga di data/campagne_da_rifare.csv:
  1. LEGGE IL SITO (home, contatti, chi siamo): l'email che l'azienda stessa
     pubblica e' quella buona. Prima quelle sul suo dominio, poi una freemail
     se e' l'unica. Hunter qui non serve: sulle piccole aziende italiane non ha
     niente (provato il 23/9: 0 su 12), il sito invece ne ha 2 su 3;
  2. se il sito non ne ha → Hunter Domain Search (chi decide, se no la piu' sicura);
  3. la verifica con Hunter Email Verifier: si tiene solo valid e accept_all;
  4. la carica nella campagna da cui era uscita, con azienda e icebreaker di prima.

Costi: 1 verifica per azienda, 1 ricerca solo dove il sito non dice niente (Starter: 2.000 + 4.000 al mese).
Chiave in ~/.hermes/config.yaml come HUNTER_KEY.

USO
  trova_email.py --prova 20      venti aziende, stampa e non carica
  trova_email.py                 tutte, e carica quelle buone
  trova_email.py --solo-carica   se la ricerca e' gia' fatta (data/campagne_trovate.csv)
"""
import concurrent.futures as cf
import csv
import glob
import ssl
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DA_RIFARE = os.path.join(D, "campagne_da_rifare.csv")
TROVATE = os.path.join(D, "campagne_trovate.csv")
CSV_CAMPAGNE = os.path.expanduser("~/Desktop/CAMPAGNE 22-09")
HUNTER = "https://api.hunter.io/v2"
BASE = "https://server.smartlead.ai/api/v1"
FREE = {"gmail.com", "yahoo.it", "yahoo.com", "hotmail.it", "hotmail.com", "libero.it", "outlook.it", "outlook.com", "live.it", "live.com",
        "tiscali.it", "alice.it", "virgilio.it", "tin.it", "icloud.com", "me.com", "email.it", "fastwebnet.it", "vodafone.it", "msn.com",
        "protonmail.com", "tim.it", "inwind.it", "iol.it", "poste.it", "ymail.com", "googlemail.com", "tiscalinet.it", "bluewin.ch", "mail.com", "mail.it"}
DECIDE = re.compile(r"titolare|owner|ceo|founder|fondat|amministrat|direttor|director|president|responsabile|manager|socio|partner|head", re.I)


def chiave(nome):
    for riga in open(os.path.expanduser("~/.hermes/config.yaml"), encoding="utf-8"):
        m = re.match(rf"\s*{nome}:\s*(\S+)", riga)
        if m:
            return m.group(1).strip("\"'")
    sys.exit(f"manca {nome} in ~/.hermes/config.yaml")


HK = chiave("HUNTER_KEY")


def hunter(percorso, **params):
    params["api_key"] = HK
    url = f"{HUNTER}/{percorso}?" + urllib.parse.urlencode({k: v for k, v in params.items() if v})
    for t in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "clara/1.0"}), timeout=60) as r:
                return json.load(r).get("data") or {}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            if e.code in (429, 500, 502, 503) and t < 3:
                time.sleep(5 * (t + 1)); continue
            return {"errore": f"{e.code} {e.read()[:120].decode(errors='replace')}"}
        except Exception:
            if t < 3:
                time.sleep(5 * (t + 1)); continue
            return {"errore": "rete"}


def dominio(url):
    d = re.sub(r"^https?://", "", (url or "").lower().strip()).split("/")[0]
    return re.sub(r"^www\.", "", d)


CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SPAZZATURA = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|woff2?)$|sentry|wixpress|example|esempio|webador|@[0-9.]+$|^u00|^x@|^[0-9a-f]{20,}@", re.I)


def pagina(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=10, context=CTX) as r:
            return r.read(400000).decode("utf-8", "ignore")
    except Exception:
        return ""


def dal_sito(dom):
    """Le email che l'azienda pubblica sul suo sito: (stesso dominio, freemail)."""
    testo = ""
    for path in ("", "/contatti", "/contatti/", "/contact", "/contacts", "/chi-siamo", "/dove-siamo", "/contattaci"):
        for sch in ("https://", "https://www.", "http://"):
            h = pagina(f"{sch}{dom}{path}")
            if h:
                testo += h; break
    testo = testo.replace("[at]", "@").replace("(at)", "@").replace("&#64;", "@").replace("%40", "@").replace(" [chiocciola] ", "@")
    mails = {m.lower() for m in re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", testo)}
    mails = {m for m in mails if not SPAZZATURA.search(m) and "pec" not in m.split("@")[1] and "legalmail" not in m}
    stesse = sorted(m for m in mails if m.split("@")[1] == dom or m.split("@")[1].endswith("." + dom))
    libere = sorted(m for m in mails if m.split("@")[1] in FREE)
    # fra quelle del dominio: prima una persona (nome@), poi info@, poi il resto
    stesse.sort(key=lambda m: (m.startswith(("info@", "contatti@", "commerciale@", "amministrazione@")), m))
    return stesse, libere


def cerca(r):
    """Una riga → (email, first_name, fiducia, come)."""
    dom = dominio(r["website"])
    if dom and dom not in FREE:
        stesse, libere = dal_sito(dom)
        vecchia = (r["email"] or "").lower()
        buone = [m for m in stesse + libere if m != vecchia]
        if buone:
            lp = buone[0].split("@")[0]
            m = re.match(r"^([a-z]{3,12})\.[a-z]{2,}$", lp)      # nome.cognome@
            nome = m.group(1).title() if m else ""
            return buone[0], nome, 100, "sito"
    if dom and dom not in FREE:
        d = hunter("domain-search", domain=dom, limit=10)
        gente = [e for e in (d.get("emails") or []) if e.get("value")]
        if gente:
            personali = [e for e in gente if e.get("type") == "personal"]
            decide = [e for e in personali if DECIDE.search(e.get("position") or "")]
            scelto = max(decide or personali or gente, key=lambda e: e.get("confidence") or 0)
            return scelto["value"].lower(), (scelto.get("first_name") or "").title(), scelto.get("confidence") or 0, "domain"
    return "", "", 0, "niente"


ERRORI_VISTI = []


def verifica(email):
    """Hunter risponde 202 «ancora in corso» finche' non ha finito: si richiede, conta una volta sola."""
    for t in range(12):
        d = hunter("email-verifier", email=email)
        if d.get("status"):
            return d["status"]
        if d.get("errore"):
            if len(ERRORI_VISTI) < 3:
                ERRORI_VISTI.append(d["errore"]); print(f"  verifica fallita ({email}): {d['errore'][:120]}", flush=True)
            return "errore"
        time.sleep(3)
    return "unknown"


def solo_verifica():
    """Riverifica le righe rimaste in errore o sconosciute (23/9: 663 «errore» per un guasto di rete), poi carica."""
    righe = list(csv.DictReader(open(TROVATE, encoding="utf-8")))
    n = 0
    for r in righe:
        if r["email_nuova"] and r["verifica"] in ("errore", "unknown", ""):
            r["verifica"] = verifica(r["email_nuova"]); n += 1
            if n % 50 == 0:
                print(f"  riverificate {n}", flush=True)
            time.sleep(0.2)
    with open(TROVATE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(righe[0].keys())); w.writeheader(); w.writerows(righe)
    import collections
    print("esiti:", dict(collections.Counter(r["verifica"] for r in righe if r["email_nuova"])))


def icebreakers():
    ice = {}
    for f in glob.glob(os.path.join(CSV_CAMPAGNE, "*.csv")):
        for x in csv.DictReader(open(f, encoding="utf-8")):
            ice[x["email"].strip().lower()] = x["icebreaker"]
    return ice


def cerca_tutte(prova):
    righe = list(csv.DictReader(open(DA_RIFARE, encoding="utf-8")))
    if prova:
        righe = righe[:prova]
    fatte = {}
    if os.path.exists(TROVATE) and not prova:
        fatte = {x["email_vecchia"]: x for x in csv.DictReader(open(TROVATE, encoding="utf-8"))}
    ice = icebreakers()
    campi = ["campagna", "email_vecchia", "azienda", "website", "email_nuova", "first_name", "fiducia", "come", "verifica", "icebreaker"]
    out = open(TROVATE, "a" if fatte else "w", encoding="utf-8", newline="")
    w = csv.DictWriter(out, fieldnames=campi)
    if not fatte:
        w.writeheader()
    conta = {}
    da_fare = [r for r in righe if r["email"] not in fatte]
    with cf.ThreadPoolExecutor(8) as ex:
        trovate = dict(zip((r["email"] for r in da_fare), ex.map(cerca, da_fare)))
    print(f"  siti letti: {len(trovate)}", flush=True)
    for i, r in enumerate(da_fare):
        email, nome, fiducia, come = trovate[r["email"]]
        stato = verifica(email) if email and not prova else ("" if not email else "non verificata (prova)")
        if email == r["email"].lower():
            stato = "uguale alla vecchia"          # Hunter ci ridà quella che rimbalza: non serve
        riga = {"campagna": r["campagna"], "email_vecchia": r["email"], "azienda": r["azienda"], "website": r["website"],
                "email_nuova": email, "first_name": nome, "fiducia": fiducia, "come": come,
                "verifica": stato, "icebreaker": ice.get(r["email"].lower(), "")}
        w.writerow(riga); out.flush()
        k = f"{come}/{stato or 'niente'}"; conta[k] = conta.get(k, 0) + 1
        if prova:
            print(f"  {r['azienda'][:30]:30} {r['email'][:32]:32} → {email or '-':34} {come:6} {fiducia:>3} {stato}")
        elif (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(righe)}  {conta}", flush=True)
        time.sleep(0.2)
    out.close()
    print(f"cercate {len(righe)}: {conta}")


def carica():
    K = chiave("SMARTLEAD_API_KEY")
    righe = [x for x in csv.DictReader(open(TROVATE, encoding="utf-8")) if x["email_nuova"] and x["verifica"] in ("valid", "accept_all", "webmail")]
    per = {}
    viste = set()
    for x in righe:
        if x["email_nuova"] in viste:
            continue
        viste.add(x["email_nuova"])
        per.setdefault(x["campagna"], []).append({"email": x["email_nuova"], "first_name": x["first_name"], "website": x["website"],
                                                  "custom_fields": {"azienda": x["azienda"], "icebreaker": x["icebreaker"]}})
    tot = {"caricati": 0, "doppioni": 0, "bloccati": 0, "non_validi": 0}
    for cid, lotto in per.items():
        for i in range(0, len(lotto), 100):
            corpo = json.dumps({"lead_list": lotto[i:i + 100], "settings": {"ignore_global_block_list": False, "ignore_unsubscribe_list": False,
                                                                           "ignore_duplicate_leads_in_other_campaign": False}}).encode()
            req = urllib.request.Request(f"{BASE}/campaigns/{cid}/leads?api_key={K}", data=corpo, method="POST",
                                         headers={"User-Agent": "clara/1.0", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                e = json.load(r)
            tot["caricati"] += e.get("upload_count", 0); tot["doppioni"] += e.get("duplicate_count", 0)
            tot["bloccati"] += e.get("block_count", 0); tot["non_validi"] += e.get("invalid_email_count", 0)
            time.sleep(0.5)
        print(f"  {cid}: {len(lotto)} lead")
    print(f"caricati nelle campagne: {tot}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--solo-carica" in a:
        carica()
    elif "--solo-verifica" in a:
        solo_verifica(); carica()
    else:
        prova = int(a[a.index("--prova") + 1]) if "--prova" in a else 0
        cerca_tutte(prova)
        if not prova:
            carica()
