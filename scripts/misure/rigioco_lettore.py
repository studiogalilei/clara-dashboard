#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL RIGIOCO DEL LETTORE (20/10/2026): le 1.087 risposte etichettate a mano (A3 di Clara nuova),
ognuna sul suo filo tagliato al momento della risposta, lette dal lettore vero (scripts/lettore.py)
e confrontate con l'etichetta. Accanto, le liste di parole del sync sulle stesse risposte.

I dati NON stanno nel repository (testi e nomi di lead): stanno nel bucket privato «storico» della
sandbox di Clara nuova (tutte/risposte.json, tutte/fili.json), scaricati in una cartella fuori dal
repo. Le letture pagate si salvano nella stessa cartella (cache_<modello>.json): rifare il rigioco
con le stesse regole non costa niente.

Uso:
  python3 scripts/misure/rigioco_lettore.py --dati <cartella> [--modello claude-sonnet-5] [--tetto 10]
                                            [--campione N] [--paralleli 6] [--errori]
  --errori stampa, solo a video, il caso letto e il perche' delle risposte che sbagliano le soglie.

LE SOGLIE DI PROTEZIONE (decise da Dre: devono essere zero, e i caldi tutti):
  si' persi            un si' di A3 letto come negativo, automatico o fuori ufficio
  no letti come si'    un no di A3 (C19, C24, C27, C28) letto come positivo, rinvio o fuori ufficio
  «non scrivetemi» mancati  un C30 di A3 senza non_scrivere
  caldi                chi chiede di sentirsi (A3) segnalato caldo
"""
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, QUI)
# Non scrive niente nel CRM: solo una riga in uso_modelli per ogni chiamata pagata (scopo «lettore-rigioco»).
import lettore as L                                    # noqa: E402

SI = {"C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C15", "C17", "C21", "C35", "C37", "C53"}
NO = {"C19", "C24", "C27", "C28"}
AUTOMATICI_A3 = {"C43", "C44", "C45", "C46", "C47", "C48"}
CALDI = {"VUOLE_CHIAMATA", "CALL_LA_CHIAMA_LUI", "DOPO_ANALISI_VUOLE_CALL", "SI_APRE_CALL", "SI_SCETTICO_APRE_CALL", "CONFERMA_ORARIO"}


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def filo_della_risposta(r, filo):
    """Il filo nella forma del lettore e l'indice della risposta (filoDellaRisposta di Clara nuova)."""
    if filo:
        msgs = filo["messaggi"]
        i = next((k for k, m in enumerate(msgs) if m["tipo"] == "REPLY" and m["at"][:16] == r["at"][:16]), -1)
        if i >= 0:
            fuori = []
            for m in msgs:
                try:
                    passo = int(m.get("passo")) if m["tipo"] == "SENT" and m.get("passo") not in (None, "", "None") else None
                except ValueError:
                    passo = None
                fuori.append({"tipo": "SENT" if m["tipo"] == "SENT" else "REPLY", "il": L._iso(m["at"]), "da": m.get("da"),
                              "cc": None, "oggetto": m.get("oggetto"), "passo": passo if passo and passo > 0 else None,
                              "allegati": None, "testo": L.testo_da_html(m.get("corpo_html"))})
            return fuori, i
    d = r["dati"]
    il = L._iso(r["at"])
    import datetime
    t = datetime.datetime.fromisoformat(il)
    import re
    m = re.search(r"step (\d+)", str(d.get("nostra_prima_tipo") or ""))
    fuori = [{"tipo": "SENT", "il": (t - datetime.timedelta(seconds=60)).isoformat(), "da": None, "cc": None, "oggetto": None,
              "passo": int(m.group(1)) if m else None, "allegati": None, "testo": L.testo_da_html(str(d.get("nostra_prima") or ""))}]
    if d.get("analisi_prima") and all(x["passo"] is not None for x in fuori):
        fuori.append({"tipo": "SENT", "il": (t - datetime.timedelta(seconds=30)).isoformat(), "da": None, "cc": None, "oggetto": None,
                      "passo": None, "allegati": 1, "testo": "(la nostra mail con l'analisi allegata)"})
    fuori.append({"tipo": "REPLY", "il": il, "da": None, "cc": None, "oggetto": None, "passo": None, "allegati": None,
                  "testo": L.normalizza(str(d.get("intero") or d.get("suo") or ""))})
    return fuori, len(fuori) - 1


def main():
    dati = arg("--dati")
    if not dati:
        sys.exit("--dati <cartella con tutte_risposte.json e tutte_fili.json>")
    modello = arg("--modello", L.modello_scelto())
    tetto = float(arg("--tetto", "10"))
    paralleli = int(arg("--paralleli", "6"))
    risposte = json.load(open(os.path.join(dati, "tutte_risposte.json"), encoding="utf-8"))
    fili = {f["id"]: f for f in json.load(open(os.path.join(dati, "tutte_fili.json"), encoding="utf-8"))}
    if arg("--campione"):
        risposte = sorted(risposte, key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())[:int(arg("--campione"))]
    if arg("--ids"):
        ids = set(arg("--ids").split(","))
        risposte = [r for r in risposte if r["id"] in ids]
    percorso_cache = os.path.join(dati, f"cache_{modello}.json")
    cache = json.load(open(percorso_cache, encoding="utf-8")) if os.path.exists(percorso_cache) else {}
    lucchetto = threading.Lock()
    conto = {"spesi": 0.0, "nuove": 0, "cache": 0, "fermato": False, "errori": 0}

    def chiedi(ruolo, istruzioni, testo, schema):
        k = hashlib.sha256(json.dumps([modello, ruolo, istruzioni, testo, schema], ensure_ascii=False).encode()).hexdigest()[:32]
        with lucchetto:
            if k in cache:
                conto["cache"] += 1
                return cache[k]["uscita"], 0.0
            if conto["spesi"] >= tetto:
                conto["fermato"] = True
                raise L.Guasto("tetto")
        uscita, c = L.chiedi_anthropic(ruolo, istruzioni, testo, schema, modello=modello, registra="lettore-rigioco")
        with lucchetto:
            conto["spesi"] += c
            conto["nuove"] += 1
            cache[k] = {"uscita": uscita, "costo": c}
        return uscita, c

    if "--lotti" in sys.argv:
        a_lotti(risposte, fili, modello, cache, percorso_cache, tetto, conto)

    import sync_v2
    esiti = []

    def uno(r):
        if conto["fermato"]:
            return None
        msgs, i = filo_della_risposta(r, fili.get(r["filo_id"]))
        for tentativo in range(2):
            try:
                l = L.leggi_filo(msgs, i, chiedi)
                break
            except L.Guasto as e:
                if conto["fermato"] or tentativo == 1:
                    with lucchetto:
                        conto["errori"] += 0 if conto["fermato"] else 1
                    if not conto["fermato"]:
                        print(f"  ! {r['id']}: {e}", flush=True)
                    return None
                time.sleep(5)
        liste = sync_v2.classifica(sync_v2.testo_suo(msgs[i]["testo"]))
        return {"id": r["id"], "codice": r["etichetta"]["codice"], "caso_a3": r["etichetta"]["caso"], "l": l, "liste": liste}

    inizio = time.time()
    with ThreadPoolExecutor(paralleli) as ex:
        for k, x in enumerate(ex.map(uno, risposte)):
            if x:
                esiti.append(x)
            if (k + 1) % 100 == 0:
                print(f"  {k + 1}/{len(risposte)} · spesi {conto['spesi']:.3f} $", flush=True)
                json.dump(cache, open(percorso_cache, "w", encoding="utf-8"))
    json.dump(cache, open(percorso_cache, "w", encoding="utf-8"))
    stampa(esiti, modello, conto, time.time() - inizio, len(risposte))


class Mancante(Exception):
    pass


def chiave_di(modello, ruolo, istruzioni, testo, schema):
    return hashlib.sha256(json.dumps([modello, ruolo, istruzioni, testo, schema], ensure_ascii=False).encode()).hexdigest()[:32]


def _api(metodo, percorso, corpo=None):
    import urllib.request
    req = urllib.request.Request("https://api.anthropic.com/v1" + percorso, method=metodo,
                                 data=json.dumps(corpo).encode() if corpo is not None else None)
    req.add_header("x-api-key", L._env("ANTHROPIC_API_KEY"))
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def a_lotti(risposte, fili, modello, cache, percorso_cache, tetto, conto):
    """Il rigioco a meta' prezzo: le domande che mancano nella cache vanno all'API dei lotti (Message
    Batches, -50%), si aspetta, e si rifa' il giro (le seconde letture nascono dalle prime)."""
    a_chiamata = 0.0065                       # la stima di partenza; dopo il primo lotto, quella misurata
    dimensione = int(arg("--lotto", "200"))
    for giro in range(40):
        mancanti = {}

        def chiedi(ruolo, istruzioni, testo, schema):
            k = chiave_di(modello, ruolo, istruzioni, testo, schema)
            if k in cache:
                return cache[k]["uscita"], 0.0
            mancanti[k] = (ruolo, istruzioni, testo, schema)
            raise Mancante()
        for r in risposte:
            msgs, i = filo_della_risposta(r, fili.get(r["filo_id"]))
            try:
                L.leggi_filo(msgs, i, chiedi)
            except Mancante:
                pass
        if not mancanti:
            return
        mancanti = dict(list(mancanti.items())[:dimensione])
        stima = len(mancanti) * a_chiamata
        print(f"lotto {giro + 1}: {len(mancanti)} domande, stima {stima:.2f} $ (spesi finora {conto['spesi']:.3f} $)", flush=True)
        if conto["spesi"] + stima > tetto:
            print("  oltre il tetto: mi fermo", flush=True)
            conto["fermato"] = True
            return
        spesi_prima = conto["spesi"]
        richieste = [{"custom_id": k, "params": L.corpo_richiesta(*v, modello)} for k, v in mancanti.items()]
        lotto = json.loads(_api("POST", "/messages/batches", {"requests": richieste}))
        print(f"  lotto {lotto['id']} mandato", flush=True)
        while True:
            time.sleep(30)
            stato = json.loads(_api("GET", f"/messages/batches/{lotto['id']}"))
            if stato.get("processing_status") == "ended":
                break
            print(f"  ... {stato.get('request_counts')}", flush=True)
        import urllib.request
        req = urllib.request.Request(stato["results_url"])
        req.add_header("x-api-key", L._env("ANTHROPIC_API_KEY"))
        req.add_header("anthropic-version", "2023-06-01")
        righe = urllib.request.urlopen(req, timeout=300).read().decode("utf-8").splitlines()
        buoni = cattivi = 0
        for riga in righe:
            x = json.loads(riga)
            k = x["custom_id"]
            res = x.get("result") or {}
            if res.get("type") != "succeeded":
                cattivi += 1
                continue
            d = res["message"]
            u = d.get("usage") or {}
            nuovi, letti, scritti = int(u.get("input_tokens") or 0), int(u.get("cache_read_input_tokens") or 0), int(u.get("cache_creation_input_tokens") or 0)
            fuori = int(u.get("output_tokens") or 0)
            c = L.costo(modello, nuovi, letti, scritti, fuori) * 0.5
            L._registra("lettore-rigioco", modello, nuovi, letti, scritti, fuori, sconto=0.5)
            conto["spesi"] += c
            conto["nuove"] += 1
            try:
                cache[k] = {"uscita": L.uscita_del_messaggio(d, mancanti[k][3]), "costo": c}
                buoni += 1
            except L.Guasto:
                cattivi += 1
        json.dump(cache, open(percorso_cache, "w", encoding="utf-8"))
        if buoni:
            a_chiamata = max(a_chiamata, (conto["spesi"] - spesi_prima) / max(1, buoni + cattivi))
        print(f"  lotto finito: {buoni} letture, {cattivi} non riuscite · spesi {conto['spesi']:.3f} $", flush=True)


def attese(caso, analisi=False):
    return {L.classe_del_caso(caso, False, analisi), L.classe_del_caso(caso, True, analisi)} if caso else {"da_classificare"}


def stampa(esiti, modello, conto, secondi, totale):
    n = len(esiti)
    pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "-"    # noqa: E731
    si = [e for e in esiti if e["caso_a3"] in SI]
    no = [e for e in esiti if e["caso_a3"] in NO]
    ns = [e for e in esiti if e["caso_a3"] == "C30"]
    caldi = [e for e in esiti if e["codice"] in CALDI]
    auto = [e for e in esiti if e["caso_a3"] in AUTOMATICI_A3 and e["codice"] != "OOO_UMANO"]
    si_persi = [e for e in si if e["l"]["classe"] in ("negativo", "automatico", "ooo")]
    no_si = [e for e in no if e["l"]["classe"] in ("positivo", "rinvio", "ooo")]
    ns_mancati = [e for e in ns if not e["l"]["non_scrivere"]]
    caldi_mancati = [e for e in caldi if not e["l"]["caldo"]]
    caldi_in_piu = [e for e in esiti if e["l"]["caldo"] and e["codice"] not in CALDI]
    auto_ok = [e for e in auto if e["l"]["classe"] in ("ooo", "automatico") or e["l"].get("autore") != "persona"]
    giusta = [e for e in esiti if e["l"]["classe"] in attese(e["caso_a3"], e["l"].get("analisi_mandata")) or (e["codice"] in CALDI and e["l"]["classe"] == "positivo")]
    a_dre = [e for e in esiti if e["l"]["classe"] == "da_classificare"]
    caso_giusto = [e for e in esiti if e["l"].get("caso") == e["caso_a3"]]
    print(f"\nRIGIOCO · {modello} · {n}/{totale} risposte in {secondi:.0f} s{' · FERMATO AL TETTO' if conto['fermato'] else ''}"
          f" · chiamate nuove {conto['nuove']}, dalla cache {conto['cache']}, errori {conto['errori']} · spesi in questo giro {conto['spesi']:.3f} $")
    spesa_tot = sum(e["l"].get("costo") or 0 for e in esiti)
    print(f"costo delle letture (anche quelle dalla cache, al primo giro): vedi cache; questo giro {conto['spesi']:.3f} $"
          + (f", {conto['spesi'] / max(1, conto['nuove']):.4f} $ a chiamata" if conto["nuove"] else "") + (f" [{spesa_tot:.3f}]" if spesa_tot else ""))
    print("LE SOGLIE DI PROTEZIONE")
    print(f"  si' persi           {len(si_persi)} su {len(si)}")
    print(f"  no letti come si'   {len(no_si)} su {len(no)}")
    print(f"  non scrivetemi mancati {len(ns_mancati)} su {len(ns)}")
    print(f"  caldi trovati       {len(caldi) - len(caldi_mancati)} su {len(caldi)}  (caldi in piu' {len(caldi_in_piu)})")
    ok = not si_persi and not no_si and not ns_mancati and not caldi_mancati
    print(f"  => {'TENGONO' if ok else 'NON TENGONO'}")
    print("LA PRECISIONE")
    print(f"  classe giusta {len(giusta)} ({pct(len(giusta), n)}) · giusta o a Dre {len(giusta) + len([e for e in a_dre if e not in giusta])}"
          f" ({pct(len(giusta) + len([e for e in a_dre if e not in giusta]), n)}) · a Dre {len(a_dre)} ({pct(len(a_dre), n)})"
          f" · caso giusto {len(caso_giusto)} ({pct(len(caso_giusto), n)}) · automatici {len(auto_ok)}/{len(auto)}")
    for c in ("positivo", "negativo", "rinvio", "ooo", "automatico"):
        decisi = [e for e in esiti if e["l"]["classe"] == c]
        buoni = [e for e in decisi if c in attese(e["caso_a3"], e["l"].get("analisi_mandata")) or (c == "positivo" and e["codice"] in CALDI)]
        print(f"  {c:11} decisi {len(decisi):4}, giusti {len(buoni):4} ({pct(len(buoni), len(decisi))})")
    print("LE LISTE DI PAROLE sulle stesse risposte")
    l_si = [e for e in si if e["liste"] in ("negativo", "ooo")]
    l_no = [e for e in no if e["liste"] in ("positivo", "rinvio", "ooo")]
    l_giusta = [e for e in esiti if e["liste"] in attese(e["caso_a3"], e["l"].get("analisi_mandata"))]
    l_dre = [e for e in esiti if e["liste"] == "da_classificare"]
    print(f"  si' persi {len(l_si)} su {len(si)} · no letti come si' {len(l_no)} su {len(no)} · classe giusta {len(l_giusta)} ({pct(len(l_giusta), n)})"
          f" · da classificare {len(l_dre)} ({pct(len(l_dre), n)})")
    for c in ("positivo", "negativo", "rinvio", "ooo"):
        decisi = [e for e in esiti if e["liste"] == c]
        buoni = [e for e in decisi if c in attese(e["caso_a3"], e["l"].get("analisi_mandata"))]
        print(f"  {c:11} decisi {len(decisi):4}, giusti {len(buoni):4} ({pct(len(buoni), len(decisi))})")
    if "--errori" in sys.argv:
        for nome, gruppo in (("SI' PERSO", si_persi), ("NO COME SI'", no_si), ("NS MANCATO", ns_mancati), ("CALDO MANCATO", caldi_mancati)):
            for e in gruppo:
                print(f"  {nome}: {e['id']} A3 {e['caso_a3']}/{e['codice']} -> {e['l']['classe']} [{e['l'].get('caso')}, {e['l'].get('sicurezza')}] {e['l']['motivo'][:220]}")


if __name__ == "__main__":
    main()
