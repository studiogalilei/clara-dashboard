#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA SALUTE DEL SISTEMA (25/9/2026, da Galileo: «l'assenza e' il controllo»).

Ogni mattina Clara controlla se stessa, e parla solo se c'e' un problema:
1. corse in errore nelle ultime 24 ore (raggruppate per operazione);
2. operazioni accese che non girano da piu' di tre volte la loro cadenza;
3. bozze aperte da piu' di 21 giorni (stanno marcendo in Posta);
4. classificazioni che cambiano avanti e indietro (piu' di 2 cambi in 7 giorni);
5. proposte aperte per chi non e' piu' un lead (non dovrebbero esistere: trigger).
Se tutto e' in ordine, una riga «controllo» e basta. Se no, una Domanda in Posta.

USO
  python3 scripts/salute.py            controlla e scrive
  python3 scripts/salute.py --prova    controlla e stampa
"""
import collections
import re
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara, contattabile, proponi        # noqa: E402


# le operazioni che possono legittimamente non produrre niente per giorni:
# guardano e stanno zitte, ed e' giusto cosi'
MUTE_VA_BENE = {"salute", "backup", "avvisi", "manda", "webhooks", "lezioni", "silenzi",
                "scadenze", "diario", "diario_recap", "recap_sera", "recap_pomeriggio",
                "brief", "posta_ordine", "sync_completo", "crediti", "stripe", "calendario_sg",
                # queste guardano e parlano solo quando c'e' qualcosa da dire:
                # il silenzio e' il loro stato normale, non un guasto
                "azioni", "prezzo", "arricchisci", "followup", "rilettura", "transcript",
                "appunti", "googlefit", "calendar", "preparo", "bozze", "posta", "analisi"}


def quando(iso):
    """La data come la scrive il database, con qualunque numero di decimali."""
    t = re.sub(r"\.(\d{1,6})\d*", lambda m: "." + m.group(1).ljust(6, "0"), (iso or "").replace("Z", "+00:00"))
    return datetime.datetime.fromisoformat(t)


def main():
    prova = "--prova" in sys.argv
    ora = datetime.datetime.now(datetime.timezone.utc)
    z = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    problemi = []
    # 1. errori
    err = sb("GET", f"/rest/v1/corse?select=operazione,dettaglio&esito=eq.errore&at=gte.{z(ora - datetime.timedelta(days=1))}&limit=500") or []
    if err:
        c = collections.Counter(e["operazione"] for e in err)
        problemi.append("errori nelle ultime 24 ore: " + ", ".join(f"{k} ×{v}" for k, v in c.most_common()))
    # 2. operazioni ferme
    ferme = []
    for o in sb("GET", "/rest/v1/operazioni?select=chiave,cadenza_minuti,ultima_corsa,attiva,comando") or []:
        if not o["attiva"] or not o.get("comando"):
            continue
        u = o.get("ultima_corsa")
        if not u:
            ferme.append(f"{o['chiave']} (mai girata)"); continue
        ritardo = (ora - quando(u)).total_seconds() / 60
        if ritardo > 3 * max(int(o["cadenza_minuti"] or 60), 5) + 30:
            ferme.append(f"{o['chiave']} (da {int(ritardo // 60)} ore)")
    if ferme:
        problemi.append("operazioni ferme: " + ", ".join(ferme))
    # 3. bozze vecchie
    vecchie = sb("GET", f"/rest/v1/proposte?select=id,titolo&stato=eq.aperta&tipo=in.(risposta,umano)&at=lte.{z(ora - datetime.timedelta(days=21))}&limit=200") or []
    if vecchie:
        problemi.append(f"{len(vecchie)} bozze aperte da più di 21 giorni (es. {vecchie[0]['titolo'][:40]})")
    # 4. classificazioni ballerine
    reg = sb("GET", f"/rest/v1/registro?select=riga&tabella=eq.prospects&campo=eq.classificazione&at=gte.{z(ora - datetime.timedelta(days=7))}&limit=5000") or []
    ball = [k for k, v in collections.Counter(r["riga"] for r in reg).items() if v > 2]
    if ball:
        problemi.append(f"{len(ball)} aziende con la classificazione cambiata più di 2 volte in 7 giorni")
    # 5. bozze a chi non e' piu' un lead
    # solo quelle che portano un TESTO DA MANDARE: un promemoria interno su un
    # cliente e' giusto che esista (regola corretta il 26/9, schema_v61)
    ap = [x for x in (sb("GET", "/rest/v1/proposte?select=id,prospect_id,azione&stato=in.(aperta,approvata)&tipo=in.(risposta,umano)&prospect_id=not.is.null&limit=1000") or [])
          if "bozza" in (x.get("azione") or {})]
    ids = list({x["prospect_id"] for x in ap})
    stato = {}
    for i in range(0, len(ids), 100):
        for p in sb("GET", f"/rest/v1/prospects?select=id,fuori,stage,pipeline_stage,no_followup,classificazione&id=in.({','.join(ids[i:i+100])})") or []:
            stato[p["id"]] = p
    fuori = [x for x in ap if x["prospect_id"] in stato and not contattabile(stato[x["prospect_id"]])]
    if fuori:
        problemi.append(f"{len(fuori)} bozze da mandare ad aziende che non sono più lead (il trigger dovrebbe impedirlo)")
    # ── 6..11 I CONTROLLI DI RISULTATO (26/9). I cinque sopra guardano se il
    # sistema GIRA; questi guardano se FA QUALCOSA. Ognuno nasce da un bug vero
    # trovato a mano il 26/9, che nessun controllo automatico aveva visto:
    # Dre: «le cose non le avremmo mai trovate, e a me non piace come cosa».

    # 6. un'operazione gira e non produce mai niente: e' viva ma inutile (caso
    #    azioni.py, che per giorni ha girato «ok» creando zero promemoria)
    mute = []
    for o in sb("GET", "/rest/v1/operazioni?select=chiave,attiva,comando,ultima_corsa") or []:
        if not o["attiva"] or not o.get("comando") or o["chiave"] in MUTE_VA_BENE:
            continue
        corse = sb("GET", f"/rest/v1/corse?select=righe&operazione=eq.{o['chiave']}&at=gte.{z(ora - datetime.timedelta(days=3))}&limit=200") or []
        if len(corse) >= 5 and all((c.get("righe") or 0) == 0 for c in corse):
            mute.append(o["chiave"])
    if mute:
        problemi.append("operazioni che girano senza mai produrre niente: " + ", ".join(mute))

    # 7. cose approvate da una persona e mai partite (caso del 25/9: due
    #    risposte approvate ferme perche' l'invio era spento, senza dirlo)
    ferme_app = sb("GET", f"/rest/v1/proposte?select=id,titolo&stato=eq.approvata&at=lte.{z(ora - datetime.timedelta(hours=6))}&limit=50") or []
    if ferme_app:
        problemi.append(f"{len(ferme_app)} cose approvate e mai partite (es. {ferme_app[0]['titolo'][:40]}): l'invio è spento o bloccato")

    # 8. la coda che non si svuota: qualcuno aspetta una bozza da troppo
    coda = sb("GET", f"/rest/v1/prospects?select=id&coda=not.is.null&coda_il=lte.{z(ora - datetime.timedelta(days=2))}&limit=200") or []
    if coda:
        problemi.append(f"{len(coda)} aziende in coda da più di due giorni senza che nessuno abbia scritto la bozza")

    # 9. il registro che non sa chi ha scritto: senza nome non si ricostruisce niente
    reg2 = sb("GET", f"/rest/v1/registro?select=chi&at=gte.{z(ora - datetime.timedelta(days=1))}&limit=2000") or []
    anonimi = [r for r in reg2 if (r.get("chi") or "").rstrip(":-c ") in ("clara", "")]
    if reg2 and len(anonimi) > len(reg2) / 3:
        problemi.append(f"il registro non sa chi ha scritto su {len(anonimi)} righe di {len(reg2)}: dopo un guaio non si risale")

    # 10. l'analisi e' PARTITA (c'e' una nostra mail che la nomina) ma la scheda
    #     dice di no: e' cosi' che parte un follow-up che promette una cosa gia'
    #     data. Sei casi trovati a mano il 26/9. Avere il PDF pronto e non averlo
    #     ancora mandato invece e' normale, e non si segnala.
    mandate = sb("GET", f"/rest/v1/interactions?select=prospect_id,body&kind=in.(email_out,analisi)&at=gte.{z(ora - datetime.timedelta(days=120))}&limit=4000") or []
    dice_analisi = re.compile(r"allego l.analisi|le lascio l.analisi|l.analisi che abbiamo preparato|attached the case study|eccola.{0,20}analisi", re.I)
    con_analisi = {m["prospect_id"] for m in mandate if dice_analisi.search(m.get("body") or "")}
    bugiarde = []
    for i in range(0, len(con_analisi), 100):
        lotto = list(con_analisi)[i:i + 100]
        bugiarde += sb("GET", f"/rest/v1/prospects?select=id,company&analysis_sent=eq.false&id=in.({','.join(lotto)})") or []
    if bugiarde:
        problemi.append(f"{len(bugiarde)} aziende hanno ricevuto l'analisi ma la scheda dice «non inviata» (es. {bugiarde[0].get('company')}): rischiano un follow-up che la promette di nuovo")

    # 10-bis. L'INVIO SPENTO CON ROBA DENTRO (28/9). Dre ha approvato dal telefono
    #     e la mail non e' uscita: l'operazione «manda» era spenta dal 25 e il
    #     workspace mostrava lo stesso «Clara la sta mandando». Testuale: «è molto
    #     pericoloso, dopo non so quale hai già inviato e quale no». Adesso la
    #     schermata lo dice, e qui si controlla che non resti spento in silenzio.
    op = (sb("GET", "/rest/v1/operazioni?select=attiva,ultima_corsa&chiave=eq.manda") or [{}])[0]
    if not op.get("attiva"):
        in_attesa = sb("GET", "/rest/v1/proposte?select=id&stato=in.(approvata,in_invio)&limit=50") or []
        if in_attesa:
            problemi.append(f"l'invio automatico è SPENTO e {len(in_attesa)} mail approvate sono ferme: nessuna è partita, vanno riaccese o mandate a mano")
        else:
            problemi.append("l'invio automatico è spento: quello che approvi resta fermo")

    # 10-ter. QUALUNQUE COSA FERMA DA TROPPO (28/9). Dre: «se è ferma deve
    #     avvisarmi in qualche modo». Istituto Flegreo ha aspettato l'analisi per
    #     giorni in silenzio, perche' il sito loro rispondeva 500 e senza sito
    #     letto l'analisi non nasce. Il sistema lo sapeva a ogni giro e non lo
    #     diceva. Qui si guarda tutto quello che e' in mezzo al guado.
    fermi = []
    #   a) chi aspetta un'analisi che non arriva
    att = sb("GET", "/rest/v1/prospects?select=company,website,coda_il,enriched"
                    "&analysis_pdf=is.null&analysis_sent=eq.false&coda=not.is.null"
                    f"&coda_il=lte.{z(ora - datetime.timedelta(days=2))}&limit=100") or []
    # il sito non letto puo' voler dire tante cose (giu', 403, SSL rotto, dominio
    # sbagliato) e NON si dichiara la causa senza averla provata: il 28/9 avevo
    # scritto «il sito non risponde» per sette aziende, e provandole una per una
    # una rispondeva benissimo. Qui si dice il fatto, non la diagnosi.
    senza_sito = [a for a in att if not (((a.get("enriched") or {}).get("google_fit") or {}).get("sito_letto"))]
    if senza_sito:
        fermi.append(f"{len(senza_sito)} aziende aspettano l'analisi e il loro sito non è mai stato letto, quindi non nascerà "
                     f"(es. {senza_sito[0].get('company')}, {senza_sito[0].get('website')}): va aperto a mano per capire perché")
    elif att:
        fermi.append(f"{len(att)} aziende aspettano l'analisi da più di due giorni")
    #   b) chi e' in coda da troppo, qualunque sia il motivo
    vecchi = sb("GET", "/rest/v1/prospects?select=company,coda,coda_il&coda=not.is.null"
                       f"&coda_il=lte.{z(ora - datetime.timedelta(days=4))}&limit=100") or []
    if vecchi:
        fermi.append(f"{len(vecchi)} aziende sono in coda da più di quattro giorni (es. {vecchi[0].get('company')}: {vecchi[0].get('coda')})")
    problemi += fermi

    # 10-quater. LE DUE COPIE CHE DIVERGONO (28/9). I volumi del mercato stanno
    #     in due posti: il file nel vault, che si aggiorna misurando col Keyword
    #     Planner, e la copia nel bucket, che e' quella che l'analisi legge
    #     davvero. Il 28/9 ho misurato Sondrio, l'ho scritto nel vault, e
    #     l'analisi continuava a dire «volumi da misurare»: leggeva l'altra copia.
    try:
        import json as _j
        import urllib.request as _u
        casa = os.path.expanduser("~/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/ODYN Cockpit/data/base_analisi.json")
        if os.path.exists(casa):
            qui = len(_j.load(open(casa, encoding="utf-8")))
            rq = _u.Request(f"{os.environ.get('VITE_SUPABASE_URL', '')}/storage/v1/object/vault/riservato/base_analisi.json",
                            headers={"apikey": os.environ.get("SUPABASE_SERVICE_KEY", ""),
                                     "Authorization": f"Bearer {os.environ.get('SUPABASE_SERVICE_KEY', '')}"})
            with _u.urlopen(rq, timeout=60) as r:
                la = len(_j.loads(r.read()))
            if qui != la:
                problemi.append(f"i volumi del mercato sono in due copie diverse: {qui} combinazioni nel vault, "
                                f"{la} nel bucket che l'analisi legge davvero. Va ricaricato il file.")
    except Exception:                                         # noqa: BLE001
        pass

    # 11. NESSUNO DEVE VEDERE IL VUOTO (27/9). Il 26/9 Salvatore e Lorenzo,
    #     entrando, vedevano 5 aziende su 13.214: la regola di visibilita' da'
    #     accesso a chi ha il nome nel campo «chi segue», e quel campo era
    #     compilato su undici aziende in tutto. Nessuno se n'era accorto perche'
    #     chi guardava era CEO e vedeva tutto. Un Workspace vuoto per una persona
    #     e' un guasto, non una configurazione.
    gente = sb("GET", "/rest/v1/profili?select=id,nome,ruolo&limit=50") or []
    seguono = collections.Counter()
    off = 0
    while True:
        lotto = sb("GET", f"/rest/v1/prospects?select=chi_segue&chi_segue=not.is.null&limit=1000&offset={off}") or []
        for x in lotto:
            seguono[(x.get("chi_segue") or "").strip().split(" ")[0].lower()] += 1
        if len(lotto) < 1000:
            break
        off += 1000
        if off > 20000:
            break
    al_buio = [g for g in gente
               if (g.get("ruolo") or "") not in ("ceo",)
               and seguono.get((g.get("nome") or "").split(" ")[0].lower(), 0) < 3]
    if al_buio:
        problemi.append("aprono il Workspace e non ci trovano niente: " + ", ".join(sorted((g.get("nome") or "?").split(" ")[0] for g in al_buio))
                        + " (nessuna azienda, o quasi, porta il loro nome in «chi segue»)")

    # 12. NIENTE GIRA IN TONDO (27/9). Il 26/9 due analisi sono state riscritte
    #     sedici volte ciascuna, sempre bocciate per lo stesso motivo: undici ore
    #     di macchina in un giorno e mezzo, e ogni corsa risultava «ok».
    giri = sb("GET", "/rest/v1/prospects?select=company,enriched&enriched->analisi->>bocciature=not.is.null&limit=200") or []
    in_tondo = [g for g in giri if int((((g.get("enriched") or {}).get("analisi") or {}).get("bocciature")) or 0) >= 3]
    if in_tondo:
        problemi.append(f"{len(in_tondo)} analisi riprovate tre volte o più senza riuscire (es. {in_tondo[0].get('company')}): girano a vuoto, servono occhi umani")

    # 13. UNA COSA E' VERA IN UN POSTO SOLO (27/9). Due campi dicono la fase di
    #     un'azienda e su nove si contraddicevano: Zafferano e Klavzar erano
    #     clienti per un pezzo del sistema e prospect per un altro.
    due = sb("GET", "/rest/v1/prospects?select=company,stage,pipeline_stage&fuori=eq.true&pipeline_stage=not.is.null&limit=300") or []
    discordi = [d for d in due
                if (d.get("pipeline_stage") in ("cliente", "prova") and d.get("stage") not in ("cliente", "prova"))
                or (d.get("pipeline_stage") == "perso" and d.get("stage") in ("call_fissata", "rinviato"))]
    if discordi:
        problemi.append(f"{len(discordi)} aziende hanno due fasi diverse nei due campi (es. {discordi[0].get('company')}: «{discordi[0].get('stage')}» e «{discordi[0].get('pipeline_stage')}»)")

    testo = "Tutto in ordine: nessun errore, operazioni regolari, Posta pulita." if not problemi else "Salute del sistema:\n- " + "\n- ".join(problemi)
    print(testo)
    if prova:
        return
    if problemi:
        proponi("umano", "Salute del sistema: c'è qualcosa che non torna", perche=testo[:280], azione={"salute": problemi, "giorno": ora.date().isoformat()}, ref=f"salute:{ora.date().isoformat()}")
    else:
        di_clara("controllo", testo, letto=True)


if __name__ == "__main__":
    main()
