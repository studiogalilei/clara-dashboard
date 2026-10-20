#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«IL SISTEMA DI STUDIO GALILEI: COM'È FATTO E CHI FA COSA» (19/10/2026, corto dal 20/10).

PERCHE'
Dre, 19/10: «non ci sto piu' capendo un cazzo». Dal 20/10 («io più il sistema») il documento e'
CORTO: il confine (fino all'analisi il sistema, dopo Dre), dove cliccare (foglio, link, scheda
Clara, scheda azienda), l'unica notifica e gli avvisi di guasto, cosa fa il sistema da solo, cosa
fare se il semaforo e' rosso, il controllo del venerdi', un glossario breve.

COSA FA
Legge dal database (solo lettura) il link del foglio, scrive il testo fisso e carica il Google Doc
nella cartella «2 Commerciale». Se c'e' gia', lo riscrive (stesso link). Nessuna mail, nessun dato
di lead: il documento non contiene nomi di aziende o persone (vale la regola del repo pubblico).

USO
  python3 scripts/strumenti/mappa_sistema.py           scrive il documento
  python3 scripts/strumenti/mappa_sistema.py --prova   stampa l'HTML, non scrive
"""

import datetime
import html
import json
import os
import sys
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # i moduli comuni stanno in scripts/
from stanza import sb, _a_secco                                     # noqa: E402

PROVA = _a_secco()
COMMERCIALE = "1ipPNIf8Ep-XFIZq23u4vG8V6xJgpuo5m"
NOME = "Il sistema di Studio Galilei: com'è fatto e chi fa cosa"
DRE = "dramane@studiogalilei.com"

DECISIONI = "https://claude.ai/artifact/FKxvMBWHXfuQSwuLPXgPhK"

e = html.escape


def a(link, testo):
    return f'<a href="{e(link)}">{e(testo)}</a>'


def documento(foglio):
    oggi = datetime.date.today()
    indice = [("1. Il sistema siete tu più lui", "p1"), ("2. Dove cliccare", "p2"),
              ("3. Cosa ti arriva sul telefono", "p3"), ("4. Cosa fa il sistema da solo", "p4"),
              ("5. Se il semaforo è rosso", "p5"), ("6. Il controllo del venerdì", "p6"), ("7. Glossario", "p7")]
    ind = "".join(f"<p><a href='#{k}'>{e(t)}</a></p>" for t, k in indice)
    glossario = "".join(f"<li><b>{e(n)}</b>: {e(d)}</li>" for n, d in [
        ("Clara", "il sistema. Gira da solo in cloud, anche col Mac spento."),
        ("Achille", "l'assistente (Claude) che ripara e migliora il sistema."),
        ("In conversazione", "un lead che ha risposto dopo l'analisi. Da lì scrivi tu."),
        ("Follow-up", "il messaggio di sollecito dopo l'analisi, col tuo testo."),
        ("Promemoria", "il messaggio a chi ha prenotato la chiamata, il giorno lavorativo prima."),
        ("Semaforo", "la riga in alto nella scheda Clara. Verde se tutto va, rosso se si è fermato qualcosa."),
        ("Diario", "le righe sotto il semaforo con cosa ha fatto Clara oggi e ieri."),
        ("Ferma", "il pulsante nella scheda azienda che blocca i messaggi automatici a quel lead."),
        ("Lettore", "è la Clara intelligente. Legge ogni risposta e capisce se è un sì, un no o altro."),
    ])

    return f"""<html><head><meta charset="utf-8"></head><body style="font-family:Arial;font-size:11pt">
<h1>Il sistema di Studio Galilei: com'è fatto e chi fa cosa</h1>
<p><i>Aggiornato al {oggi:%d/%m/%Y}. Si legge in cinque minuti.</i></p>
{ind}

<h2 id="p1">1. Il sistema siete tu più lui</h2>
<p><b>Fino all'analisi fa tutto il sistema.</b> Prima mail, risposta a chi dice sì, analisi, follow-up. Non devi approvare niente e non ti arrivano avvisi per questo.</p>
<p><b>Dopo l'analisi scrivi tu.</b> Se il lead risponde dopo aver ricevuto l'analisi, è <b>in conversazione</b>. Gli rispondi tu su Smartlead. Il sistema non prepara bozze.</p>
<p>Restano a te: le conversazioni, le chiamate, spostare i lead nel foglio, i prezzi. Le campagne su Smartlead le tocchi solo tu.</p>

<h2 id="p2">2. Dove cliccare</h2>
<p><b>Il foglio {a(foglio, "Pipeline Studio Galilei")}</b> è la tua base. Lo guardi la sera. Si aggiorna da solo ogni 10 minuti.</p>
<ul>
<li>Accanto a ogni azienda ci sono due link piccoli: <b>scheda</b> apre la sua scheda, <b>filo</b> apre la conversazione su Smartlead.</li>
<li>La colonna <b>Prossimo</b> dice quando il sistema scrive di nuovo a quel lead (per esempio «gio 22/10»). Vuota vuol dire che non c'è niente in programma.</li>
<li>Per spostare un lead copia il nome dell'azienda in un'altra fase. Per toglierlo cancellalo. Le celle gialle e la colonna <b>Note</b> sono tue: il sistema non le riscrive.</li>
</ul>
<p><b>La scheda «Clara»</b>, nello stesso file in basso, ti dice se il sistema sta bene.</p>
<ul>
<li>In alto il <b>semaforo</b>: verde «tutto a posto», oppure rosso con cosa si è fermato, da quando e cosa sta facendo il sistema.</li>
<li>Sotto il <b>diario</b>: cosa ha fatto Clara oggi e ieri, una riga per azione, la più recente in alto.</li>
</ul>
<p><b>La scheda azienda</b> (dal link «scheda»): contatti e sito, cosa ha scritto il lead, cosa gli abbiamo mandato con l'analisi in PDF. In più <b>il prossimo messaggio di Clara</b>, con il giorno e il testo esatto, e il pulsante <b>Ferma</b>: blocca quel messaggio e tutti i messaggi automatici dopo, finché il lead non riscrive.</p>

<h2 id="p3">3. Cosa ti arriva sul telefono</h2>
<p><b>Una notifica sola: «un lead è entrato in conversazione»</b>, con il link alla scheda. Suona per ogni persona che risponde dopo l'analisi, anche per un no. Le risposte automatiche (fuori ufficio) non suonano.</p>
<p><b>Gli avvisi di guasto</b>, rari. Suonano solo se si ferma qualcosa che costa lead o soldi:</p>
<ul>
<li>un sì aspetta l'analisi da più di un'ora, in orario di lavoro;</li>
<li>le mail non partono: crediti finiti, chiave scaduta, Smartlead che non risponde;</li>
<li>il sistema è fermo, o il foglio non si aggiorna da più di un'ora;</li>
<li>un lead è entrato in conversazione e la notifica non è partita.</li>
</ul>
<p>Un guasto suona una volta. Se dura, suona di nuovo ogni 2 ore. Quando si risolve ti arriva «Risolto». Dalle 22 alle 7:30 il telefono non suona: se il guasto c'è ancora, suona alle 7:30. Più guasti insieme fanno una notifica sola.</p>

<h2 id="p4">4. Cosa fa il sistema da solo</h2>
<ul>
<li><b>La prima risposta</b>: a chi dice sì manda l'analisi e la presentazione. Se il lead chiede di scrivere a un collega, la manda a lui con il lead in copia, solo all'indirizzo che il lead ha scritto.</li>
<li><b>I follow-up</b> dopo l'analisi, col tuo testo parola per parola. Si fermano da soli se il lead ha già risposto o se l'hai già sollecitato tu.</li>
<li><b>Il promemoria</b> a chi ha prenotato la chiamata conoscitiva, il giorno lavorativo prima.</li>
<li><b>Le categorie su Smartlead</b>: mette l'etichetta giusta a ogni lead, così i tuoi filtri sono in ordine.</li>
<li><b>Legge la tua casella</b>: se uno annulla o sposta la chiamata per mail, il lead torna «Da chiamare» e il promemoria si ferma.</li>
<li><b>La Clara intelligente</b> legge ogni risposta e decide se è un sì, un no o una richiesta di non scrivere più. Provata su più di mille risposte vere: nessun sì perso. Le vecchie liste di parole restano solo come rete di sicurezza.</li>
</ul>
<p>Non scrive mai a un cliente, a chi è in trattativa, a chi ha detto no o ha chiesto di non essere contattato.</p>

<h2 id="p5">5. Se il semaforo è rosso</h2>
<ul>
<li><b>Leggi la riga.</b> Dice cosa si è fermato e cosa sta facendo il sistema. Quasi sempre riprova da solo: aspetta il giro dopo.</li>
<li><b>Se dice «sì senza analisi»</b>: apri la scheda dal link. Se il messaggio è pronto ma fermo, guardalo lì o rispondi tu su Smartlead.</li>
<li><b>Se dice «crediti finiti o chiave scaduta»</b>: da solo non riparte. Dillo ad Achille.</li>
<li><b>Se resta rosso per ore</b>, o non parte più nessuna mail: apri una sessione con Achille.</li>
<li>Le cose piccole non urgenti scrivile nella colonna <b>Note</b> del foglio: le legge il controllo del venerdì.</li>
</ul>

<h2 id="p6">6. Il controllo del venerdì</h2>
<p>Ogni venerdì alle 8 Achille gira da solo in cloud. Legge le tue note e la pagina {a(DECISIONI, "Decisioni di Dre")}, guarda com'è andata la settimana e ripara alla fonte quello che non va. Poi ti manda <b>una mail sola</b> con il punto. Non serve aprire Claude per sapere com'è andata.</p>

<h2 id="p7">7. Glossario</h2>
<ul>{glossario}</ul>
<p style="color:#5b6170"><i>Il documento si rifà con python3 scripts/strumenti/mappa_sistema.py.</i></p>
</body></html>"""


def scrivi(corpo_html):
    """Il Google Doc nella cartella «2 Commerciale»: nuovo, o lo stesso riscritto (stesso link)."""
    from google_api import access_token, drive_cerca
    nome_q = NOME.replace("'", "\\'")
    q = (f"'{COMMERCIALE}' in parents and name = '{nome_q}' and mimeType = 'application/vnd.google-apps.document' and trashed = false")
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
    st = (sb("GET", "/rest/v1/snella_numeri?select=dati->>foglio_id&chiave=eq.foglio") or [{}])[0]
    fid = (st or {}).get("foglio_id")
    foglio = f"https://docs.google.com/spreadsheets/d/{fid}/edit" if fid else "https://drive.google.com/drive/folders/" + COMMERCIALE
    corpo = documento(foglio)
    print(f"  foglio {foglio}")
    if PROVA:
        print(corpo)
        print("(prova: non scrivo il documento)")
        return
    d = scrivi(corpo)
    print(f"mappa del sistema: {d.get('webViewLink')}")


if __name__ == "__main__":
    main()
