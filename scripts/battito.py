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
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, di_clara                  # noqa: E402

PROVA = "--prova" in sys.argv
ADESSO = datetime.datetime.now(datetime.timezone.utc)
ROMA = zoneinfo.ZoneInfo("Europe/Rome")          # 6/10: non +2 fisso (ora solare dal 25/10)
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


SEGUITI = ("FOLLOW UP 1", "MINI FOLLOW UP", "RINVIO SCADUTO", "RICONTATTO OOO", "RIPRESA", "FOLLOW UP SU MISURA")


def _perche_non_parte(pr, pid):
    """Il primo motivo per cui la prima risposta automatica non la prende: lo stesso cancello, letto senza scrivere."""
    try:
        import prima_risposta as PR
        p = (sb("GET", f"/rest/v1/prospects?select={PR.CAMPI}&id=eq.{pid}") or [None])[0]
        no = [m for m in PR.perche_no(pr, p) if m != "gia' passata di qui"]
        return no[0] if no else ""
    except Exception as e:                                   # noqa: BLE001
        return f"cancello non letto ({str(e)[:40]})"


def giornata(oggi):
    """LA GIORNATA NON E' FINITA (Dre, 5/10: «finche' tutti quelli che hanno detto si' non hanno
    ricevuto l'analisi, e tutti quelli che devono avere un follow-up non l'hanno ricevuto»).
    Due liste che devono essere vuote. Una bozza in Posta non e' un follow-up partito: conta
    come dovuto. Il workflow sta nel vault: «La giornata non e' finita (regola del 5-10-2026)»."""
    si = sb_tutte("/rest/v1/prospects?select=id,company,name,email,coda&fuori=eq.false&analysis_sent=eq.false"
                  "&classificazione=in.(positivo,tiepido)&no_followup=eq.false&stage=not.in.(perso,cliente)&pipeline_stage=is.null") or []
    dovuti = {c["prospect_id"]: "il suo giorno e' passato" for c in
              sb_tutte(f"/rest/v1/seguiti_calendario?select=prospect_id&il=lte.{oggi}", chiave="prospect_id") or []}
    for x in sb_tutte("/rest/v1/proposte?select=prospect_id,stato,azione&stato=in.(aperta,approvata,in_invio)&tipo=eq.risposta") or []:
        if x.get("prospect_id") and (x.get("azione") or {}).get("template") in SEGUITI:
            dovuti[x["prospect_id"]] = "bozza in Posta, aspetta te" if x["stato"] == "aperta" else f"bozza {x['stato']}, in partenza"
    if not si and not dovuti:
        return ["GIORNATA CHIUSA: tutti i sì hanno l'analisi, tutti i follow-up sono partiti."]
    out = [f"GIORNATA APERTA: {len(si)} sì senza analisi, {len(dovuti)} follow-up non partiti."]
    in_posta = sum(1 for m in dovuti.values() if m.startswith("bozza in Posta"))
    if in_posta:
        out.append(f"  {in_posta} follow-up sono bozze in Posta: si chiudono con Approva e manda.")
    for p in si[:3]:
        out.append(f"  sì senza analisi: {(p.get('company') or p.get('name') or p['email'])[:26]}" + (" (in coda)" if p.get("coda") else ""))
    return out


def main():
    oggi = datetime.date.today().isoformat()
    mandate = sb("GET", f"/rest/v1/proposte?select=titolo&stato=eq.fatta&tipo=eq.risposta&risposta_il=gte.{oggi}T00:00:00") or []
    # con l'invio spento (28/9) ogni bozza aperta aspetta Dre: dire «non passata dai controlli»
    # faceva pensare a un guasto dove c'era solo una bozza da approvare (6/10)
    invio = (sb("GET", "/rest/v1/operazioni?select=attiva&chiave=eq.manda") or [{}])[0].get("attiva")

    att = sb_tutte("/rest/v1/prospects?select=id,company,name,email,last_reply_at,classificazione&awaiting_us=eq.true&fuori=eq.false")
    vivi = [p for p in att if (p.get("classificazione") or "") not in MORTI]
    prop = {}
    for x in sb_tutte("/rest/v1/proposte?select=id,tipo,titolo,prospect_id,stato,azione&stato=in.(aperta,approvata,in_invio)"):
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
                motivo = "bozza in Posta, aspetta te"
                if invio:
                    # il motivo vero per cui non parte da sola (6/10): prima diceva «non ancora
                    # passata dai controlli» anche quando il cancello l'aveva fermata da giorni
                    perche = _perche_non_parte(pr, p["id"])
                    if perche:
                        motivo += f" (non parte da sola: {perche})"
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

    r.extend(giornata(oggi))
    testo = "\n".join(r)
    print(testo)
    if not PROVA:
        di_clara("battito", testo, letto=False)


if __name__ == "__main__":
    main()
