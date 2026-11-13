#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL PROMEMORIA DELLA CONOSCITIVA (Dre, 19/10/2026).

Dre: «per le chiamate conoscitive, un giorno prima mandiamo un messaggio di reminder: oggi ne
avevo due e due hanno annullato». Il giorno lavorativo prima di ogni chiamata conoscitiva nel
calendario di Dre, a chi l'ha prenotata parte il suo messaggio, nel filo di mail di sempre, una
volta sola per chiamata. Strada di ogni mail: la proposta, il cancello, la seconda testa, il postino.

    python3 scripts/promemoria.py                    il giro (dalle 9 alle 18, ora di Roma)
    python3 scripts/promemoria.py --prova            mostra cosa manderebbe, non scrive niente
    python3 scripts/promemoria.py --prova --giorno 2026-10-21   come se la call fosse quel giorno
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, contattabile                              # noqa: E402

PROVA = "--prova" in sys.argv
CHI = "Regola di Dre (19/10): il promemoria il giorno prima della conoscitiva"
NUMERO_DRE = "371 116 9430"


def testo(quando):
    """Il messaggio di Dre (19/10), col lei come in tutte le nostre mail."""
    return (f"Salve,\nci vediamo {quando} per la chiamata conoscitiva: ci sarà anche il mio collega Dramane.\n"
            "Se ha un contrattempo o qualsiasi cosa, può spostarla dall'invito che ha ricevuto nel calendario.\n"
            f"Le lascio anche il numero di Dramane, se preferisce sentirci per telefono: {NUMERO_DRE}.\n"
            "Un saluto,")


def giorno_della_call(oggi):
    """Il giorno delle call a cui si manda oggi il promemoria: il prossimo giorno lavorativo
    (il venerdi' per il lunedi')."""
    g = oggi + datetime.timedelta(days=1)
    while g.weekday() >= 5:
        g += datetime.timedelta(days=1)
    return g


def quando_detto(oggi, giorno):
    nomi = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
    return "domani" if (giorno - oggi).days == 1 else nomi[giorno.weekday()]


def da_ricordare(eventi, giorno, roma):
    """Le conoscitive confermate di quel giorno con qualcuno di fuori che non l'ha rifiutata."""
    import segnale_provvisorio as SP
    out = []
    for ev in eventi:
        inizio = ev.get("inizio")
        if not inizio or inizio.astimezone(roma).date() != giorno:
            continue
        if "conoscitiv" not in (ev.get("titolo") or "").lower() or ev.get("stato") != "confirmed":
            continue
        fuori = SP._esterni(ev)
        if not fuori or all(x in (ev.get("rifiutati") or []) for x in fuori):
            continue
        out.append(ev)
    return out


def main():
    import segnale_provvisorio as SP
    import lettura
    import manda
    roma = SP.ROMA
    adesso = datetime.datetime.now(roma)
    oggi = adesso.date()
    if "--giorno" in sys.argv:
        giorno = datetime.date.fromisoformat(sys.argv[sys.argv.index("--giorno") + 1])
        oggi = giorno - datetime.timedelta(days=1)
    else:
        if adesso.weekday() >= 5 or not (9 <= adesso.hour < 18):
            # 9/11: il controllo del postino stava solo dentro l'orario, e il guasto (vale 120 min)
            # si spegneva da solo la sera: tutto il weekend i promemoria delle call di lunedi'
            # sono rimasti fermi col semaforo verde. Una cosa ferma avvisa anche fuori orario.
            print("promemoria: fuori orario (si manda nei giorni lavorativi, dalle 9 alle 18)")
            postino_fermo(); return
        giorno = giorno_della_call(oggi)
    eventi = da_ricordare(SP._eventi_calendario(adesso), giorno, roma)
    print(f"promemoria: {len(eventi)} conoscitive {giorno.isoformat()}")
    fatti = 0
    for ev in eventi:
        ref = f"promemoria:{ev['evento']}"
        if sb("GET", f"/rest/v1/proposte?select=id&ref=eq.{ref}&limit=1"):
            print(f"  gia' mandato: {ev['titolo'][:60]}"); continue
        pid = SP._riconosci(ev)
        if not pid:
            print(f"  NON abbinata a un lead, niente promemoria: {ev['titolo'][:60]}"); continue
        p = (sb("GET", f"/rest/v1/prospects?select=*&id=eq.{pid}") or [None])[0]
        if not p or not contattabile(p):
            print(f"  non contattabile: {(p or {}).get('company') or pid}"); continue
        corpo = testo(quando_detto(oggi, giorno))
        errori = manda.controlla(corpo, p) or []
        if errori:
            print(f"  {p.get('company')}: il cancello lo ferma: {'; '.join(errori)[:120]}"); continue
        _, letti = lettura.leggi(p)
        if not letti.get("ultima_loro"):
            # 2/11: senza una sua mail nel filo il database rifiuta la bozza (nessuna bozza senza
            # lettura) e il giro cadeva, saltando anche le altre call del giorno. Non c'e' un filo in
            # cui rispondere: si dice e si passa alla prossima.
            print(f"  {p.get('company')}: nel filo non c'e' nessuna sua mail, niente promemoria (lo mandi tu se serve)"); continue
        verdetto, motivo = lettura.coerenza(letti, corpo, "PROMEMORIA")
        ora_call = ev["inizio"].astimezone(roma).strftime("%H:%M")
        if PROVA:
            print(f"  (prova) a {p.get('company')} per la call delle {ora_call}: seconda testa {verdetto} {motivo[:80]}"); continue
        if verdetto != "COERENTE":
            print(f"  {p.get('company')}: la seconda testa lo ferma: {motivo[:120]}"); continue
        adesso_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        sb("POST", "/rest/v1/proposte", {
            "tipo": "risposta", "stato": "approvata", "prospect_id": pid, "ref": ref,
            "titolo": f"Promemoria della conoscitiva: {p.get('company') or ''}, {giorno.strftime('%d/%m')} alle {ora_call}"[:200],
            "perche": "Il giorno prima della conoscitiva (regola di Dre del 19/10).",
            "azione": {"bozza": corpo, "intento": "PROMEMORIA", "template": "PROMEMORIA", "allega": False,
                       "allega_presentazione": False, "approvata_da": CHI, "approvata_il": adesso_iso,
                       "lettura": {**letti, "coerenza": verdetto, "coerenza_motivo": motivo, "gruppo": None}}},
           {"Prefer": "return=minimal"})
        fatti += 1
        print(f"  promemoria approvato: {p.get('company')} (call delle {ora_call})")
    postino_fermo()
    print(f"promemoria: {fatti} approvati oggi")


def call_passata(titolo, creato_il, adesso):
    """13/11: la call di un promemoria e' gia' passata? Il titolo lo scrive main(): «…, 09/11 alle 17:00».
    L'anno e' quello in cui il promemoria e' nato (la call cade nei giorni subito dopo). Se il titolo non
    si legge, si dice di no: meglio un avviso in piu' che uno perso."""
    import re
    m = re.search(r"(\d{2})/(\d{2}) alle (\d{1,2}):(\d{2})", titolo or "")
    if not m:
        return False
    try:
        nato = datetime.datetime.fromisoformat(str(creato_il).replace("Z", "+00:00"))
        roma = adesso.tzinfo or datetime.timezone.utc
        quando = datetime.datetime(nato.year, int(m.group(2)), int(m.group(1)), int(m.group(3)), int(m.group(4)), tzinfo=roma)
        if quando < nato - datetime.timedelta(days=60):          # nato a fine dicembre, call a gennaio
            quando = quando.replace(year=nato.year + 1)
    except ValueError:
        return False
    return quando < adesso


def postino_fermo():
    """6/11: dal 3/11 il postino vecchio (operazione `manda`) e' spento e quello nuovo (clara_manda)
    legge solo clara_decisioni, quindi un promemoria approvato restava fermo in silenzio mentre il giro
    scriveva «pronti per il postino». Se una cosa e' ferma deve avvisare (28/9): finche' ci sono
    promemoria approvati e nessuno li spedisce, suona il semaforo; quando non ce ne sono piu', si spegne.
    Chi spedisce lo decide Dre: qui non si manda niente."""
    import stanza
    acceso = (sb("GET", "/rest/v1/operazioni?select=attiva&chiave=eq.manda") or [{}])[0].get("attiva")
    fermi = sb("GET", "/rest/v1/proposte?select=id,titolo,at&stato=eq.approvata&ref=like.promemoria:*") or []
    # 13/11: un promemoria la cui call e' gia' passata non serve piu' a nessuno. Restava «approvato» per
    # sempre e il semaforo e' rimasto rosso dal 9/11 al 13/11 per tre call gia' fatte: un rosso che non
    # chiede piu' niente insegna a ignorare il rosso. Si chiude con il motivo, e suona solo chi serve ancora.
    import zoneinfo
    adesso = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Rome"))
    for f in [f for f in fermi if call_passata(f.get("titolo"), f.get("at"), adesso)]:
        print(f"  chiuso, la call e' passata senza promemoria: {(f.get('titolo') or '')[:80]}")
        if not PROVA:
            sb("PATCH", f"/rest/v1/proposte?id=eq.{f['id']}&stato=eq.approvata",
               # senza risposta_il e con «pulizia»: non e' una correzione di Dre, le lezioni non la leggono
               {"stato": "no", "risposta": "superata (pulizia): la call e' passata e il promemoria non e' partito (postino spento)"})
    fermi = [f for f in fermi if not call_passata(f.get("titolo"), f.get("at"), adesso)]
    if fermi and not acceso:
        titoli = "; ".join((f.get("titolo") or "")[:80] for f in fermi)
        print(f"  FERMO: {len(fermi)} promemoria approvati e il postino (manda) e' spento: {titoli}")
        stanza.guasto("promemoria:postino", f"{len(fermi)} promemoria della conoscitiva pronti ma nessuno li spedisce "
                      f"(il postino vecchio e' spento dal 3/11): {titoli}", vale=120)
    else:
        stanza.guarito("promemoria:postino")
    return bool(fermi and not acceso)


if __name__ == "__main__":
    main()
