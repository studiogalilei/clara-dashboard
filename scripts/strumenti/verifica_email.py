#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VERIFICA LE EMAIL DELLE CAMPAGNE (Dre, 23/9/2026: «passiamo da un verificatore,
quelli validi continuiamo le campagne, per le altre usiamo un tool affidabile»).

Bounce del 2,2% nelle prime ore: indirizzi indovinati mai verificati.
Tre passi, ognuno lanciabile da solo:

  verifica_email.py --esporta          scarica i lead vivi delle 6 campagne → data/campagne_lead.csv
  verifica_email.py --verifica         li manda a MillionVerifier e aspetta il risultato → data/campagne_verifica.csv
  verifica_email.py --verifica --riprendi <file_id>   se il file e' gia' caricato
  verifica_email.py --applica          toglie dalle campagne le email non valide, salva le aziende da rifare (finder)

Non riattiva le campagne: lo Start e' di Dre.
Chiave in ~/.hermes/config.yaml come MILLIONVERIFIER_KEY.
"""
import csv, io, json, os, re, sys, time, urllib.request, urllib.error, collections

# 24/9: i domini catch-all dicono si' a qualunque nome, il verificatore non puo' sapere se la
# casella esiste. Dati veri del 23-24/9: catch-all generiche 1,2% di bounce, catch-all con nome
# e cognome 10%, «ok» 0 su 566. Quindi: catch-all si tiene SOLO se generica.
GENERICA = re.compile(r"^(info|contatti|contact|amministrazione|commerciale|vendite|segreteria|ufficio|mail|posta|direzione|hello|sales|marketing|ordini|preventivi|reception|booking|prenotazioni|agenzia|studio|ufficiotecnico|assistenza|servizioclienti|customer|support)@")

BASE = "https://server.smartlead.ai/api/v1"
MV = "https://bulkapi.millionverifier.com/bulkapi/v2"
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CAMP = [4003942, 4003943, 4003944, 4003946, 4003947, 4003948]
ESPORTO, VERIFICA, DA_RIFARE = (os.path.join(D, f) for f in ("campagne_lead.csv", "campagne_verifica.csv", "campagne_da_rifare.csv"))


def chiave(nome):
    for riga in open(os.path.expanduser("~/.hermes/config.yaml"), encoding="utf-8"):
        m = re.match(rf"\s*{nome}:\s*(\S+)", riga)
        if m:
            return m.group(1).strip("\"'")
    sys.exit(f"manca {nome} in ~/.hermes/config.yaml")


def sl(metodo, p, corpo=None):
    k = chiave("SMARTLEAD_API_KEY")
    req = urllib.request.Request(f"{BASE}{p}{'&' if '?' in p else '?'}api_key={k}", method=metodo,
                                 data=json.dumps(corpo).encode() if corpo is not None else None,
                                 headers={"User-Agent": "clara/1.0", "Content-Type": "application/json"})
    for t in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
                try:
                    return json.loads(raw or b"null")
                except Exception:
                    return raw.decode(errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (401, 429, 500, 502, 503, 504) and t < 5:
                time.sleep(4 * (t + 1)); continue
            raise RuntimeError(f"{e.code} {metodo} {p}: {e.read()[:150]}")
        except Exception:
            if t < 5:
                time.sleep(4 * (t + 1)); continue
            raise


def esporta():
    os.makedirs(D, exist_ok=True)
    righe = []
    for cid in CAMP:
        off, n = 0, None
        while True:
            r = sl("GET", f"/campaigns/{cid}/leads?offset={off}&limit=100")
            n = int(r.get("total_leads") or 0)
            for x in r.get("data") or []:
                l = x.get("lead") or {}
                righe.append({"campagna": cid, "lead_id": l.get("id"), "email": (l.get("email") or "").lower(),
                              "first_name": l.get("first_name") or "", "website": l.get("website") or "",
                              "azienda": (l.get("custom_fields") or {}).get("azienda", ""),
                              "gia_contattato": "si" if x.get("last_email_sequence_sent") else ""})
            off += 100
            if off >= n or not r.get("data"):
                break
            time.sleep(0.3)
        print(f"  {cid}: {n} lead", flush=True)
    with open(ESPORTO, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(righe[0])); w.writeheader(); w.writerows(righe)
    print(f"esportati {len(righe)} lead → {ESPORTO}")


def mv_get(url, timeout=60):
    # senza User-Agent il loro Cloudflare risponde 403 (visto il 23/9)
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "clara/1.0"}), timeout=timeout)


def verifica(fid=None):
    k = chiave("MILLIONVERIFIER_KEY")
    if fid:
        return attendi(k, fid)
    email = sorted({r["email"] for r in csv.DictReader(open(ESPORTO, encoding="utf-8")) if r["email"]})
    print(f"mando {len(email)} email a MillionVerifier")
    corpo = "\r\n".join(email).encode()
    bordo = "----clara"
    dati = (f"--{bordo}\r\nContent-Disposition: form-data; name=\"file_contents\"; filename=\"campagne.txt\"\r\n"
            f"Content-Type: text/plain\r\n\r\n").encode() + corpo + f"\r\n--{bordo}--\r\n".encode()
    req = urllib.request.Request(f"{MV}/upload?key={k}&remove_duplicates=1", data=dati, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={bordo}", "User-Agent": "clara/1.0"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    if r.get("error"):
        sys.exit(f"MillionVerifier: {r}")
    fid = r["file_id"]; print("file", fid, "in coda")
    attendi(k, fid)


def attendi(k, fid):
    while True:
        s = json.load(mv_get(f"{MV}/fileinfo?key={k}&file_id={fid}"))
        print(f"  {s.get('status')} {s.get('percent')}%", flush=True)
        if s.get("status") == "finished":
            break
        time.sleep(30)
    csvt = mv_get(f"{MV}/download?key={k}&file_id={fid}&filter=all", 300).read().decode("utf-8", "replace")
    open(VERIFICA, "w", encoding="utf-8").write(csvt)
    esiti = collections.Counter(r.get("result") or r.get("quality") for r in csv.DictReader(io.StringIO(csvt)))
    print("esito:", dict(esiti), "→", VERIFICA)


def applica(prova=False):
    lead = list(csv.DictReader(open(ESPORTO, encoding="utf-8")))
    ver = {}
    for r in csv.DictReader(open(VERIFICA, encoding="utf-8")):
        e = (r.get("email") or r.get("Email") or "").lower()
        ver[e] = (r.get("result") or r.get("quality") or "").lower()
    # ok e catch_all restano; invalid, disposable, unknown escono (unknown = il server non risponde: a bounce si va lo stesso)
    via = [l for l in lead if ver.get(l["email"], "") in ("invalid", "disposable", "unknown", "error")
           or (ver.get(l["email"], "") == "catch_all" and not GENERICA.match(l["email"]))]
    print(f"da togliere {len(via)} su {len(lead)}:", dict(collections.Counter(ver.get(l['email']) for l in via)))
    with open(DA_RIFARE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lead[0]) + ["esito"]); w.writeheader()
        for l in via:
            w.writerow({**l, "esito": ver.get(l["email"])})
    print(f"aziende da rifare col finder → {DA_RIFARE}")
    if prova:
        return
    # IL POLIZIOTTO (24/9): regole dure, seconda testa, ok di Dre sopra soglia
    from polizia import controlla
    via = controlla("cancello lead dalle campagne Smartlead (email invalide/sconosciute/catch-all nominative)", via,
                    chiave=lambda l: l["email"], irreversibile=True, motivo="il verificatore le ha bocciate: rimbalzano")
    n = 0
    for l in via:
        # 24/9: MAI cancellare chi ha risposto. Cancellare il lead cancella il thread
        # dalla Master Inbox di Smartlead (successo con 5 rispondenti su 6, 24/9).
        try:
            dati = sl("GET", f"/leads/?email={l['email']}")
            if any(c.get("last_reply_at") for c in (dati.get("lead_campaign_data") or []) if isinstance(dati, dict)):
                print(f"  tengo {l['email']}: ha risposto"); continue
        except Exception:
            pass
        r = sl("DELETE", f"/campaigns/{l['campagna']}/leads/{l['lead_id']}")
        n += r == "success"; time.sleep(0.2)
    print(f"tolti {n}/{len(via)}. Le campagne restano in pausa: lo Start e' di Dre.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--esporta" in a: esporta()
    elif "--verifica" in a: verifica(a[a.index("--riprendi") + 1] if "--riprendi" in a else None)
    elif "--applica" in a: applica("--prova" in a)
    else: print(__doc__)
