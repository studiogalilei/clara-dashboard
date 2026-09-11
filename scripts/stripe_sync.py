#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLI INCASSI DA STRIPE (10/9/2026).

Dre: «dopo connettiamo Stripe». Clara legge Stripe con una chiave di sola
lettura (rk_live_..., permessi «Reportistica, analisi e contabilita'») e
mette nella tabella `incassi` addebiti, fatture pagate e abbonamenti.

Per ogni incasso prova a capire di che azienda e': la mail del cliente Stripe
contro prospects.email, poi il dominio (se non e' gmail e simili), poi il
nome. Se un addebito riuscito combacia con un preventivo accettato e non
pagato della stessa azienda (stesso importo, ±1 €), lo segna pagato da sola
e scrive «Stripe» nelle note. Se l'azienda c'e' ma il preventivo non torna,
lo chiede nella stanza (tipo richiesta). Non tocca mai Stripe.

USO
  python3 scripts/stripe_sync.py            legge e scrive
  python3 scripts/stripe_sync.py --prova    mostra e non scrive
"""

import base64
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env, proponi                        # noqa: E402

STRIPE = "https://api.stripe.com/v1"
GRATIS = {"gmail.com", "yahoo.com", "yahoo.it", "hotmail.com", "hotmail.it", "outlook.com", "outlook.it",
          "live.com", "live.it", "icloud.com", "libero.it", "virgilio.it", "tiscali.it", "alice.it", "pec.it"}


def stripe(via, **q):
    k = env("STRIPE_SECRET_KEY")
    if not k:
        sys.exit("ERRORE: manca STRIPE_SECRET_KEY")
    fuori, dopo = [], None
    while True:
        p = {"limit": 100, **q}
        if dopo:
            p["starting_after"] = dopo
        url = f"{STRIPE}/{via}?" + urllib.parse.urlencode(p)
        req = urllib.request.Request(url, headers={"Authorization": "Basic " + base64.b64encode(f"{k}:".encode()).decode()})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        fuori += d.get("data", [])
        if not d.get("has_more") or not fuori:
            return fuori
        dopo = fuori[-1]["id"]


def quando(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat() if ts else None


# ── da Stripe alle righe di `incassi` ────────────────────────────────
def righe_stripe():
    clienti = {c["id"]: c for c in stripe("customers")}

    def chi(cus_id, fallback=None):
        c = clienti.get(cus_id) or {}
        f = fallback or {}
        return (c.get("name") or f.get("name"), (c.get("email") or f.get("email") or "").lower() or None, cus_id)

    righe = []
    for ch in stripe("charges"):
        nome, mail, cus = chi(ch.get("customer"), ch.get("billing_details"))
        righe.append({"id": ch["id"], "genere": "addebito", "importo": ch["amount"] / 100, "valuta": ch["currency"],
                      "stato": ch["status"], "quando": quando(ch["created"]), "ricorrenza": None,
                      "cliente_nome": nome, "cliente_email": mail or (ch.get("receipt_email") or "").lower() or None,
                      "stripe_cliente": cus, "descrizione": (ch.get("description") or "")[:200] or None,
                      "metodo": {"sepa_debit": "sepa", "card": "carta", "customer_balance": "bonifico"}.get(((ch.get("payment_method_details") or {}).get("type")) or "", None)})
    for inv in stripe("invoices"):
        if inv.get("status") not in ("paid", "open"):
            continue
        nome, mail, cus = chi(inv.get("customer"), {"name": inv.get("customer_name"), "email": inv.get("customer_email")})
        linee = inv.get("lines", {}).get("data", [])
        righe.append({"id": inv["id"], "genere": "fattura", "importo": (inv.get("amount_paid") or inv.get("amount_due") or 0) / 100,
                      "valuta": inv["currency"], "stato": inv["status"], "quando": quando(inv.get("status_transitions", {}).get("paid_at") or inv["created"]),
                      "ricorrenza": None, "cliente_nome": nome, "cliente_email": mail, "stripe_cliente": cus,
                      "descrizione": (linee[0].get("description") if linee else "")[:200] or None})
    for s in stripe("subscriptions", status="all", **{"expand[]": "data.default_payment_method"}):
        nome, mail, cus = chi(s.get("customer"))
        voci = s.get("items", {}).get("data", [])
        prezzo = (voci[0].get("price") or {}) if voci else {}
        pm = s.get("default_payment_method")
        tipo_pm = pm.get("type") if isinstance(pm, dict) else None
        metodo = {"sepa_debit": "sepa", "card": "carta", "customer_balance": "bonifico"}.get(tipo_pm or "", "altro" if tipo_pm else None)
        if s.get("collection_method") == "send_invoice":
            metodo = metodo or "bonifico"
        fine = s.get("cancel_at") or s.get("canceled_at") or s.get("ended_at")
        prossimo = s.get("current_period_end") or (voci[0].get("current_period_end") if voci else None)
        attivo = s["status"] in ("active", "trialing", "past_due", "unpaid")
        righe.append({"id": s["id"], "genere": "abbonamento", "importo": (prezzo.get("unit_amount") or 0) / 100 * (voci[0].get("quantity", 1) if voci else 1),
                      "valuta": prezzo.get("currency") or "eur", "stato": s["status"], "quando": quando(s["created"]),
                      "ricorrenza": (prezzo.get("recurring") or {}).get("interval"), "cliente_nome": nome, "cliente_email": mail,
                      "stripe_cliente": cus, "descrizione": ((prezzo.get("nickname") or prezzo.get("product") or "") if isinstance(prezzo.get("product"), str) else "")[:200] or None,
                      "metodo": metodo, "prossimo_il": quando(prossimo) if attivo else None, "fine_il": quando(fine)})
    return righe


# ── di chi e' ──────────────────────────────────────────────────────
def indice_aziende():
    ps = sb("GET", "/rest/v1/prospects?select=id,email,company,name&limit=50000") or []
    per_mail, per_dominio, per_nome = {}, {}, {}
    for p in ps:
        m = (p.get("email") or "").lower()
        if m:
            per_mail[m] = p["id"]
            d = m.split("@")[-1]
            if d and d not in GRATIS:
                per_dominio.setdefault(d, p["id"])
        for n in (p.get("company"), p.get("name")):
            if n and len(n) > 3:
                per_nome.setdefault(n.strip().lower(), p["id"])
    return per_mail, per_dominio, per_nome


def di_chi(r, idx):
    per_mail, per_dominio, per_nome = idx
    m = r.get("cliente_email") or ""
    if m in per_mail:
        return per_mail[m]
    d = m.split("@")[-1] if "@" in m else ""
    if d and d not in GRATIS and d in per_dominio:
        return per_dominio[d]
    n = (r.get("cliente_nome") or "").strip().lower()
    return per_nome.get(n)


def main():
    prova = "--prova" in sys.argv
    righe = righe_stripe()
    idx = indice_aziende()
    gia = {r["id"]: r for r in (sb("GET", "/rest/v1/incassi?select=id,prospect_id,preventivo_id&limit=50000") or [])}
    nuovi, collegati, pagati, chiesti = 0, 0, 0, 0
    for r in righe:
        vecchio = gia.get(r["id"])
        r["prospect_id"] = (vecchio or {}).get("prospect_id") or di_chi(r, idx)
        r["preventivo_id"] = (vecchio or {}).get("preventivo_id")
        if r["prospect_id"]:
            collegati += 1
        # un incasso vero, di un'azienda nota, senza preventivo collegato: cerco il preventivo
        incassato = (r["genere"] == "addebito" and r["stato"] == "succeeded") or (r["genere"] == "fattura" and r["stato"] == "paid")
        if incassato and r["prospect_id"] and not r["preventivo_id"]:
            # inviati o accettati, non ancora pagati: pagare vale come accettare
            aperti = sb("GET", f"/rest/v1/preventivi?select=id,importo,titolo&prospect_id=eq.{r['prospect_id']}"
                               "&stato=in.(inviato,accettato)&pagato_il=is.null") or []
            con_importo = [q for q in aperti if q.get("importo") is not None]
            giusti = [q for q in con_importo if abs(float(q["importo"]) - r["importo"]) <= 1]
            # un pagamento solo per piu' preventivi (es. sito + prova in un link): la somma torna
            if not giusti and len(con_importo) > 1 and abs(sum(float(q["importo"]) for q in con_importo) - r["importo"]) <= 1:
                giusti = con_importo
            if giusti and (len(giusti) == 1 or len(giusti) == len(con_importo)):
                r["preventivo_id"] = giusti[0]["id"]
                if not prova:
                    for q in giusti:
                        sb("PATCH", f"/rest/v1/preventivi?id=eq.{q['id']}",
                           {"stato": "accettato", "pagato_il": (r["quando"] or "")[:10] or datetime.date.today().isoformat(),
                            "note": f"pagato su Stripe ({r['id']})"})
                pagati += len(giusti)
            elif aperti and not prova:
                if proponi("richiesta", f"Incasso di {r['importo']:.0f} {r['valuta'].upper()} su Stripe: quale preventivo segno pagato?",
                           prospect_id=r["prospect_id"],
                           perche=f"{r.get('cliente_nome') or r.get('cliente_email')}, {r['descrizione'] or r['genere']}. Preventivi aperti: "
                                  + ", ".join(f"{q['titolo'] or 'senza titolo'} {q['importo']:.0f} €" for q in aperti),
                           azione={"incasso_id": r["id"]}):
                    chiesti += 1
        if not vecchio:
            nuovi += 1
        if prova:
            print(f"  {r['genere']:11} {r['stato']:12} {r['importo']:8.2f} {r['valuta']} {str(r.get('cliente_nome'))[:24]:24} "
                  f"{'azienda ok' if r['prospect_id'] else '-':10} {'prev ' + str(r['preventivo_id']) if r['preventivo_id'] else ''}")
    if not prova and righe:
        r0 = datetime.datetime.now(datetime.timezone.utc).isoformat()
        chiavi = {k for r in righe for k in r}          # PostgREST vuole le stesse chiavi su ogni riga
        for r in righe:
            r["letto_il"] = r0
            for k in chiavi:
                r.setdefault(k, None)
        sb("POST", "/rest/v1/incassi", righe, {"Prefer": "resolution=merge-duplicates"})
    print(f"stripe: {len(righe)} righe ({nuovi} nuove), {collegati} con azienda, {pagati} preventivi segnati pagati, {chiesti} domande")


if __name__ == "__main__":
    main()
