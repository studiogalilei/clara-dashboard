#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«COME LAVORARE COL SISTEMA SENZA ANSIA» (19/10/2026).

PERCHE'
Il design del foglio della pipeline (docs/superpowers/specs/2026-10-19-foglio-pipeline-design.md):
una pagina sola per Dre, in parole semplici, con i tempi MISURATI sui giri veri e non stimati.
Cosa succede da solo e in quanto tempo, cosa gli arriva sul telefono, cosa fa lui e dove, cosa
fare se qualcosa sembra fermo.

COSA FA
Misura sull'ultima settimana (tabelle proposte, interactions, segnali_provvisori, corse) e scrive
il Google Doc nella cartella «2 Commerciale», accanto al foglio. Se c'e' gia', lo riscrive (stesso
link). Solo lettura sul database; nessuna mail.

USO
  python3 scripts/strumenti/senza_ansia.py           misura e scrive il documento
  python3 scripts/strumenti/senza_ansia.py --prova   misura e stampa, non scrive
"""

import datetime
import html
import json
import os
import statistics
import sys
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # i moduli comuni stanno in scripts/
from stanza import sb, sb_tutte, quando, _a_secco                  # noqa: E402

PROVA = _a_secco()
COMMERCIALE = "1ipPNIf8Ep-XFIZq23u4vG8V6xJgpuo5m"
NOME = "Come lavorare col sistema senza ansia"
DRE = "dramane@studiogalilei.com"
GIORNI = 7                       # l'ultima settimana: dal 15/10 il sistema gira in due corsie, prima i tempi erano altri


def _z(t):
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def durata(minuti):
    if minuti is None:
        return "non misurabile"
    if minuti < 1:
        return "meno di un minuto"
    if minuti < 90:
        return f"{round(minuti)} minuti"
    if minuti < 36 * 60:
        return f"{minuti / 60:.1f} ore".replace(".", ",").replace(",0 ", " ")
    return f"{minuti / 1440:.1f} giorni".replace(".", ",").replace(",0 ", " ")


def riassunto(valori):
    """(mediana, 9 su 10 entro, quanti) in minuti."""
    v = sorted(x for x in valori if x is not None and x >= 0)
    if not v:
        return None, None, 0
    p90 = v[min(len(v) - 1, int(round(0.9 * (len(v) - 1))))]
    return statistics.median(v), p90, len(v)


def in_orario(t):
    import zoneinfo
    r = t.astimezone(zoneinfo.ZoneInfo("Europe/Rome"))
    return r.weekday() < 5 and 9 <= r.hour < 17


def misura():
    ora = datetime.datetime.now(datetime.timezone.utc)
    da = ora - datetime.timedelta(days=GIORNI)
    fatte = sb_tutte(f"/rest/v1/proposte?select=id,at,prospect_id,risposta_il,azione->>approvata_da,azione->>approvata_il,"
                     f"azione->>intento&tipo=eq.risposta&stato=eq.fatta&risposta_il=gte.{_z(da)}")
    pids = sorted({x["prospect_id"] for x in fatte if x.get("prospect_id")})
    entrate = {}
    for i in range(0, len(pids), 80):
        for r in sb_tutte(f"/rest/v1/interactions?select=id,prospect_id,at&kind=eq.email_in&prospect_id=in.({','.join(pids[i:i + 80])})"
                          f"&at=gte.{_z(da - datetime.timedelta(days=14))}"):
            entrate.setdefault(r["prospect_id"], []).append(quando(r["at"]))

    def sua_prima(x):
        """La sua mail a cui risponde la bozza: l'ultima prima che la bozza nascesse."""
        prima = [t for t in entrate.get(x["prospect_id"], []) if t <= quando(x["at"])]
        return max(prima) if prima else None

    auto = [x for x in fatte if (x.get("approvata_da") or "").startswith("prima-risposta-automatica")]
    a_mano = [x for x in fatte if x not in auto and (x.get("intento") or "").startswith("INT")]
    seguiti = [x for x in fatte if "FOLLOW" in (x.get("intento") or "").upper() or (x.get("intento") or "") == "RIPRESA"]
    m = {}
    # la prima risposta automatica: dalla sua mail all'invio (in orario, cioe' quando il sistema puo' mandare)
    righe = [((quando(x["risposta_il"]) - t).total_seconds() / 60, t) for x in auto if (t := sua_prima(x)) and x.get("risposta_il")]
    m["auto_orario"] = riassunto([d for d, t in righe if in_orario(t)])
    m["auto_tutte"] = riassunto([d for d, t in righe])
    # le risposte che passano da Dre: la bozza pronta dalla sua mail, poi l'invio dalla bozza
    m["bozza_pronta"] = riassunto([(quando(x["at"]) - t).total_seconds() / 60 for x in a_mano if (t := sua_prima(x))])
    m["bozza_invio"] = riassunto([(quando(x["risposta_il"]) - quando(x["at"])).total_seconds() / 60 for x in a_mano if x.get("risposta_il")])
    m["approvata_invio"] = riassunto([(quando(x["risposta_il"]) - quando(x["approvata_il"])).total_seconds() / 60
                                      for x in fatte if x.get("approvata_il") and x.get("risposta_il")])
    m["seguito_invio"] = riassunto([(quando(x["risposta_il"]) - quando(x["at"])).total_seconds() / 60 for x in seguiti if x.get("risposta_il")])
    # il segnale sul telefono: dalla sua mail alla notifica (caldo subito, si' dopo 10 minuti)
    segn = sb_tutte(f"/rest/v1/segnali_provvisori?select=id,interaction_id,tipo,quando,come&quando=gte.{_z(da)}")
    segn = [s for s in segn if s.get("come") == "segnale" and s.get("interaction_id")]
    arrivi = {}
    ids = sorted({str(s["interaction_id"]) for s in segn})
    for i in range(0, len(ids), 80):
        for r in sb("GET", f"/rest/v1/interactions?select=id,at&id=in.({','.join(ids[i:i + 80])})") or []:
            arrivi[str(r["id"])] = quando(r["at"])
    for tipo in ("caldo", "si"):
        m[f"segnale_{tipo}"] = riassunto([(quando(s["quando"]) - arrivi[str(s["interaction_id"])]).total_seconds() / 60
                                          for s in segn if s["tipo"] == tipo and str(s["interaction_id"]) in arrivi])
    # ogni quanto girano le operazioni (gli ultimi 3 giorni)
    corse = sb_tutte(f"/rest/v1/corse?select=id,operazione,at,esito&at=gte.{_z(ora - datetime.timedelta(days=3))}")
    per_op = {}
    for c in corse:
        per_op.setdefault(c["operazione"], []).append(quando(c["at"]))
    giri = {}
    for op, tt in per_op.items():
        tt.sort()
        giri[op] = riassunto([(b - a).total_seconds() / 60 for a, b in zip(tt, tt[1:])])
    m["giri"] = giri
    m["errori"] = {op: sum(1 for c in corse if c["operazione"] == op and c["esito"] == "errore") for op in per_op}
    m["quante"] = {"auto": len(auto), "a_mano": len(a_mano), "seguiti": len(seguiti)}
    return m


def riga_tempo(r):
    med, p90, n = r
    if not n:
        return "non ancora misurabile"
    return f"di solito {durata(med)}; 9 volte su 10 entro {durata(p90)} (su {n})"


def documento(m, foglio_link):
    g = m["giri"]
    giro = lambda op: durata(g.get(op, (None, None, 0))[0])                    # noqa: E731
    oggi = datetime.date.today()
    tabella = [
        ("Un sì: la risposta con l'analisi parte da sola", riga_tempo(m["auto_orario"]),
         "lun-ven 9-17. Fuori orario aspetta il mattino dopo. Tutte, orario compreso: " + riga_tempo(m["auto_tutte"])),
        ("Una risposta che non è un sì semplice: la bozza è pronta per te", riga_tempo(m["bozza_pronta"]), "Posta / Oggi nell'app"),
        ("Dalla bozza pronta all'invio (quando passa da te)", riga_tempo(m["bozza_invio"]), "è il tempo che la bozza aspetta l'ok"),
        ("Da «approvata» a «partita» (il postino)", riga_tempo(m["approvata_invio"]), "il postino passa ogni " + giro("manda")),
        ("Un follow-up: dalla bozza all'invio", riga_tempo(m["seguito_invio"]), "i follow-up li decide il sistema, li approvi tu o Achille"),
        ("Le mail nuove entrano nel sistema", "ogni " + giro("sync_smartlead"), "dalla casella di Smartlead"),
        ("Il segnale «Vuole sentirti» sul telefono", riga_tempo(m["segnale_caldo"]), "subito, appena letta"),
        ("Il segnale «Sì da servire» sul telefono", riga_tempo(m["segnale_si"]), "solo se dopo 10 minuti nessuno ha risposto"),
        ("Il promemoria al lead prima della conoscitiva", "il giorno lavorativo prima, 9-18", "parte da solo, nel filo di mail"),
        ("Il foglio della pipeline si aggiorna", "ogni 10 minuti", "le tue celle gialle le legge prima"),
    ]
    e = html.escape
    righe_t = "".join(f"<tr><td>{e(a)}</td><td><b>{e(b)}</b></td><td>{e(c)}</td></tr>" for a, b, c in tabella)
    return f"""<html><head><meta charset="utf-8"></head><body style="font-family:Arial">
<h1>Come lavorare col sistema senza ansia</h1>
<p><i>Una pagina. I tempi sono misurati sui giri veri degli ultimi {GIORNI} giorni (da quando il sistema gira in due corsie), al {oggi:%d/%m/%Y}, non stimati.</i></p>
<p><b>In breve.</b> Il sistema risponde da solo ai sì semplici, prepara le bozze di tutto il resto, segue i follow-up e ti avvisa quando serve una persona.
Tu chiami, fai le call e chiudi. Se non ti arriva niente, vuol dire che non c'è niente da fare: quando qualcosa si ferma, il sistema lo dice.</p>
<h2>Cosa succede da solo, e in quanto tempo</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse"><tr><th>Cosa</th><th>Quanto ci mette (misurato)</th><th>Note</th></tr>{righe_t}</table>
<h2>Cosa ti arriva sul telefono (e per mail)</h2>
<ul>
<li><b>Vuole sentirti: azienda</b>. Uno ha chiesto di essere chiamato o ha lasciato il numero. Lo chiami: è in Oggi, «Da chiamare».</li>
<li><b>Sì da servire: azienda</b>. Un sì è lì da più di 10 minuti senza risposta. Di solito vuol dire che la risposta automatica si è fermata a un controllo: guarda la bozza in Posta.</li>
<li><b>Prenotato: azienda, giorno e ora</b>, con la scheda di chi è. E la mattina della call, dalle 8:30, «Oggi alle...».</li>
<li><b>Manca il link: azienda</b>. Nella call vi siete accordati per la call dopo con una data, e il giorno dopo l'invito non è in calendario. Mandalo.</li>
<li><b>In attesa da 5 giorni: azienda</b>. L'avevi messo «In attesa di risposta» nel foglio e non ha scritto. Lo chiami o lo segni perso.</li>
<li>Un guasto (Gmail o il database fermi): al massimo una volta ogni 2 ore, finché non si risolve.</li>
</ul>
<h2>Cosa fai tu, e dove</h2>
<ul>
<li><b>Nell'app (SG Oggi)</b>: chiamare chi è «Da chiamare», approvare le bozze che ti aspettano, leggere la scheda prima di una call, scrivere una nota (la legge Achille e la esegue).</li>
<li><b>Nel foglio</b> (<a href="{e(foglio_link)}">Pipeline Studio Galilei</a>): guardare a che punto sei; scrivere solo nelle <b>celle gialle</b>:
«Sposta in» (anche «Togli dal foglio» per chi si perde dopo una call), la scelta della Conversazione («Da chiamare», «In attesa di risposta», «Perso»),
costo, inizio e fine della Prova, il retainer del Cliente, la «Nota per Achille». Quello che scrivi tu non viene mai riscritto.</li>
<li><b>Le call</b>: le fai tu. Gli appunti di Gemini finiscono da soli nella cartella «Chiamate» del Drive.</li>
<li>Dal foglio <b>non parte mai nessuna mail</b>: cambia solo lo stato, le note e le date.</li>
</ul>
<h2>Se qualcosa sembra fermo</h2>
<ul>
<li><b>Il foglio non cambia</b>: guarda l'ora in alto a destra («Aggiornato ... alle»). Se è più vecchia di mezz'ora, scrivilo ad Achille.</li>
<li><b>Un sì non ha ricevuto risposta</b>: ti è già arrivato «Sì da servire». La bozza è in Posta; se non c'è, l'analisi non è nata: dillo ad Achille.</li>
<li><b>Un lead è fermo in una colonna da giorni</b>: spostalo con «Sposta in», o scrivi cosa fare nella «Nota per Achille».</li>
<li><b>Una cosa che non ti torna</b>: una nota nell'app sul lead. Achille le legge a ogni giro.</li>
</ul>
<p style="color:#5b6170"><i>Misurato su {m['quante']['auto']} risposte automatiche, {m['quante']['a_mano']} risposte passate da te e {m['quante']['seguiti']} follow-up degli ultimi {GIORNI} giorni.
Il documento si rifà con python3 scripts/strumenti/senza_ansia.py.</i></p>
</body></html>"""


def scrivi(corpo_html):
    """Il Google Doc nella cartella «2 Commerciale»: nuovo, o lo stesso riscritto (stesso link)."""
    from google_api import access_token, drive_cerca
    q = (f"'{COMMERCIALE}' in parents and name = '{NOME}' and mimeType = 'application/vnd.google-apps.document' and trashed = false")
    gia = drive_cerca(q, campi="id,webViewLink", email=DRE)
    confine = uuid.uuid4().hex
    meta = {"name": NOME, "mimeType": "application/vnd.google-apps.document"}
    if not gia:
        meta["parents"] = [COMMERCIALE]
    corpo = (f"--{confine}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
             f"--{confine}\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n{corpo_html}\r\n--{confine}--").encode("utf-8")
    base = "https://www.googleapis.com/upload/drive/v3/files"
    url = (f"{base}/{gia[0]['id']}?uploadType=multipart&supportsAllDrives=true&fields=id,webViewLink" if gia
           else f"{base}?uploadType=multipart&supportsAllDrives=true&fields=id,webViewLink")
    req = urllib.request.Request(url, data=corpo, method="PATCH" if gia else "POST", headers={
        "Authorization": "Bearer " + access_token(DRE), "Content-Type": f"multipart/related; boundary={confine}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    m = misura()
    for k, v in m.items():
        if k not in ("giri", "errori"):
            print(f"  {k}: {v}")
    print("  giri (mediana minuti): " + ", ".join(f"{op} {round(v[0] or 0)}" for op, v in sorted(m["giri"].items()) if v[2]))
    st = (sb("GET", "/rest/v1/snella_numeri?select=dati->>foglio_id&chiave=eq.foglio") or [{}])[0]
    fid = (st or {}).get("foglio_id")
    link = f"https://docs.google.com/spreadsheets/d/{fid}/edit" if fid else "https://drive.google.com/drive/folders/" + COMMERCIALE
    corpo = documento(m, link)
    if PROVA:
        print("(prova: non scrivo il documento)")
        return
    d = scrivi(corpo)
    print(f"senza ansia: {d.get('webViewLink')}")


if __name__ == "__main__":
    main()
