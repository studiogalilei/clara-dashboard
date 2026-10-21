#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RIPULISCI: l'arretrato si chiude, domani si comincia freschi (Dre, 21/10/2026 sera).

Dre: «liberiamo l'app da tutte le bozze e stronzate arretrate: domani cominciamo freschi». E la
regola nuova dello stesso giorno: «quando sistemiamo qualcosa, le leggi sono retroattive: sistema
anche i casi vecchi arretrati se applicabili».

COSA FA (tre gesti, ognuno passa dal Revisore con prova a secco, conteggi e campione)

  --proposte      chiude (stato «no», motivo scritto, MAI una mail) ogni proposta aperta che NON e'
                  una decisione viva di Dre. La regola e' `verdetto()`, pura, provata dalle invarianti:
                  (a) tutto cio' che e' nato prima del 19/10 (il sistema nuovo), tranne le approvate e
                      tranne le domande su una persona che ha riscritto dopo il 19/10;
                  (b) i «Da guardare tu» senza una persona dietro: autorisposte, rimbalzi, caselle di
                      servizio, persona sbagliata (lettore C38-C48), classe ooo/soppresso, un no del
                      lettore ad alta sicurezza senza spiraglio;
                  (c) i tipi del sistema vecchio (avanza, nuovo, richiesta) e le note «Ho imparato
                      dalle tue correzioni» / «Appunti di Gemini» piu' vecchie di 3 giorni;
                  (d) i follow-up aperti da piu' di 7 giorni (il calendario dei follow-up li rifa').
                  Si tengono: le approvate, le domande con le strade, le decisioni recenti su persone vere.
  --da-chiamare   «Da chiamare» solo con un cellulare suo (Dre, 20/10 sera), anche sulle righe
                  vecchie scritte dal sistema: senza cellulare la riga diventa «Da rispondere» con Dre
                  responsabile (segnale_provvisorio.passa_a_dre). Le righe toccate da Dre non si toccano.

USO
  python3 scripts/ripulisci.py --proposte --prova      conteggi e campione, non scrive
  python3 scripts/ripulisci.py --proposte              chiude davvero
  python3 scripts/ripulisci.py --da-chiamare [--prova]
"""
import datetime
import json
import os
import re
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, quando, lettore_di, _a_secco  # noqa: E402

PROVA = _a_secco()
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
NATO = datetime.date(2026, 10, 19)           # il giorno in cui e' nato il sistema nuovo (foglio, confine, conversazioni)
GIORNI_NOTE = 3                              # le note del sistema vecchio («Ho imparato», «Appunti») vivono 3 giorni
GIORNI_SEGUITI = 7                           # un follow-up fermo da piu' di una settimana lo rifa' il calendario
GIORNI_MUTO = 45                             # una persona muta da piu' di 45 giorni non e' una decisione viva (le schede guardano 60)
TIPI_VECCHI = ("avanza", "nuovo", "richiesta")
NOTE_VECCHIE = ("Ho imparato dalle tue", "Appunti di Gemini")
DOMANDE = ("Da guardare tu", "Decidi tu")
SEGUITO = re.compile(r"FOLLOW UP|RIPRESA", re.I)
# il lettore AI: chi ha cambiato indirizzo, non lavora piu' li', persona o azienda sbagliata, fuori
# ufficio, risponditore, rimbalzo (scripts/lettore_regole.json C38-C48): non c'e' nessuno con cui decidere
CASI_NON_PERSONA = {f"C{n}" for n in range(38, 49)}
CLASSI_FERME = ("ooo", "soppresso", "nervoso")
NON_PERSONA = re.compile(r"autorispost|autorespon|auto-?reply|autoresponder|bounce|\bNDR\b|\bDSN\b|mancata consegna|"
                         r"casella di servizio|antispam|helpdesk|ticket|indirizzo non valido|deliverability", re.I)
MOTIVO = "chiusa il 21/10 (ripartenza): "


# ── 1. la regola pura (la provano le invarianti) ───────────────────────────────

def _persona(pr, p):
    """C'e' una persona vera dietro la domanda? (la stessa regola di strade.e_persona, piu' il lettore)"""
    az = (pr or {}).get("azione") or {}
    let = az.get("lettura") or {}
    if let.get("autorisposta") or let.get("casella_di_servizio"):
        return False, "l'ultima mail e' un'autorisposta o una casella di servizio"
    if NON_PERSONA.search((pr or {}).get("perche") or ""):
        return False, "non c'e' una persona (autorisposta, rimbalzo, casella di servizio)"
    if p and p.get("classificazione") in CLASSI_FERME:
        return False, f"il lead e' «{p.get('classificazione')}»"
    l = lettore_di(p) if p else {}
    # una persona vera che ha sbagliato destinatario ma apre una porta (lascia un numero, indica l'ufficio):
    # il lettore lo segna caldo o «porta aperta», e resta una decisione di Dre (L'Officina, 21/10 sera)
    if l.get("caso") in CASI_NON_PERSONA and (l.get("caldo") or l.get("porta_aperta")):
        return True, ""
    if l.get("caso") in CASI_NON_PERSONA:
        return False, f"il lettore ha letto «{l.get('caso')}»: persona sbagliata, assente o risponditore"
    if l.get("classe") == "negativo" and l.get("sicurezza") == "alta" and not l.get("porta_aperta") and not l.get("caldo"):
        return False, "il lettore ha letto un no (sicurezza alta, nessuno spiraglio)"
    return True, ""


def _lead_vivo(p):
    """Un lead a cui si puo' ancora scrivere (la parte pura di stanza.contattabile)."""
    if not p:
        return False
    if p.get("fuori") or p.get("stage") in ("cliente", "perso") or p.get("pipeline_stage") in ("cliente", "perso"):
        return False
    if p.get("no_followup") or p.get("classificazione") in ("soppresso", "nervoso"):
        return False
    return True


def verdetto(pr, p, ora):
    """(tieni, motivo) per una proposta aperta. `p` e' la scheda del lead (o None se la proposta non ne ha)."""
    stato = pr.get("stato")
    if stato in ("approvata", "in_invio"):
        return True, "approvata: parte"
    tipo = pr.get("tipo") or ""
    titolo = pr.get("titolo") or ""
    az = pr.get("azione") or {}
    nata = quando(pr["at"])
    eta = ora - nata
    vecchia = nata.astimezone(ROMA).date() < NATO
    # (c) il sistema vecchio
    if tipo in TIPI_VECCHI or titolo.startswith(NOTE_VECCHIE):
        if eta > datetime.timedelta(days=GIORNI_NOTE):
            return False, f"arretrato del sistema vecchio ({tipo}), piu' di {GIORNI_NOTE} giorni"
        return True, "nota recente del sistema"
    # (d) i follow-up fermi
    if tipo == "risposta" and (SEGUITO.search(titolo) or SEGUITO.search(str(az.get("intento") or "")) or SEGUITO.search(str(az.get("template") or ""))):
        if eta > datetime.timedelta(days=GIORNI_SEGUITI):
            return False, f"follow-up fermo da piu' di {GIORNI_SEGUITI} giorni: se serve lo rifa' il calendario"
        return True, "follow-up recente"
    # la proposta e' su un lead
    if pr.get("prospect_id"):
        if not p:
            return False, "il lead non c'e' piu' nel database"
        if not _lead_vivo(p):
            return False, "non e' piu' un lead (pipeline, cliente, perso, bloccato)"
        if az.get("strade"):
            return True, "ha le strade: decisione viva"          # il sistema le ha gia' pensate: le decide Dre con un tocco
        if tipo in ("umano", "risposta"):
            ok, perche = _persona(pr, p)
            if not ok:
                return False, perche
            ultima = p.get("last_reply_at")
            if ultima and ora - quando(ultima) > datetime.timedelta(days=GIORNI_MUTO):
                return False, f"l'ultima mail sua e' di piu' di {GIORNI_MUTO} giorni fa: non e' una conversazione viva"
        if vecchia:
            ultima = p.get("last_reply_at")
            if ultima and quando(ultima).astimezone(ROMA).date() >= NATO and titolo.startswith(DOMANDE):
                return True, "ha riscritto dopo il 19/10: decisione viva"
            return False, "arretrato: nata prima del sistema nuovo (19/10)"
        return True, "decisione recente su una persona vera"
    # senza lead: domande sul sistema
    if vecchia:
        return False, "arretrato: domanda sul sistema nata prima del 19/10"
    return True, "domanda recente sul sistema"


# ── 2. i gesti ─────────────────────────────────────────────────────────────────

CAMPI_P = ("id,name,company,email,classificazione,stage,pipeline_stage,fuori,no_followup,awaiting_us,last_reply_at,"
           "analysis_sent_at,enriched,phone")


def _persone(ids):
    ids = sorted({i for i in ids if i})
    out = {}
    for i in range(0, len(ids), 80):
        for p in sb("GET", f"/rest/v1/prospects?select={CAMPI_P}&id=in.({','.join(ids[i:i + 80])})") or []:
            out[p["id"]] = p
    return out


def proposte(ora):
    import revisore
    aperte = sb("GET", "/rest/v1/proposte?select=id,tipo,titolo,stato,at,prospect_id,perche,azione"
                       "&stato=in.(aperta,approvata,in_invio)&order=at.asc&limit=2000") or []
    persone = _persone(pr["prospect_id"] for pr in aperte)
    tenute, chiuse = [], []
    for pr in aperte:
        tieni, motivo = verdetto(pr, persone.get(pr["prospect_id"]), ora)
        (tenute if tieni else chiuse).append((pr, motivo))
    print(f"RIPULISCI le proposte{' (prova: non scrive)' if PROVA else ''}: {len(aperte)} aperte, ne chiudo {len(chiuse)}, ne tengo {len(tenute)}")
    for nome, gruppo in (("CHIUDO", chiuse), ("TENGO", tenute)):
        conti = {}
        for pr, motivo in gruppo:
            k = (pr["tipo"], "Da guardare tu" if (pr["titolo"] or "").startswith(DOMANDE) else "altro", motivo)
            conti[k] = conti.get(k, 0) + 1
        print(f"  {nome}:")
        for (tipo, che, motivo), n in sorted(conti.items(), key=lambda kv: -kv[1]):
            print(f"    {n:4}  {tipo:9} {che:15} {motivo}")
    if not chiuse:
        return
    righe = [{"id": pr["id"], "email": (persone.get(pr["prospect_id"]) or {}).get("email"), "azienda": ((persone.get(pr["prospect_id"]) or {}).get("company") or "")[:40],
              "classe_lead": (persone.get(pr["prospect_id"]) or {}).get("classificazione"), "verifica": f"{pr['tipo']} {pr['at'][:10]} {(pr['titolo'] or '')[:50]}",
              "esito": motivo} for pr, motivo in chiuse]
    if PROVA:
        os.environ["REVISORE_PROVA"] = "1"
    tenuti = revisore.controlla("chiudo le proposte arretrate della Posta (stato no, motivo scritto, nessuna mail)", righe,
                                chiave=lambda r: r.get("email"), irreversibile=False, dove="crm",
                                motivo="Dre, 21/10: via le bozze e le domande arretrate, domani si comincia freschi; nessuna e' una decisione viva")
    if PROVA:
        print("(prova a secco: nessuna scrittura)")
        return
    fatte = 0
    for r in tenuti:
        sb("PATCH", f"/rest/v1/proposte?id=eq.{r['id']}&stato=in.(aperta,approvata,in_invio)",
           {"stato": "no", "risposta": (MOTIVO + r["esito"])[:300], "risposta_il": ora.isoformat()}, {"Prefer": "return=minimal"})
        fatte += 1
    print(f"  chiuse {fatte} proposte")


def da_chiamare(ora):
    """«Da chiamare» scritto dal sistema senza un cellulare suo -> «Da rispondere», Dre responsabile."""
    import revisore
    from segnale_provvisorio import cellulare_di, passa_a_dre
    righe = sb("GET", "/rest/v1/snella_lead?select=prospect_id,stato,aggiornato_da,chiamata,chiamata_il&stato=eq.Da%20chiamare") or []
    del_sistema = [r for r in righe if not r.get("aggiornato_da")]
    persone = _persone(r["prospect_id"] for r in del_sistema)
    da_fare = []
    for r in del_sistema:
        p = persone.get(r["prospect_id"])
        if not p:
            continue
        cell = cellulare_di(p)
        print(f"  {(p.get('company') or '')[:34]:34} cellulare: {'si' if cell else 'no'}")
        if not cell:
            da_fare.append({"id": p["id"], "email": p.get("email"), "azienda": (p.get("company") or "")[:40], "esito": "Da rispondere, gli scrive Dre"})
    print(f"RIPULISCI «Da chiamare»{' (prova)' if PROVA else ''}: {len(righe)} righe, {len(del_sistema)} del sistema, {len(da_fare)} senza cellulare -> «Da rispondere»")
    if not da_fare:
        return
    if PROVA:
        os.environ["REVISORE_PROVA"] = "1"
    tenuti = revisore.controlla("sposto a «Da rispondere» i «Da chiamare» del sistema senza un cellulare", da_fare,
                                chiave=lambda r: r.get("email"), irreversibile=False, dove="crm",
                                motivo="Dre, 20/10 sera: Da chiamare solo con un cellulare suo; 21/10: le leggi sono retroattive")
    if PROVA:
        return
    for r in tenuti:
        riga = passa_a_dre(r["id"], None, ora)
        riga.update({"chiamata": None, "chiamata_il": None, "richiamare_il": None})
        sb("POST", "/rest/v1/snella_lead?on_conflict=prospect_id", [riga], {"Prefer": "resolution=merge-duplicates,return=minimal"})
        sb("POST", "/rest/v1/snella_note", {"prospect_id": r["id"], "testo": "Dal sistema: era «Da chiamare» senza un cellulare suo: passa a «Da rispondere», gli scrive Dre (regola del 20/10, applicata all'arretrato il 21/10)",
                                            "tipo": "nota", "autore_nome": "Clara"}, {"Prefer": "return=minimal"})
    print(f"  spostate {len(tenuti)} righe")


def main():
    ora = datetime.datetime.now(datetime.timezone.utc)
    if "--proposte" in sys.argv:
        proposte(ora)
    if "--da-chiamare" in sys.argv:
        da_chiamare(ora)
    if "--proposte" not in sys.argv and "--da-chiamare" not in sys.argv:
        print(__doc__)


if __name__ == "__main__":
    main()
