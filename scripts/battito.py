#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL BATTITO DELL'OUTBOUND (Dre, 2/10/2026).

Parole sue: «Smartlead non lo uso piu'. Nel pannello laterale del Workspace voglio
una chat stile WhatsApp dove Clara mi manda messaggi di questo tipo: oggi N
consegne, N in attesa, il problema vero. Devo poter controllare e dire: ok, sta
andando tutto bene, oppure no. Un sistema per vedere il tutto».

Questo scrive UN messaggio «battito» nella chat di Clara (clara_messaggi), in
italiano, a colpo d'occhio: cosa e' partito oggi, chi aspetta e diviso come, se
la promessa dei tempi tiene, e il problema vero se c'e'. Niente numeri inventati:
conta quello che c'e' nel database. Gira la mattina e il pomeriggio dal direttore.

USO:  python3 scripts/battito.py [--prova]
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, di_clara                  # noqa: E402

PROVA = "--prova" in sys.argv
ADESSO = datetime.datetime.now(datetime.timezone.utc)
MORTI = ("fuori_target", "soppresso", "nervoso")
AUTO = ("INT-01", "INT-02", "INT-03", "INT-23", "INT-GB")


def _ore(iso):
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return (ADESSO - (t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc))).total_seconds() / 3600
    except Exception:                                       # noqa: BLE001
        return None


def main():
    oggi = datetime.date.today().isoformat()
    mandate = sb("GET", f"/rest/v1/proposte?select=titolo&stato=eq.fatta&tipo=eq.risposta&risposta_il=gte.{oggi}T00:00:00") or []

    att = sb_tutte("/rest/v1/prospects?select=id,company,name,email,last_reply_at,classificazione&awaiting_us=eq.true&fuori=eq.false")
    vivi = [p for p in att if (p.get("classificazione") or "") not in MORTI]
    prop = {}
    for x in sb_tutte("/rest/v1/proposte?select=prospect_id,azione&stato=in.(aperta,approvata,in_invio)"):
        if x.get("prospect_id"):
            prop[x["prospect_id"]] = (x.get("azione") or {}).get("intento") or "?"

    neg = ooo = corsia = tua = senza = 0
    tardi = []
    in_finestra = ADESSO.astimezone(datetime.timezone(datetime.timedelta(hours=2)))
    finestra = in_finestra.weekday() < 5 and 9 <= in_finestra.hour < 17
    for p in vivi:
        cls = p.get("classificazione") or ""
        if cls == "negativo":
            neg += 1
        elif cls == "ooo":
            ooo += 1
        inten = prop.get(p["id"])
        if inten in AUTO:
            corsia += 1
            if finestra and (_ore(p.get("last_reply_at")) or 0) > 1 and cls not in ("negativo", "ooo"):
                tardi.append(p.get("company") or p.get("name") or p["email"])
        elif inten:
            tua += 1
        else:
            senza += 1

    # il problema vero: chi aspetta, non e' un morto, non e' OOO, e non ha nemmeno una bozza
    orfani = [p for p in vivi if p["id"] not in prop
              and (p.get("classificazione") or "") not in ("negativo", "ooo")]

    r = [f"Outbound, {ADESSO.astimezone(datetime.timezone(datetime.timedelta(hours=2))):%d/%m %H:%M}."]
    r.append(f"Oggi {len(mandate)} {'consegna' if len(mandate) == 1 else 'consegne'} partite.")
    r.append(f"In attesa adesso: {len(vivi)}. {corsia} in corsia automatica, {tua} da te, {neg} no (gigante buono), {ooo} fuori ufficio.")
    if tardi:
        r.append(f"ATTENZIONE: {len(tardi)} in corsia oltre l'ora ({', '.join(tardi[:3])}): guarda il polso nei Numeri.")
    elif finestra:
        r.append("La promessa dei tempi tiene: niente oltre l'ora.")
    if orfani:
        nomi = ", ".join((p.get("company") or p.get("name") or p["email"])[:24] for p in orfani[:3])
        r.append(f"Da sistemare: {len(orfani)} aspettano senza una bozza ({nomi}).")
    else:
        r.append("Tutti quelli che aspettano hanno la loro risposta in lavorazione.")

    testo = "\n".join(r)
    print(testo)
    if not PROVA:
        di_clara("battito", testo, letto=False)


if __name__ == "__main__":
    main()
