#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LO SCORE DELLA GARANZIA (Dre, 1/10/2026).

Parole sue: «quella linea voglio che venga usata in modo intelligente: uno score
fatto bene, se supera certi criteri lo mettiamo, se no no. Se non siamo
sicurissimi di un'azienda non possiamo scrivere subito quella linea, anche
perche' uno se lo ricorda». La frase e' quella del template INT-01: «avremmo
pronta anche una proposta con garanzia da farvi».

Il perche' di ogni criterio sta scritto accanto: un sistema che ragiona, non
uno meccanico. La garanzia e' soddisfatti-o-rimborsati: la promettiamo quando
IL RISCHIO E' BASSO PER NOI, cioe' quando i numeri misurati dicono che il
mercato c'e' e l'azienda regge la spesa. In analisi non si scrive mai: e' un
capitolo della mail, non del documento.

Uso:
    from garanzia import promettibile
    si, motivo, punti = promettibile(p)      # p = riga prospects con enriched
"""


def promettibile(p):
    """(True/False, il motivo in una riga, i punti). Decide se la frase della garanzia entra nella mail."""
    gf = ((p or {}).get("enriched") or {}).get("google_fit") or {}
    zona = gf.get("zona") or {}
    rec = gf.get("recensioni") or {}
    motivi_no, punti = [], 0

    # ── i blocchi secchi: qui non si promette, qualunque sia il resto ──
    if gf.get("verdetto") == "NO":
        return False, f"il fit dice NO ({(gf.get('motivo') or '')[:60]}): promettere un rimborso qui e' regalarlo", 0
    if gf.get("settore_uguale") is False:
        return False, "i volumi misurati non sono del loro settore: non sappiamo abbastanza per garantire", 0
    if not gf:
        return False, "nessun fit letto: di questa azienda non sappiamo niente di misurato", 0

    # ── i punti: ogni numero vero a favore ──
    if gf.get("verdetto") == "SI":
        punti += 2            # il fit pieno: settore, mercato e dimensione in linea
    if (zona.get("verdetto") == "VERDE"):
        punti += 2            # la domanda misurata c'e' davvero dove vendono
    elif zona.get("verdetto") == "GIALLO":
        punti += 1
    else:
        motivi_no.append("domanda non misurata")
    if (rec.get("recensioni") or 0) >= 20:
        punti += 1            # un'azienda vera, con clienti veri: il rischio di sorprese cala
    else:
        motivi_no.append("poche recensioni")
    tmax = gf.get("ticket_max") or 0
    if tmax >= 1000:
        punti += 1            # un cliente vale abbastanza da ripagare fee e campagna
    elif tmax and tmax < 300:
        motivi_no.append(f"ticket basso ({tmax} €): la garanzia rischia di pagarla la nostra fee")
    if zona.get("cpc") and tmax and float(zona["cpc"]) * 33 <= tmax:
        punti += 1            # un cliente costa meno di quanto rende (33 clic al 3%)

    # ── la soglia: 4 punti. Sotto, la frase non si scrive e Dre resta libero ──
    if punti >= 4:
        return True, f"{punti} punti: mercato misurato e azienda che regge la spesa", punti
    return False, f"solo {punti} punti ({'; '.join(motivi_no) or 'numeri deboli'}): meglio non promettere, uno se lo ricorda", punti
