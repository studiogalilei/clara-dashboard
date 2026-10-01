#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE FASI DEL LAVORO, IN UN POSTO SOLO (28/9/2026).

PERCHE' ESISTE
Carlo, il 23/9: «vorremmo una pipeline per i clienti gia' attivi con le varie
task, scadenze e avanzamento delle varie fasi dei processi, ridandoci delle
tempistiche standard, in modo tale che Clara poi ci dica: guarda, mancano tre
giorni, bisognerebbe fare il check». Cinque giorni senza risposta.

I tempi qui sotto NON sono inventati: vengono dal documento «Lancio Google Ads»
che Carlo ha scritto per Salvatore (28/9) e dai suoi messaggi dello stesso
giorno. Dove il documento dice un intervallo (2-5 giorni) si prende il valore
alto, perche' una tappa che scade troppo presto diventa rumore e si smette di
guardarla.

COSA E' QUESTO FILE
La mappa del processo E la configurazione che il sistema esegue, nello stesso
posto. Non un disegno accanto al software: il software legge di qui. Se le
fasi cambiano, si cambia questo file e cambia il comportamento. Un diagramma,
se servira', si genera da qui e mai il contrario: un disegno generato non puo'
divergere.

COME SI USA
    python3 scripts/fasi.py --prova       cosa nascerebbe, senza scrivere
    python3 scripts/fasi.py               crea le tappe mancanti sui progetti
    python3 scripts/fasi.py --mostra      la mappa, leggibile
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte                                        # noqa: E402

PROVA = "--prova" in sys.argv

# ── LE FASI ───────────────────────────────────────────────────────
# «giorni» = quanti giorni lavorativi dopo l'inizio della fase.
# «chi» = chi la porta a casa, cosi' l'avviso arriva alla persona giusta.
# «aspetta» = da chi dipende: quando e' «cliente», il ritardo non e' colpa nostra
#             e l'avviso lo dice, invece di far sembrare che siamo indietro noi.
ONBOARDING = [
    {"tappa": "Incontro fatto: obiettivi, clienti target, budget",
     "giorni": 1, "chi": "marketing", "aspetta": "noi"},
    {"tappa": "Casella Gmail dedicata e accessi agli strumenti",
     "giorni": 2, "chi": "marketing", "aspetta": "cliente"},
    {"tappa": "Account, fatturazione e metodo di pagamento",
     "giorni": 5, "chi": "marketing", "aspetta": "cliente"},
    {"tappa": "Verifica del metodo di pagamento arrivata",
     "giorni": 8, "chi": "marketing", "aspetta": "cliente",
     "nota": "Carlo: tre giorni tecnici, e il cliente deve passarci la verifica"},
    {"tappa": "Tag Manager collegato (Alex se il sito non e' WordPress)",
     "giorni": 6, "chi": "frontend", "aspetta": "noi"},
    {"tappa": "Conversioni impostate e testate",
     "giorni": 8, "chi": "marketing", "aspetta": "noi"},
    {"tappa": "Verifica dell'inserzionista conclusa",
     "giorni": 12, "chi": "marketing", "aspetta": "Google",
     "nota": "Carlo: fino a una settimana, e Google non da' spiegazioni"},
    {"tappa": "Campagna in aria",
     "giorni": 14, "chi": "marketing", "aspetta": "noi"},
]

# Carlo (28/9): «il primo check vale la pena dopo tre giorni buttando un occhio,
# ma con sguardo critico dopo una settimana, poi si ricontrolla la settimana
# dopo e si iniziano a fare le prime considerazioni».
DOPO_LA_PARTENZA = [
    {"tappa": "Primo sguardo: il tracciamento e' corretto?",
     "giorni": 3, "chi": "marketing", "aspetta": "noi"},
    {"tappa": "Check critico: quali ricerche intercettiamo davvero",
     "giorni": 7, "chi": "marketing", "aspetta": "noi"},
    {"tappa": "Secondo check: quali annunci e gruppi reggono",
     "giorni": 14, "chi": "marketing", "aspetta": "noi"},
    {"tappa": "Prime considerazioni con il cliente",
     "giorni": 21, "chi": "marketing", "aspetta": "noi"},
    {"tappa": "Report del mese",
     "giorni": 30, "chi": "marketing", "aspetta": "noi", "ogni": 30},
]

# Carlo: «un cliente nuovo va lasciato andare, uno gia' attivo va controllato
# piu' spesso perche' ha gia' storico, sulle keyword e quasi giornalmente sui
# termini di ricerca».
RETAINER = [
    {"tappa": "Termini di ricerca: sfoltire le ricerche fuori tema",
     "giorni": 7, "chi": "marketing", "aspetta": "noi", "ogni": 7},
    {"tappa": "Keyword e offerte: cosa spinge e cosa si spegne",
     "giorni": 14, "chi": "marketing", "aspetta": "noi", "ogni": 14},
    {"tappa": "Report del mese",
     "giorni": 30, "chi": "marketing", "aspetta": "noi", "ogni": 30},
]

# ── IL WEB VIENE PRIMA (Carlo, 28/9) ─────────────────────────────
# «Alex deve avere una scadenza di consegna del sito web di almeno tre giorni
# prima del processo di onboarding per le Google Ads, se no poi a noi tocca fare
# tutto di corsa». E: «il sistema si blocca nella maggior parte dei casi per il
# lato web». Misurato il 28/9: cinque clienti su cinque hanno il sito che blocca
# gli Ads, e quattro su cinque non hanno nemmeno una scadenza sul sito.
WEB = [
    {"tappa": "Contenuti e materiali dal cliente",
     "giorni": 3, "chi": "frontend", "aspetta": "cliente"},
    {"tappa": "Prima versione da far vedere",
     "giorni": 8, "chi": "frontend", "aspetta": "noi"},
    {"tappa": "Revisioni chiuse",
     "giorni": 12, "chi": "frontend", "aspetta": "cliente",
     "nota": "Carlo: le revisioni continue del cliente sono il secondo motivo di ritardo"},
    {"tappa": "Sito online e consegnato",
     "giorni": 15, "chi": "frontend", "aspetta": "noi",
     "blocca_ads": True,
     "nota": "Carlo: almeno tre giorni prima che parta l'onboarding degli Ads"},
]


# I check dopo la partenza NON si contano dall'inizio del progetto, ma dal giorno
# in cui la campagna va in aria: il giorno 14 dell'onboarding. Se no il «primo
# sguardo dopo tre giorni» cadrebbe mentre stiamo ancora chiedendo gli accessi.
# Trovato guardando la mappa stampata, prima di scrivere una sola tappa vera.
PARTENZA = next(f["giorni"] for f in ONBOARDING if f["tappa"] == "Campagna in aria")
DOPO = [{**f, "giorni": f["giorni"] + PARTENZA, "da_partenza": f["giorni"]} for f in DOPO_LA_PARTENZA]

MAPPA = {
    "onboarding": ONBOARDING + DOPO,
    "trial": ONBOARDING + DOPO,
    "retainer": RETAINER,
    "web": WEB,
}

# I nomi dei progetti che sono lavoro web, per riconoscerli senza chiedere
PAROLE_WEB = ("sito", "landing", "vetrina", "web")

# Carlo (28/9): «il problema col cliente diventa evidente quando le tempistiche
# si allungano oltre i tre giorni, weekend esclusi». Sotto i tre giorni e' il
# ritmo normale di un cliente che lavora; sopra, e' un ritardo da dire.

PREAVVISO = 3          # Clara avvisa tre giorni prima, come chiedeva Carlo


def giorni_lavorativi(da, quanti):
    """Sabato e domenica non contano: i tempi di Carlo sono giorni lavorativi."""
    d = da
    fatti = 0
    while fatti < quanti:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            fatti += 1
    return d


def mostra():
    print("LE FASI DEL LAVORO (dai tempi di Carlo, 28/9)\n")
    for nome, fasi in MAPPA.items():
        print(f"  {nome.upper()}")
        for f in fasi:
            ogni = f"  (poi ogni {f['ogni']} gg)" if f.get("ogni") else ""
            att = "" if f["aspetta"] == "noi" else f"  [aspetta: {f['aspetta']}]"
            quando = (f"gg {f['giorni']:>3}" + (f" (+{f['da_partenza']} dalla partenza)" if f.get("da_partenza") else ""))
            print(f"    {quando:<26}  {f['tappa']:<52} {f['chi']}{att}{ogni}")
            if f.get("nota"):
                print(f"            {f['nota']}")
        print()
    print(f"  Clara avvisa {PREAVVISO} giorni prima di ogni tappa.")


def e_web(g):
    """Questo progetto e' lavoro web (sito, landing, vetrina)?"""
    testo = f"{g.get('nome') or ''} {g.get('natura') or ''}".lower()
    return any(k in testo for k in PAROLE_WEB)


def tipo_di(g):
    """Che fasi segue questo progetto. Il web si riconosce dal nome, il resto dal tipo."""
    if e_web(g):
        return "web"
    t = (g.get("tipo") or "").strip()
    return t if t in MAPPA else None


def il_web_blocca(progetti):
    """IL SITO VIENE PRIMA DEGLI ADS (Carlo, 28/9). Per ogni cliente che ha sia un
    lavoro web sia una campagna, il sito deve essere consegnato almeno tre giorni
    prima che parta l'onboarding. Se il sito e' in ritardo, non e' in ritardo solo
    lui: trascina la campagna, e questo va detto a tutti e due, non solo ad Alex.
    Restituisce, per cliente, la coppia (progetto web, progetto ads)."""
    per_cliente = {}
    for g in progetti:
        per_cliente.setdefault((g.get("cliente") or "").strip().lower(), []).append(g)
    coppie = []
    for _, lista in per_cliente.items():
        web = [x for x in lista if e_web(x)]
        ads = [x for x in lista if not e_web(x) and (x.get("tipo") in ("onboarding", "trial"))]
        for w in web:
            for a in ads:
                coppie.append((w, a))
    return coppie


def main():
    if "--mostra" in sys.argv:
        mostra(); return
    if "--legami" in sys.argv:
        pg = sb("GET", "/rest/v1/progetti?select=id,cliente,nome,natura,tipo,stato,scadenza,chi_segue"
                       "&stato=neq.consegnato&limit=200") or []
        coppie = il_web_blocca(pg)
        print(f"IL SITO CHE BLOCCA LA CAMPAGNA: {len(coppie)} clienti\n")
        for w, a in coppie:
            sc = w.get("scadenza") or "NESSUNA SCADENZA"
            print(f"  {w.get('cliente')}")
            print(f"     web: {w.get('nome')} ({w.get('stato')}), scadenza {sc}, segue {w.get('chi_segue')}")
            print(f"     ads: {a.get('nome')} ({a.get('tipo')}), segue {a.get('chi_segue')}")
            if not w.get("scadenza"):
                print(f"     -> manca la data di consegna del sito: senza quella nessuno sa se siamo in ritardo")
            print()
        return
    oggi = datetime.date.today()
    progetti = sb("GET", "/rest/v1/progetti?select=id,cliente,nome,natura,tipo,stato,scadenza,chi_segue,data_inizio,note,at"
                         "&stato=neq.consegnato&limit=200") or []
    gia = {}
    for t in (sb_tutte("/rest/v1/tappe?select=progetto_id,titolo&limit=2000") or []):
        gia.setdefault(t["progetto_id"], set()).add(t["titolo"])
    nuove = 0
    senza_tipo = []
    senza_data = []
    senza_inizio = []
    for g in progetti:
        tipo = tipo_di(g)
        if not tipo:
            senza_tipo.append(g)
            continue
        # DA QUANDO SI CONTA (28/9). Prima si ripiegava sulla data di nascita del
        # progetto nel sistema, l'8 settembre per tutti, e il risultato era cinque
        # clienti con «campagna in aria» lo stesso giorno: una data calcolata, non
        # vera, e le note dicevano pure «da pagare». Una data finta e' peggio di
        # nessuna data, perche' fa suonare allarmi che nessuno controlla.
        # Senza data d'inizio le fasi non nascono, e si chiede la data.
        if not g.get("data_inizio"):
            senza_inizio.append(g)
            continue
        try:
            inizio = datetime.date.fromisoformat(g["data_inizio"])
        except Exception:                                     # noqa: BLE001
            senza_inizio.append(g)
            continue
        for f in MAPPA[tipo]:
            if f["tappa"] in gia.get(g["id"], set()):
                continue
            quando = giorni_lavorativi(inizio, f["giorni"])
            # LA DATA DI CONSEGNA DEL SITO NON SI INVENTA (28/9). Contando i giorni
            # dalla nascita del progetto, tutti e sei i siti sarebbero scaduti lo
            # stesso giorno: una data finta che fa suonare sei allarmi insieme.
            # Carlo dice che la consegna del sito deve stare tre giorni prima
            # dell'onboarding, e quella data la sa solo chi lo sta facendo.
            # Quindi: se il progetto web non ha una scadenza vera, la tappa finale
            # non nasce, e si chiede la data invece di inventarla.
            if f.get("blocca_ads") and not g.get("scadenza"):
                senza_data.append(g)
                continue
            if f.get("blocca_ads") and g.get("scadenza"):
                quando = datetime.date.fromisoformat(g["scadenza"])
            # LE TAPPE GIA' PASSATE NASCONO CHIUSE (28/9). I progetti sono nati
            # l'8 settembre: contando i giorni, 63 tappe su 97 sarebbero nate
            # scadute. Un elenco di 63 cose in ritardo il primo giorno e' il muro
            # che fa smettere di guardare, e per il lavoro gia' fatto sarebbe pure
            # falso. Restano nella storia del progetto, ma non chiamano nessuno.
            # Chi le vuole riaprire lo fa a mano, e sa perche'.
            passata = quando < oggi
            riga = {"progetto_id": g["id"], "titolo": f["tappa"], "data": quando.isoformat(),
                    "fatta": passata}
            if passata:
                riga["fatta_il"] = quando.isoformat()
            nome = f"{g.get('cliente') or '?'}: {f['tappa']}"
            if PROVA:
                print(f"  {quando:%d/%m}  {'(chiusa) ' if passata else '         '}{nome[:56]}")
                nuove += 1
                continue
            sb("POST", "/rest/v1/tappe", riga)
            nuove += 1
    print(f"fasi: {nuove} tappe {'da creare' if PROVA else 'create'} su {len(progetti)} progetti "
          f"(quelle con data passata nascono gia' chiuse: restano nella storia, non avvisano)")
    if senza_inizio:
        print(f"  {len(senza_inizio)} progetti senza data d'inizio: le fasi non nascono, perche' "
              f"contarle dalla nascita nel sistema darebbe date finte")
        for g in senza_inizio:
            print(f"     {g.get('cliente')}/{g.get('nome')} ({g.get('tipo') or 'senza tipo'}, segue {g.get('chi_segue') or 'nessuno'})"
                  + (f" - nota: {str(g.get('note'))[:40]}" if g.get("note") else ""))
    if senza_data:
        print(f"  {len(senza_data)} siti senza data di consegna: la tappa finale non nasce, perche' "
              f"la data la sa solo chi lo sta facendo")
        for g in senza_data:
            print(f"     {g.get('cliente')}/{g.get('nome')} (segue {g.get('chi_segue') or 'nessuno'})")
        print("  Carlo: il sito va consegnato almeno tre giorni prima che parta l'onboarding degli Ads")
    if senza_tipo:
        print(f"  {len(senza_tipo)} progetti senza tipo, quindi senza fasi: "
              + ", ".join(f"{g.get('cliente')}/{g.get('nome')}" for g in senza_tipo[:6]))
        print("  (vanno messi come onboarding, retainer o trial: lo decide chi li segue)")


if __name__ == "__main__":
    main()
