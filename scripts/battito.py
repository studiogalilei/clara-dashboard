#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL BATTITO DELL'OUTBOUND (Dre, 2/10/2026; rifatto il 5/10 dopo il caso Contarini).

Parole sue: «Smartlead non lo uso piu': voglio che Clara mi scriva nel pannello,
stile WhatsApp, come stanno andando le cose». E il 5/10: «quando dici di aver
controllato, controlla sul serio, dal posto di chi usa, non con finta sicurezza».

La lezione di Contarini: una bozza FERMA non e' una risposta. Il vecchio battito
contava gli stati interni («ha una bozza → coperto») e chiamava sano un lead che
aspettava da 2 giorni dietro un freno sbagliato. Questo battito conta dal posto
del lead: per ognuno che aspetta, QUANTE ORE aspetta e cosa lo tiene fermo, e
nomina chiunque sia oltre soglia, bozza o non bozza. Niente «tutto ok» sommari.

USO:  python3 scripts/battito.py [--prova]
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, di_clara                  # noqa: E402

PROVA = "--prova" in sys.argv
ADESSO = datetime.datetime.now(datetime.timezone.utc)
ROMA = datetime.timezone(datetime.timedelta(hours=2))
MORTI = ("fuori_target", "soppresso", "nervoso")
AUTO = ("INT-01", "INT-02", "INT-03", "INT-23", "INT-GB")
# oltre queste ore di attesa, il lead si nomina col motivo (i no e gli ooo hanno piu' margine)
SOGLIA_ORE = 4
SOGLIA_ORE_NO = 48


def _dt(iso):
    if not iso:
        return None
    iso = re.sub(r"\.(\d{6})\d+", r".\1", str(iso).replace("Z", "+00:00"))
    try:
        t = datetime.datetime.fromisoformat(iso)
        return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def _ore(iso):
    t = _dt(iso)
    return round((ADESSO - t).total_seconds() / 3600, 1) if t else None


def main():
    oggi = datetime.date.today().isoformat()
    mandate = sb("GET", f"/rest/v1/proposte?select=titolo&stato=eq.fatta&tipo=eq.risposta&risposta_il=gte.{oggi}T00:00:00") or []

    att = sb_tutte("/rest/v1/prospects?select=id,company,name,email,last_reply_at,classificazione&awaiting_us=eq.true&fuori=eq.false")
    vivi = [p for p in att if (p.get("classificazione") or "") not in MORTI]
    prop = {}
    for x in sb_tutte("/rest/v1/proposte?select=prospect_id,stato,azione&stato=in.(aperta,approvata,in_invio)"):
        if x.get("prospect_id") and x["prospect_id"] not in prop:
            prop[x["prospect_id"]] = x

    # dal posto del lead: ognuno con le sue ore di attesa e cosa lo tiene fermo
    fermi = []           # (ore, nome, motivo) per chi e' oltre soglia
    eta_max = 0.0
    for p in vivi:
        ore = _ore(p.get("last_reply_at")) or 0
        eta_max = max(eta_max, ore)
        cls = p.get("classificazione") or ""
        soglia = SOGLIA_ORE_NO if cls in ("negativo", "ooo") else SOGLIA_ORE
        if ore <= soglia:
            continue
        pr = prop.get(p["id"])
        if cls == "ooo":
            continue                                        # aspettano il rientro: fermo giusto
        nome = (p.get("company") or p.get("name") or p["email"])[:26]
        if not pr:
            motivo = "nessuna bozza" if cls != "negativo" else "gigante buono non ancora scritto"
        else:
            esito = ((pr.get("azione") or {}).get("prima_risposta") or {})
            if esito.get("esito") == "resta a Dre":
                motivo = "fermo in Posta, aspetta TE: " + (esito.get("motivo") or "")[:60]
            elif pr["stato"] == "aperta":
                motivo = "bozza pronta, non ancora passata dai controlli"
            else:
                motivo = f"bozza {pr['stato']}"
        fermi.append((ore, nome, motivo))
    fermi.sort(reverse=True)

    r = [f"Outbound, {ADESSO.astimezone(ROMA):%d/%m %H:%M}."]
    r.append(f"Oggi {len(mandate)} {'consegna' if len(mandate) == 1 else 'consegne'} partite.")
    r.append(f"Aspettano una risposta: {len(vivi)}. Il piu' vecchio da {eta_max:.0f} ore.")
    if fermi:
        r.append(f"FERMI OLTRE SOGLIA: {len(fermi)}.")
        for ore, nome, motivo in fermi[:5]:
            r.append(f"  {nome}, {ore:.0f}h: {motivo}")
        if len(fermi) > 5:
            r.append(f"  e altri {len(fermi) - 5}: li vedi nel polso, nei Numeri")
    else:
        r.append("Nessuno oltre soglia (4 ore i vivi, 48 i no gentili). Gli OOO aspettano il rientro.")

    testo = "\n".join(r)
    print(testo)
    if not PROVA:
        di_clara("battito", testo, letto=False)


if __name__ == "__main__":
    main()
