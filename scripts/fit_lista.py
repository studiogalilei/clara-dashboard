#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I TRE FIT SU UNA LISTA NUOVA, PRIMA DELLA CAMPAGNA (4/11/2026).

Dre, 4/11 sera: «crea il Meta Fit e il LinkedIn Fit, così domani ti passo i nuovi lead, facciamo
l'enrichment e prepariamo una campagna outbound con un pubblico più high ticket».

Prende un CSV (o un XLSX) con le aziende, legge ogni sito, chiede al modello cosa vendono e a chi,
e scrive per ognuna il Google fit, il Meta fit e il LinkedIn fit (googlefit.valuta: le stesse regole
di chi risponde), il ticket e il canale consigliato. Non manda niente e non tocca il database, a
meno di --scrivi (solo per chi e' gia' in scheda, per email).

COLONNE: le riconosce dal nome (azienda/company/ragione sociale, sito/website/url, email, citta'/city,
telefono, persona/referente, ruolo). Le altre colonne restano com'erano nel file in uscita.

USO
  python3 scripts/fit_lista.py lista.csv                 tutti, scrive lista_fit.csv e lista_fit.json accanto
  python3 scripts/fit_lista.py lista.csv --prova         le prime 5 righe, a schermo, niente file
  python3 scripts/fit_lista.py lista.csv --senza-ricerche   niente SearchAPI (recensioni, Ad Library, Transparency):
                                                         solo sito + modello, costa meno, i verdetti lo dicono
  python3 scripts/fit_lista.py lista.csv --solo-si       in uscita solo chi ha almeno un SI
  python3 scripts/fit_lista.py lista.csv --scrivi        salva il fit anche in scheda (prospects.enriched.google_fit)
                                                         per chi c'e' gia' per email
  python3 scripts/fit_lista.py lista.csv --fili 3        quante aziende insieme (3 di default)
"""
import csv
import datetime
import functools
import json
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import googlefit                                            # noqa: E402

# come si chiamano le colonne nei file che arrivano (Apollo, Hunter, fogli a mano)
SINONIMI = {
    "azienda": ("azienda", "company", "company name", "ragione sociale", "nome azienda", "organization", "società", "societa", "ditta", "impresa", "account"),
    "sito": ("sito", "website", "web", "url", "sito web", "dominio", "domain", "company website", "site"),
    "email": ("email", "e-mail", "mail", "indirizzo email", "work email"),
    "citta": ("citta", "città", "city", "comune", "localita", "località", "sede", "company city"),
    "telefono": ("telefono", "phone", "cellulare", "mobile", "tel", "numero", "phone number", "mobile phone", "work phone"),
    "persona": ("persona", "referente", "nome", "name", "contatto", "full name", "first name", "contact"),
    "ruolo": ("ruolo", "role", "title", "job title", "posizione", "qualifica"),
}
# 4/11: «un pubblico piu' high ticket». Soglia di Achille: nella stima alta un cliente vale almeno 10.000 €
# (le stime dal sito sono intervalli larghi, «fra 100 e 200.000 €»: la stima bassa da sola non dice niente).
ALTO_TICKET = 10000


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").strip().lower()).strip()


def mappa_colonne(intestazioni):
    """{campo: nome colonna nel file} per i campi che riconosce; una colonna serve un campo solo."""
    out, usate = {}, set()
    for campo, nomi in SINONIMI.items():
        for n in nomi:
            for h in intestazioni:
                if h in usate:
                    continue
                if _norm(h) == _norm(n):
                    out[campo] = h; usate.add(h); break
            if campo in out:
                break
    # «first name» + «last name» → persona intera
    if out.get("persona") and _norm(out["persona"]) == "first name":
        cogn = next((h for h in intestazioni if _norm(h) == "last name"), None)
        if cogn:
            out["cognome"] = cogn
    return out


def leggi_lista(percorso):
    if percorso.lower().endswith((".xlsx", ".xls")):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("per un .xlsx serve openpyxl (pip install openpyxl), oppure esporta in CSV")
        wb = openpyxl.load_workbook(percorso, read_only=True, data_only=True)
        ws = wb.active
        righe = [[("" if v is None else str(v)) for v in r] for r in ws.iter_rows(values_only=True)]
        if not righe:
            return [], []
        intest = [h or f"colonna{i + 1}" for i, h in enumerate(righe[0])]
        return intest, [dict(zip(intest, r)) for r in righe[1:] if any(x.strip() for x in r)]
    with open(percorso, encoding="utf-8-sig", newline="") as f:
        testo = f.read()
    try:
        dialetto = csv.Sniffer().sniff(testo[:4000], delimiters=",;\t")
    except csv.Error:
        dialetto = csv.excel
    lettore = csv.DictReader(testo.splitlines(), dialect=dialetto)
    righe = [r for r in lettore if any((v or "").strip() for v in r.values())]
    return list(lettore.fieldnames or []), righe


def prospect_da(riga, col):
    v = lambda k: (riga.get(col[k]) or "").strip() if col.get(k) else ""   # noqa: E731
    persona = v("persona")
    if col.get("cognome"):
        persona = f"{persona} {(riga.get(col['cognome']) or '').strip()}".strip()
    sito = v("sito")
    if sito and "." in sito and not sito.startswith("http"):
        sito = "https://" + sito
    return {"company": v("azienda"), "website": sito, "email": v("email").lower(), "city": v("citta"),
            "phone": v("telefono"), "name": persona, "role": v("ruolo")}


def senza_ricerche():
    """Niente SearchAPI: recensioni, Meta Ad Library e Transparency Center non si chiedono (i verdetti dicono «non misurato»)."""
    googlefit.recensioni = lambda nome, provincia: None
    googlefit.fa_meta_ads = lambda azienda, dom: None
    import types
    finto = types.ModuleType("pull")
    finto.fa_ads = lambda dom: None
    finto.cerca = lambda *a, **k: {}
    sys.modules["pull"] = finto


def riga_uscita(riga, p, fit):
    g, m, l = fit, fit.get("meta") or {}, fit.get("linkedin") or {}
    tmax = fit.get("ticket_max") or fit.get("ticket_min") or 0
    si = [n for n, f in (("Google", g), ("Meta", m), ("LinkedIn", l)) if f.get("verdetto") == "SI"]
    return {**riga,
            "google_fit": g.get("verdetto"), "google_motivo": g.get("motivo"),
            "meta_fit": m.get("verdetto"), "meta_motivo": m.get("motivo"),
            "linkedin_fit": l.get("verdetto"), "linkedin_motivo": l.get("motivo"),
            "canale": fit.get("canale"), "quanti_si": len(si),
            "ticket": fit.get("ticket"), "ticket_min": fit.get("ticket_min"), "ticket_max": fit.get("ticket_max"), "ticket_fonte": fit.get("ticket_fonte"),
            "alto_ticket": "si" if tmax and tmax >= ALTO_TICKET else "no",
            "tipo": fit.get("tipo"), "settore": fit.get("settore"), "cosa_fa": fit.get("cosa_fa"), "chi_decide": l.get("chi_decide"),
            "dimensione_clienti": l.get("dimensione_clienti"), "provincia": fit.get("provincia"), "raggio": fit.get("raggio"),
            "esclusione": fit.get("esclusione"), "da_sistemare": fit.get("da_sistemare"),
            "fa_google_ads": ((fit.get("google_ads") or {}).get("fa_ads")), "fa_meta_ads": ((m.get("meta_ads") or {}).get("fa_meta_ads")),
            "recensioni": ((fit.get("recensioni") or {}).get("recensioni")), "sito_letto": "si" if fit.get("sito_letto") else "no",
            "sito_usato": p.get("website") or (("https://" + p["email"].split("@")[1]) if "@" in p.get("email", "") else "")}


# il sito si scarica una volta sola (la lettura e' in cache): prima per vedere se si legge, poi dentro valuta
googlefit.leggi_sito = functools.lru_cache(maxsize=4096)(googlefit.leggi_sito)


def valuta_una(args):
    i, riga, p, zone, settori = args
    nome = p.get("company") or p.get("email") or f"riga {i + 2}"
    try:
        from stanza import sito_vero
        # 4/11: un sito che non si legge (bloccato, lento, vuoto) NON si manda al modello: inventerebbe un'azienda.
        # Si dice «non leggibile» e la riga si guarda a mano. Niente spesa, niente verdetto finto.
        if not googlefit.leggi_sito(sito_vero(p)):
            return i, riga, p, None, f"{nome}: sito non leggibile ({sito_vero(p)}): da guardare a mano"
        fit = googlefit.valuta(p, zone, settori)
        return i, riga, p, fit, None
    except Exception as e:                                   # noqa: BLE001
        return i, riga, p, None, f"{nome}: {str(e)[:90]}"


def scrivi_in_scheda(p, fit):
    """Solo per chi e' gia' in scheda (per email): il fit nuovo prende il posto del vecchio."""
    from stanza import sb
    if not p.get("email"):
        return "senza email"
    r = sb("GET", f"/rest/v1/prospects?select=id,enriched&email=eq.{urllib.parse.quote(p['email'])}") or []
    if not r:
        return "non in scheda"
    fit = dict(fit, valutato_il=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), tentativi=1, da="fit_lista")
    sb("PATCH", f"/rest/v1/prospects?id=eq.{r[0]['id']}", {"enriched": {**(r[0].get("enriched") or {}), "google_fit": fit}}, {"Prefer": "return=minimal"})
    return "scritto"


def main():
    argv = sys.argv[1:]
    file = next((a for a in argv if not a.startswith("--") and os.path.exists(a)), None)
    if not file:
        raise SystemExit(__doc__)
    prova, scrivi, solo_si = "--prova" in argv, "--scrivi" in argv, "--solo-si" in argv
    fili = int(argv[argv.index("--fili") + 1]) if "--fili" in argv else 3
    if "--senza-ricerche" in argv:
        senza_ricerche()
    intest, righe = leggi_lista(file)
    col = mappa_colonne(intest)
    print(f"{len(righe)} righe; colonne riconosciute: " + ", ".join(f"{k}={v}" for k, v in col.items()))
    if "azienda" not in col and "sito" not in col and "email" not in col:
        raise SystemExit("non trovo ne' l'azienda, ne' il sito, ne' l'email: rinomina le colonne (azienda / sito / email)")
    if prova:
        righe = righe[:5]
    zone, settori = googlefit.carica_fogli()
    lavori = [(i, r, prospect_da(r, col), zone, settori) for i, r in enumerate(righe)]
    # chi non ha ne' sito ne' email con dominio non si puo' leggere: si dice, non si paga
    da_fare, uscita, errori, fits = [], [None] * len(righe), [], {}
    for w in lavori:
        p = w[2]
        from stanza import sito_vero
        if not sito_vero(p):
            uscita[w[0]] = {**w[1], "google_fit": "", "meta_fit": "", "linkedin_fit": "", "canale": "", "google_motivo": "senza sito ne' email aziendale: non valutabile"}
            errori.append(f"{p.get('company') or 'riga ' + str(w[0] + 2)}: senza sito")
            continue
        da_fare.append(w)
    conti = {"google": {}, "meta": {}, "linkedin": {}, "canale": {}, "alto_ticket": 0}
    with ThreadPoolExecutor(max_workers=max(1, fili)) as ex:
        for i, riga, p, fit, err in ex.map(valuta_una, da_fare):
            nome = (p.get("company") or p.get("email") or "")[:30]
            if err:
                errori.append(err); uscita[i] = {**riga, "google_motivo": "non valutata: " + err}
                print(f"  ?        {nome:30} {err[:70]}")
                continue
            u = riga_uscita(riga, p, fit)
            uscita[i] = u; fits[i] = fit
            for k, v in (("google", u["google_fit"]), ("meta", u["meta_fit"]), ("linkedin", u["linkedin_fit"]), ("canale", u["canale"])):
                conti[k][v] = conti[k].get(v, 0) + 1
            conti["alto_ticket"] += u["alto_ticket"] == "si"
            print(f"  G {u['google_fit']:8} M {u['meta_fit']:8} L {u['linkedin_fit']:8} {nome:30} {u['ticket'] or '':22} {u['canale']}")
            if scrivi and not prova:
                try:
                    print(f"           in scheda: {scrivi_in_scheda(p, fit)}")
                except Exception as e:                       # noqa: BLE001
                    print(f"           in scheda: non scritto ({str(e)[:60]})")
    valutate = sum(1 for u in uscita if u and u.get("google_fit"))
    print(f"\nfit su lista: {valutate} valutate, {len(errori)} non valutabili (senza sito o sito non leggibile); alto ticket (stima alta ≥ {ALTO_TICKET} €): {conti['alto_ticket']}")
    for k in ("google", "meta", "linkedin", "canale"):
        print(f"  {k:9} " + ", ".join(f"{v}: {n}" for v, n in sorted(conti[k].items(), key=lambda x: -x[1])))
    if prova:
        print("(prova: niente file scritto)")
        return
    if solo_si:
        uscita = [u if (u and u.get("quanti_si")) else None for u in uscita]
    base = re.sub(r"\.(csv|xlsx|xls)$", "", file, flags=re.I)
    campi = list(dict.fromkeys(list(intest) + [k for u in uscita if u for k in u.keys()]))
    with open(base + "_fit.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campi, extrasaction="ignore")
        w.writeheader()
        for u in uscita:
            if u:
                w.writerow({k: ("" if v is None else v) for k, v in u.items()})
    # il JSON tiene tutto (anche il testo del sito): e' la base dell'enrichment e dell'analisi
    with open(base + "_fit.json", "w", encoding="utf-8") as f:
        json.dump([{"riga": u, "fit": fits.get(i)} for i, u in enumerate(uscita) if u], f, ensure_ascii=False)
    print(f"scritti {base}_fit.csv e {base}_fit.json")


if __name__ == "__main__":
    main()
