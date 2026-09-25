#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CARICA I LEAD NELLE SEI CAMPAGNE (22/9/2026).

Prende i CSV in ~/Desktop/CAMPAGNE 22-09 (uno per campagna, generati dal fit)
e li carica su Smartlead a lotti di 100. azienda e icebreaker vanno come
campi personalizzati con quel nome esatto: e' cosi' che li leggono i copy.

Non tocca lo stato della campagna: restano in bozza, lo Start e' di Dre.

USO
  carica_lead_campagne.py --una 4003944     solo quella (per provare)
  carica_lead_campagne.py                   tutte e sei
"""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "https://server.smartlead.ai/api/v1"
D = os.path.expanduser("~/Desktop/CAMPAGNE 22-09")

CAMP = {  # id: prefisso del file
    4003942: "CECCHINO_non_fa_ads_",
    4003943: "CECCHINO_investe_",
    4003944: "CECCHINO_paga_ma_fermo_",
    4003946: "STRASCICO_non_fa_ads_",
    4003947: "STRASCICO_investe_",
    4003948: "STRASCICO_paga_ma_fermo_",
}


def chiave():
    for riga in open(os.path.expanduser("~/.hermes/config.yaml"), encoding="utf-8"):
        m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", riga)
        if m:
            return m.group(1).strip("\"'")
    sys.exit("manca SMARTLEAD_API_KEY")


K = chiave()


def api(metodo, p, corpo=None):
    sep = "&" if "?" in p else "?"
    req = urllib.request.Request(f"{BASE}{p}{sep}api_key={K}",
                                 data=json.dumps(corpo).encode() if corpo is not None else None,
                                 method=metodo, headers={"User-Agent": "clara/1.0", "Content-Type": "application/json"})
    for t in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            corpo_err = e.read()[:200].decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and t < 3:
                time.sleep(5 * (t + 1)); continue
            raise RuntimeError(f"{e.code} {metodo} {p}: {corpo_err}")
        except Exception:
            if t < 3:
                time.sleep(5 * (t + 1)); continue
            raise


# ── IL CONTROLLO EMAIL (23/9/2026): 1.149 email sbagliate erano finite in campagna
# (PEC, supporto Webador, sentry di Wix, maria@esempio.it, mario.rossi@, gmail.co,
# privacy@, Comuni). Il fit guarda il sito, l'email non la guardava nessuno.
# Da qui in poi chi non passa non si carica, e si dice quante e perche'.
VENDOR = ("webador", "wixpress", "sentry", "wix.com", "jimdo", "shopify", "prestashop", "qodeinteractive", "squarespace", "weebly",
          "godaddy", "ionos", "register.it", "siteground", "wordpress", "elementor", "iubenda", "cookiebot", "instagram.com", "facebook.com",
          "casa.it", "casa.com", "immobiliare.it", "idealista", "subito.it", "paginegialle", "paginesi", "altervista", "readymag", "site123",
          "b12sites", "website.com", "eclouditalia", "ocalab", "blu.it")
FINTI_DOM = re.compile(r"^(esempio|example|dominio|domain|tuodominio|tuosito|yourdomain|yoursite|azienda|nomeazienda|sito|website|address|"
                       r"youremail|mailservice|placeholder|test|xxx|nome|tuamail|miosito|miaazienda|server|host|localhost|ilmiosito|providermail|echoecho|xyz)\.(it|com|net|org|eu)$|\.(local|test|example|invalid)$")
FINTI_LP = re.compile(r"^(mario\.?rossi|mario\.?bianchi|paolo\.?rossi|giuseppe\.?verdi|nome\.?cognome|nomecognome|tuo\.?nome|test|prova|esempio|example|"
                      r"email|mail|name\.?surname|john\.?doe|user|utente|nome|cognome|tua\.?email|tuamail|xxx+|aaa+|abc|indirizzo|indirizzoemail|[0-9]+)$")
# 25/9 (Dre: «mail di supporto, fanno schifo»): anche le caselle di servizio non entrano
TECNICHE = re.compile(r"^(noreply|no-reply|no_reply|donotreply|sentry|privacy|abuse|postmaster|mailer-daemon|dpo|unsubscribe|cookie|gdpr"
                      r"|support|supporto|assistenza|help|helpdesk|customercare|customerservice|customer\.service|ticket|servizioclienti|clienti"
                      r"|newsletter|webmaster|hr|risorseumane|jobs|lavoraconnoi|careers|recruiting|fatture|fatturazione|amministrazione|contabilita"
                      r"|billing|ordini|orders|prenotazioni|booking|reception|segreteria)([\w.-]*)$")
REFUSI = {"gmail.co", "gmail.comt", "gmail.it", "gmial.com", "gmal.com", "gamil.com", "gmail.con", "gmail.cm", "hotmal.it", "hotmail.i", "libero.com",
          "yahoo.i", "gmail.om", "gmai.com", "hotmail.co", "outlook.i", "libero.i", "icloud.it", "gmail.cpm", "gmail.comm"}
PEC = {"ticertifica.it", "pcert.it", "postacertificata.com", "sicurezzapostale.it", "postecert.it", "legalmail.it", "legalmail.com"}


def perche_sporca(email):
    """Il motivo per cui NON si carica, o None se e' pulita."""
    e = (email or "").strip().lower()
    if not re.match(r"^[a-z0-9._%+\-']+@[a-z0-9.\-]+\.[a-z]{2,}$", e):
        return "formato"
    lp, d = e.split("@", 1)
    if d in REFUSI:
        return "refuso freemail"
    if FINTI_DOM.search(d) or FINTI_LP.match(lp):
        return "email finta"
    if any(d == v or d.endswith("." + v) for v in VENDOR) or any(k in d for k in ("webador", "wixpress", "sentry")):
        return "piattaforma / chi ha fatto il sito"
    if d in PEC or "legalmail" in d or d.startswith("cert.") or any(l.startswith("pec") or l.endswith("pec") for l in d.split(".")) or lp == "pec":
        return "PEC"
    if TECNICHE.match(lp):
        return "casella tecnica"
    if "comune." in d or d.startswith("comune") or d.endswith(".gov.it") or "regione." in d or "provincia." in d:
        return "ente pubblico"
    return None


def carica(cid):
    pref = CAMP[cid]
    file = [f for f in os.listdir(D) if f.startswith(pref)]
    if not file:
        print(f"  {cid}: manca il file {pref}*"); return
    tutte = list(csv.DictReader(open(os.path.join(D, file[0]), encoding="utf-8")))
    scarti = {}
    righe = []
    for r in tutte:
        m = perche_sporca(r.get("email"))
        if m:
            scarti[m] = scarti.get(m, 0) + 1
        else:
            righe.append(r)
    print(f"  {file[0]}: {len(tutte)} lead, {len(righe)} da caricare" + (f", NON caricati {sum(scarti.values())}: {scarti}" if scarti else ""))
    tot = {"caricati": 0, "doppioni": 0, "bloccati": 0, "non_validi": 0}
    for i in range(0, len(righe), 100):
        lotto = [{
            "email": r["email"].strip().lower(),
            "first_name": (r.get("first_name") or "").strip(),
            "website": (r.get("website") or "").strip(),
            "custom_fields": {"azienda": (r.get("azienda") or "").strip(),
                              "icebreaker": (r.get("icebreaker") or "").strip()},
        } for r in righe[i:i + 100] if r.get("email")]
        esito = api("POST", f"/campaigns/{cid}/leads", {
            "lead_list": lotto,
            "settings": {"ignore_global_block_list": False,
                         "ignore_unsubscribe_list": False,
                         "ignore_duplicate_leads_in_other_campaign": False},
        })
        tot["caricati"] += esito.get("upload_count", 0)
        tot["doppioni"] += esito.get("duplicate_count", 0)
        tot["bloccati"] += esito.get("block_count", 0)
        tot["non_validi"] += esito.get("invalid_email_count", 0)
        if (i // 100) % 10 == 9:
            print(f"     {i + len(lotto)}/{len(righe)}  {tot}", flush=True)
        time.sleep(0.4)
    print(f"  → {tot}")
    return tot


def main():
    args = sys.argv[1:]
    quali = [int(args[args.index("--una") + 1])] if "--una" in args else list(CAMP)
    for cid in quali:
        carica(cid)


if __name__ == "__main__":
    main()
