#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«IL SISTEMA DI STUDIO GALILEI: COM'È FATTO E CHI FA COSA» (19/10/2026).

PERCHE'
Dre, 19/10: «voglio un documento tecnico con anche i nomi ecc., non ci sto piu' capendo un cazzo».
E' la MAPPA del sistema: ogni pezzo col suo nome, cosa fa, dove sta, quando gira, chi lo tocca
(Dre / sistema / Achille). Sta in «2 Commerciale» accanto a «Come lavorare col sistema senza ansia»
(scripts/strumenti/senza_ansia.py), che invece dice i TEMPI: qui non si ripetono.

COSA FA
Legge dal database (solo lettura) la tabella `operazioni` (nome, cosa fa, cadenza, acceso o spento)
e il link del foglio, scrive il testo fisso della mappa e carica il Google Doc nella cartella
«2 Commerciale». Se c'e' gia', lo riscrive (stesso link). Nessuna mail, nessun dato di lead:
il documento non contiene nomi di aziende o persone dei lead (vale la regola del repo pubblico).

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
from direttore import corsia_di                                     # noqa: E402

PROVA = _a_secco()
COMMERCIALE = "1ipPNIf8Ep-XFIZq23u4vG8V6xJgpuo5m"
CHIAMATE = "1PWqTL7hhhPr6JaYNbBfadxnojPWAlWb6"
NOME = "Il sistema di Studio Galilei: com'è fatto e chi fa cosa"
DRE = "dramane@studiogalilei.com"

APP = "https://studiogalilei.github.io/clara/#/s/oggi"
DECISIONI = "https://claude.ai/artifact/FKxvMBWHXfuQSwuLPXgPhK"
SENZA_ANSIA = "https://docs.google.com/document/d/1zKE8CFkHO0QPOvxkItPdz97_-7QwhyK9ZpkaGHfaI0M/edit"
REPO = "https://github.com/studiogalilei/clara-dashboard"
AZIONI_GH = "https://github.com/studiogalilei/clara-dashboard/actions"
CERVELLO = "https://github.com/studiogalilei/cervello"
SUPABASE = "https://supabase.com/dashboard/project/tqssfcuzezlczfceqsmk"
SMARTLEAD = "https://app.smartlead.ai/app/master-inbox"
GCLOUD = "https://console.cloud.google.com/home/dashboard?project=686127567563"

e = html.escape


def a(link, testo):
    return f'<a href="{e(link)}">{e(testo)}</a>'


def ogni(op):
    m = op.get("cadenza_minuti") or 0
    if m >= 10080:
        return "una volta a settimana"
    if m >= 1440:
        return f"ogni giorno alle {op['ora_preferita']}" if op.get("ora_preferita") else "una volta al giorno"
    if m >= 60:
        return f"ogni {m // 60} ore" if m >= 120 else "ogni ora"
    return f"ogni {m} minuti"


def tabella(righe, intest):
    th = "".join(f"<th style='background:#eef0f4;text-align:left'>{e(x)}</th>" for x in intest)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in righe)
    return f"<table border='1' cellpadding='5' style='border-collapse:collapse;width:100%'><tr>{th}</tr>{tr}</table>"


def pagina(titolo, ancora):
    return f"<h1 id='{ancora}' style='page-break-before:always'>{e(titolo)}</h1>"


def documento(ops, foglio):
    oggi = datetime.date.today()
    accese = [o for o in ops if o.get("attiva") and o.get("comando")]
    spente = [o for o in ops if not o.get("attiva")]
    righe_ops = [(f"<b>{e(o['nome'])}</b><br><span style='color:#5b6170'>{e(o['chiave'])}</span>",
                  e(o.get("cosa") or ""), e(ogni(o)), corsia_di(o["chiave"]))
                 for o in sorted(accese, key=lambda o: (corsia_di(o["chiave"]), o["nome"]))]
    righe_spente = [(f"<b>{e(o['nome'])}</b> <span style='color:#5b6170'>({e(o['chiave'])})</span>", e(o.get("cosa") or ""))
                    for o in sorted(spente, key=lambda o: o["nome"])]
    indice = [("1", "In una pagina: il disegno e la regola d'oro", "p1"), ("2", "I luoghi di Dre", "p2"),
              ("3", "Clara, il sistema in cloud", "p3"), ("4", "Le regole che il sistema rispetta da solo", "p4"),
              ("5", "Dove stanno le cose", "p5"), ("6", "Cosa fare se...", "p6"), ("7", "Glossario: i nomi", "p7"),
              ("8", "Cosa cambia il 19/10 e cosa è in pausa", "p8")]
    ind = "".join(f"<p><a href='#{k}'>{e(t)}</a></p>" for n, t, k in indice)

    return f"""<html><head><meta charset="utf-8"></head><body style="font-family:Arial;font-size:11pt">
<h1>Il sistema di Studio Galilei: com'è fatto e chi fa cosa</h1>
<p><i>La mappa: ogni pezzo col suo nome, cosa fa, dove sta, quando gira e chi lo tocca. Al {oggi:%d/%m/%Y}.
I tempi (quanto ci mette ogni cosa) stanno nell'altro documento, {a(SENZA_ANSIA, "Come lavorare col sistema senza ansia")}: qui non si ripetono.</i></p>
<p><b>Chi tocca cosa</b>, in tutto il documento: <b>Dre</b> = tu. <b>Sistema</b> = Clara, che gira da sola in cloud.
<b>Achille</b> = l'assistente (Claude in Claude Code) che ripara e migliora il sistema.</p>
<h2>Indice</h2>{ind}

{pagina("1. In una pagina: il disegno e la regola d'oro", "p1")}
<h2>La regola d'oro</h2>
<p><b>Tu lavori dall'app e dal foglio. Il sistema fa il resto. Achille ripara e migliora: non serve ogni giorno.</b></p>
<h2>Il disegno, da sinistra a destra</h2>
<ol>
<li><b>Smartlead</b> manda le campagne dalle caselle di Lorenzo e riceve le risposte. Le campagne le tocchi solo tu.</li>
<li><b>Clara in cloud</b> (il sistema): ogni pochi minuti prende le risposte da Smartlead, le legge, fa il Google Fit e l'analisi, prepara la bozza, la controlla due volte e la manda (o la lascia a te). Gira su GitHub, non sul tuo Mac.</li>
<li><b>Il database</b> (Supabase): la memoria di tutto. Lead, mail, bozze, call, note, cosa ha fatto ogni operazione.</li>
<li>Dal database escono tre cose per te:
  <ul>
  <li><b>l'app «SG Oggi»</b> (chi chiamare, le call, la scheda di ogni lead, le note);</li>
  <li><b>il foglio «Pipeline Studio Galilei»</b> (le 8 fasi, il colpo d'occhio);</li>
  <li><b>le mail e le notifiche a te</b> (vuole sentirti, sì da servire, prenotato, manca il link...).</li>
  </ul></li>
<li><b>Il giro della settimana di Achille</b>: ogni lunedì alle 7, in cloud, Achille legge le tue note dell'app e del foglio e la pagina delle decisioni, guarda com'è andata la settimana, ripara alla fonte quello che non va e ti manda <b>una</b> mail sola col punto.</li>
</ol>
<p style="font-family:Courier New;background:#f6f7f9;padding:8px">Smartlead → Clara in cloud (GitHub, ogni 5-20 minuti) → database (Supabase) → app SG Oggi · foglio · mail e notifiche a Dre<br>
Lunedì 7:00 → il giro della settimana di Achille → una mail a Dre</p>

{pagina("2. I luoghi di Dre", "p2")}
<h2>L'app «SG Oggi»</h2>
<p>{a(APP, "Apri l'app")}. Sul telefono è l'icona «SG Oggi» nella Home. Chi la tocca: <b>Dre</b> (la legge e scrive), il <b>sistema</b> (prepara le schede ogni 10 minuti), <b>Achille</b> (legge le tue note ed esegue).</p>
<ul>
<li><b>Oggi</b>: in alto se c'è qualcuno in ritardo. Poi «Da chiamare» (chi ha chiesto di sentirti o ha lasciato il numero, col telefono pronto), «Call prenotate» (con il link del Meet), «Da decidere» (le domande e le bozze che aspettano te).</li>
<li><b>Lead</b>: chi ha risposto negli ultimi 60 giorni, con un filtro per ogni stato e la ricerca.</li>
<li><b>Tutti</b>: tutti i prospect col loro stato, anche chi non ha mai risposto (con un interruttore).</li>
<li><b>Campagne</b>: come vanno le campagne, a 7 e a 30 giorni.</li>
<li><b>La scheda di un lead</b>: telefoni, cosa fa l'azienda, stato e prossima azione, note, analisi, tutta la conversazione.</li>
</ul>
<p><b>Cosa puoi fare dall'app:</b></p>
<ul>
<li>cambiare lo <b>stato</b> (i 12 stati del 19/10), il <b>responsabile</b> (Dramane o Claude), la <b>prossima azione</b> e la sua <b>data</b>: quello che scegli tu vince su quello che dice il sistema;</li>
<li>su chi è da chiamare: <b>Chiamato</b>, <b>Non risponde</b> (conta i tentativi), <b>Richiamare il...</b> (con il giorno);</li>
<li>scrivere una <b>nota</b>: è un'istruzione per Achille, che la legge, la esegue e risponde nella scheda con «Fatto (Achille)»;</li>
<li>attivare le <b>notifiche</b> sul telefono («Attiva le notifiche») e collegare il telefono con un codice.</li>
</ul>

<h2>Il foglio «Pipeline Studio Galilei»</h2>
<p>{a(foglio, "Apri il foglio")}, nella cartella {a("https://drive.google.com/drive/folders/" + COMMERCIALE, "2 Commerciale")} del Drive condiviso. Si aggiorna da solo ogni 10 minuti (operazione «foglio»). Chi lo tocca: <b>Dre</b> nelle celle gialle, il <b>sistema</b> nel resto. Dal foglio non parte mai nessuna mail.</p>
<ul>
<li><b>Le 8 fasi</b>, una colonna ciascuna, da sinistra a destra: Analisi in preparazione · Analisi inviata · Conversazione · Chiamata conoscitiva · Chiamata tecnica · Chiamata di avvio · Periodo di prova · Cliente. Il numero nell'intestazione dice quanti sono; in Cliente c'è anche l'MRR (la somma dei retainer).</li>
<li>Sopra ogni colonna, in grigio, <b>«Ultima modifica»</b> con la data: l'ultima volta che il sistema ha cambiato qualcosa lì.</li>
<li><b>Le celle gialle</b> sono tue: la scelta della Conversazione («Da chiamare», «In attesa di risposta», «Perso»), costo, inizio e fine della Prova, il retainer del Cliente, e la colonna <b>«Note»</b> (una nota per Achille). Quello che scrivi tu non viene mai riscritto.</li>
<li><b>Spostare un lead</b>: copia e incolla il nome dell'azienda nella colonna Azienda di un'altra fase. Il sistema lo capisce al giro dopo.</li>
<li><b>Togliere un lead</b>: cancella il nome dalla sua cella. Diventa perso e non viene più contattato.</li>
</ul>

<h2>La pagina «Decisioni di Dre»</h2>
<p>{a(DECISIONI, "Apri la pagina")}. Quando Achille ha bisogno di una tua decisione (un prezzo, una regola, un caso che cambia il tuo modo di lavorare) la scrive qui con le opzioni e quella consigliata. Tu tocchi la risposta; Achille la legge e la applica. Chi la tocca: <b>Dre</b> e <b>Achille</b>.</p>

<h2>Le mail e le notifiche che ricevi</h2>
<p>Tutte arrivano <b>solo a te</b> (dramane@), per mail e sul telefono. Quando arrivano esattamente sta nel documento «senza ansia».</p>
<ul>
<li><b>Vuole sentirti: azienda</b>: uno ha chiesto di essere chiamato o ha lasciato il numero (operazione «segnale»).</li>
<li><b>Sì da servire: azienda</b>: un sì aspetta da più di 10 minuti senza risposta («segnale»).</li>
<li><b>Prenotato: azienda, giorno e ora</b>, con la scheda; la mattina della call «Oggi alle...»; e se la call viene spostata o cancellata («segnale»).</li>
<li><b>Manca il link: azienda</b>: vi siete accordati per la call dopo e l'invito non c'è in calendario («foglio»).</li>
<li><b>In attesa da 5 giorni: azienda</b>: l'avevi messo «In attesa di risposta» nel foglio e non ha scritto («foglio»).</li>
<li><b>Un guasto</b> (Gmail o database fermi): al massimo una volta ogni 2 ore.</li>
<li><b>Il punto della settimana</b>: il lunedì mattina, una mail di Achille (il giro della settimana).</li>
</ul>

<h2>Il documento «senza ansia»</h2>
<p>{a(SENZA_ANSIA, "Come lavorare col sistema senza ansia")}: i tempi misurati (in quanto parte un sì, una bozza, un follow-up), cosa ti arriva, cosa fai tu e dove. Questo documento è la mappa, quello è l'orologio.</p>

{pagina("3. Clara, il sistema in cloud", "p3")}
<p><b>Il direttore</b> è il pezzo che fa partire tutto: gira su GitHub ogni 20 minuti (e subito, quando Smartlead avvisa che è arrivata una risposta). Legge la tabella <b>operazioni</b> del database: per ognuna sa ogni quanto deve girare e se è <b>accesa o spenta</b> (l'interruttore). Lavora in <b>due corsie</b> parallele: la <b>leggera</b> (le cose veloci: posta, segnale, postino, foglio) e la <b>pesante</b> (quello che usa a lungo l'intelligenza artificiale: analisi, bozze, Google Fit). Così il segnale a te e le mail approvate non aspettano dietro un'analisi.</p>
<p>Chi tocca le operazioni: le fa girare il <b>sistema</b>; gli interruttori li possono girare <b>Dre</b> (dal Workspace completo, pagina delle operazioni) e <b>Achille</b>.</p>
<h2>Le operazioni accese ({len(accese)})</h2>
{tabella(righe_ops, ["Nome", "Cosa fa", "Quando gira", "Corsia"])}
<p style="color:#5b6170"><i>«Quando gira» è il tempo minimo fra due giri: il direttore passa ogni 20 minuti, più i campanelli di Smartlead, quindi le cose «ogni 5 minuti» girano di fatto a ogni passaggio del direttore.</i></p>
<h2>Le operazioni spente ({len(spente)})</h2>
{tabella(righe_spente, ["Nome", "Cosa farebbe"])}
<h2>Fuori dal direttore (ognuna con il suo orologio su GitHub)</h2>
<ul>
<li><b>La sentinella</b> (ogni 15 minuti): sorveglia il direttore da fuori; se è bloccato lo rianima e scrive l'avviso.</li>
<li><b>L'ispettore</b> (ogni ora dalle 8 alle 21): rilegge quello che è uscito davvero da Smartlead e lo confronta col sistema. Solo letture; la sera la pagella, il lunedì i consigli.</li>
<li><b>Il backup notturno</b> (ogni notte): una copia cifrata di tutto il database, tenuta 30 giorni.</li>
<li><b>Il pull, il fit sulle liste e l'impronta</b> (ogni ora): preparano le liste nuove prima delle campagne (fa pubblicità? recensioni? è in target?).</li>
<li><b>Pubblica</b>: a ogni modifica dell'app, la ricompila e la mette online.</li>
<li><b>Controlla</b>: a ogni modifica, le prove e le regole che non devono rompersi mai.</li>
<li><b>Il giro della settimana di Achille</b>: ogni lunedì alle 7, una routine in cloud (vedi la parte 1).</li>
</ul>

<h2>Il percorso di una risposta, passo per passo</h2>
<ol>
<li><b>Il campanello</b> (webhook): Smartlead avvisa che è arrivata una risposta e il direttore parte subito.</li>
<li><b>Sync</b> (sincronizza Smartlead): la risposta entra nel database, nella scheda del lead.</li>
<li><b>Lampo</b>: per chi ha risposto da poco fa tutta la catena qui sotto in un giro solo, senza aspettare i giri successivi.</li>
<li><b>Google Fit</b>: legge il sito, capisce settore e provincia e dà il verdetto (sì, parziale, no). Chi è no non riceve l'analisi.</li>
<li><b>Analisi</b>: scrive l'analisi Google Ads dai fatti veri (sito, annunci, recensioni, mercato della zona) e ne fa il PDF col logo.</li>
<li><b>Lettura</b>: nessuna bozza senza lettura. Legge il filo vero delle mail: abbiamo già risposto? ha già l'analisi? ha detto no? è un fuori ufficio?</li>
<li><b>Bozze</b>: scrive la risposta col playbook e con il tuo stile.</li>
<li><b>Seconda testa</b>: un secondo modello rilegge «la loro mail / la nostra ultima / la bozza» e dice coerente o no. Se no, la bozza resta a te come «da guardare».</li>
<li><b>Prima risposta</b>: se è un sì semplice e passa tutti i controlli, la approva lei al posto tuo (dalle 8 alle 21). Tutto il resto (no, rinvii, domande, prezzi, casi strani) resta a te in Oggi.</li>
<li><b>Revisore</b>: rilegge ogni mail sapendo che partirà davvero. Può solo fermare, mai mandare.</li>
<li><b>Approva</b>: una bozza approvata (da te, dalla prima risposta, o da Achille quando gliel'hai chiesto) passa ad «approvata».</li>
<li><b>Il postino</b> (manda): manda le approvate da Smartlead, nel filo della persona, con analisi e presentazione allegate. Ha un lucchetto: la stessa mail non parte mai due volte.</li>
<li><b>Segnale</b>: se la risposta è calda o un sì resta lì, ti scrive (parte 2).</li>
<li><b>Promemoria</b>: il giorno lavorativo prima di una chiamata conoscitiva, il tuo messaggio a chi l'ha prenotata.</li>
<li><b>Schede</b>: ogni 10 minuti prepara le schede dell'app. <b>Foglio</b>: ogni 10 minuti aggiorna il foglio.</li>
<li>Dopo l'analisi: i <b>follow-up</b> (5 giorni dopo, col tuo testo parola per parola) e i <b>silenzi</b> (10 giorni senza risposta dopo il follow-up: esce dai prospect).</li>
</ol>

{pagina("4. Le regole che il sistema rispetta da solo", "p4")}
<ul>
<li><b>Mai una mail a un cliente o a chi è in pipeline</b> (in trattativa, in call, in prova). La regola è murata nel database: anche se un pezzo sbaglia, il database rifiuta la bozza.</li>
<li><b>Mai a chi ha detto no, a chi ha chiesto di non essere contattato, a chi è perso o soppresso.</b> «Non contattare» è un blocco per sempre.</li>
<li><b>Nessuna bozza senza lettura</b> del filo vero, e ogni bozza passa dalla seconda testa.</li>
<li><b>Le risposte ai sì partono da sole dal 15/10</b>, con analisi e presentazione, dopo tutti i controlli. Fusibile: al massimo 60 al giorno (serve solo se il sistema impazzisse).</li>
<li><b>Prezzi, garanzie fuori regola, reclami, lutti, legali: a te.</b> Il sistema prepara la bozza ma non la manda.</li>
<li><b>Il prezzo suggerito resta interno</b>: non finisce mai in una mail.</li>
<li><b>Tetti di spesa</b>: le letture con l'intelligenza artificiale per il segnale hanno un tetto (10 per giro, 150 al giorno); una risposta già letta non si ripaga. I follow-up hanno un <b>ammortizzatore</b> (5 in più per casella al giorno), non un tetto.</li>
<li><b>Il promemoria della conoscitiva</b> parte il giorno lavorativo prima (il venerdì per il lunedì), una volta sola per call, dalle 9 alle 18.</li>
<li><b>Le azioni di massa passano dal Revisore</b>: prova a secco, conteggi, campione, seconda testa; sopra 300 righe serve il tuo ok.</li>
<li><b>Quello che decidi tu vince</b>: uno stato scelto a mano (il «lock umano») il sistema non lo riscrive; le celle gialle del foglio nemmeno.</li>
<li><b>Le 8 fasi</b> del foglio (parte 2) e <b>i 12 stati</b> dell'app, con <b>le tue 4 regole</b>: 1) un contatto, uno stato; 2) ogni stato ha una prossima azione, se non si sa cosa fare lo stato è sbagliato; 3) le date stanno nel campo data, non in stati nuovi; 4) mai automatizzare alla cieca un rifiuto o un'opportunità calda.</li>
<li><b>Le campagne Smartlead le tocchi solo tu.</b> Il sistema su Smartlead legge e risponde nei fili, non cambia le campagne.</li>
<li><b>Se una cosa è ferma, deve avvisare</b>: la sentinella e la salute del mattino lo dicono, mai silenzio.</li>
</ul>

{pagina("5. Dove stanno le cose", "p5")}
{tabella([
        ("<b>Il codice</b>", f"{a(REPO, 'clara-dashboard')} su GitHub. <b>È pubblico</b>: dentro non ci sono mai dati di lead, nomi o mail.", "Achille"),
        ("<b>Il cervello</b>", f"{a(CERVELLO, 'cervello')} su GitHub, <b>privato</b>: la memoria di Achille e le note.", "Achille"),
        ("<b>Il database</b>", f"{a(SUPABASE, 'Supabase')}, progetto Studio Galilei. Le tabelle sono sotto.", "sistema, Achille"),
        ("<b>Cosa gira in cloud</b>", f"{a(AZIONI_GH, 'GitHub Actions')}: il direttore, la sentinella, l'ispettore, il backup, le liste, la pubblicazione dell'app.", "sistema"),
        ("<b>L'app online</b>", f"{a(APP, 'studiogalilei.github.io/clara')}", "Dre"),
        ("<b>Drive</b>", f"Drive condiviso Studio Galilei: {a('https://drive.google.com/drive/folders/' + COMMERCIALE, '2 Commerciale')} (foglio e documenti), {a('https://drive.google.com/drive/folders/' + CHIAMATE, 'Chiamate')} (gli appunti delle call).", "Dre, sistema"),
        ("<b>Google Cloud</b>", f"{a(GCLOUD, 'il progetto SG Workspace')}: i permessi con cui il sistema legge Gmail, Calendar e Drive a nome di chi li ha dati, e scrive il foglio.", "Achille"),
        ("<b>Smartlead</b>", f"{a(SMARTLEAD, 'Master inbox')}: campagne, caselle, risposte.", "Dre (campagne), sistema (risposte)"),
        ("<b>Le chiavi</b>", "Nei segreti di GitHub e in un file sul Mac di Achille (.env.local). <b>Mai nel codice</b>: un controllo blocca il salvataggio se ne trova una.", "Achille"),
        ("<b>Sul Mac</b>", "Niente del sistema gira sul Mac: se il Mac è spento, il sistema va avanti. Sul Mac c'è solo dove Achille lavora.", "—"),
    ], ["Cosa", "Dove", "Chi la tocca"])}
<h2>Le tabelle principali del database</h2>
{tabella([
        ("prospects", "Le aziende: una riga per lead, con stato, classe della risposta, fase, Google Fit, analisi."),
        ("interactions", "Tutto quello che succede a un lead: mail in entrata e in uscita, call, note, transcript."),
        ("proposte", "Le bozze e le domande per te: aperta, approvata, fatta. Il postino manda le approvate."),
        ("agenda", "Le call lette dai calendari, attaccate al lead giusto."),
        ("operazioni", "Le operazioni di Clara: cosa fanno, ogni quanto, acceso o spento (gli interruttori)."),
        ("corse", "Il registro di ogni giro di ogni operazione: ok o errore, quanto ci ha messo."),
        ("snella_lead, snella_note, snella_schede, snella_numeri", "L'app SG Oggi: le tue scelte (stato, chiamato...), le note, le schede pronte, i numeri e lo stato del foglio."),
        ("snella_stati", "I 12 stati del 19/10, con responsabile e prossima azione."),
        ("segnali_provvisori, prenotazioni_segnalate", "Le mail «vuole sentirti», «sì da servire», «prenotato» già mandate: la stessa non parte due volte."),
        ("clienti, progetti, preventivi, incassi", "Chi è cliente, i progetti, i preventivi, i pagamenti da Stripe."),
        ("registro", "Chi ha fatto cosa, sempre: ogni cambio importante con il nome di chi l'ha fatto."),
        ("suppressions", "Chi non va mai toccato."),
        ("uso_modelli, memoria_letture", "Quanto si spende in intelligenza artificiale, e le letture già pagate."),
    ], ["Tabella", "A cosa serve"])}

{pagina("6. Cosa fare se...", "p6")}
<ul>
<li><b>Qualcosa sembra fermo.</b> Guarda la data «Ultima modifica» sopra le colonne del foglio e l'ora in alto. Se il foglio non cambia da più di mezz'ora, o un sì non ha risposta e non ti è arrivato «Sì da servire», scrivi una nota nell'app: Achille la vede. Se è grave (nessuna mail parte, l'app non si apre) apri una sessione con Achille.</li>
<li><b>È partita una mail sbagliata.</b> Non si può richiamare. Scrivi subito nella scheda del lead cosa è successo; Achille ripara il caso e la fonte (la regola che l'ha lasciata passare). Se è grave (un cliente, un prezzo), spegni l'interruttore «manda» (vedi sotto) e apri una sessione con Achille.</li>
<li><b>Un lead è nella fase sbagliata.</b> Nel foglio: copia il nome nella colonna giusta, o cancellalo per toglierlo. Nell'app: cambia lo stato. Vince sempre la tua scelta.</li>
<li><b>Vuoi fermare tutto.</b> Gli interruttori stanno nella tabella operazioni (Workspace completo, pagina delle operazioni). <b>«manda»</b> spento: non parte più nessuna mail. <b>«prima_risposta»</b> spento: i sì restano a te. <b>«seguiti»</b>: i follow-up automatici. Spegnere non perde niente: le bozze restano lì.</li>
<li><b>Vuoi parlare con Achille.</b> Non serve ogni giorno: il <b>giro della settimana di Achille</b>, ogni lunedì alle 7, legge le tue note dell'app e del foglio e la pagina delle decisioni, ripara alla fonte e ti manda una mail. Le cose normali le scrivi come nota (app o colonna «Note» del foglio). Apri una sessione solo per: una mail sbagliata partita, il sistema fermo, una cosa nuova da costruire che porta una call o un cliente questa settimana.</li>
</ul>

{pagina("7. Glossario: i nomi", "p7")}
{tabella([(f"<b>{e(n)}</b>", e(d)) for n, d in [
        ("Clara (vecchia)", "Il sistema che gira adesso in cloud: tutte le operazioni della parte 3."),
        ("Clara nuova", "Il sistema ricostruito da zero, a mattoni. In pausa dal 19/10 (parte 8)."),
        ("Achille", "L'assistente (Claude in Claude Code) che costruisce, ripara e migliora il sistema."),
        ("Il giro della settimana di Achille", "La routine in cloud del lunedì alle 7: note, decisioni, settimana, riparazioni, una mail a Dre."),
        ("SG Oggi", "L'app sul telefono e sul computer: Oggi, Lead, Tutti, Campagne."),
        ("Snella", "Il nome interno dell'app SG Oggi (la «versione snella» del Workspace)."),
        ("Workspace completo", "La vecchia Dashboard, a un tocco dall'app: Posta, operazioni, clienti."),
        ("Il foglio", "Il foglio Google «Pipeline Studio Galilei» con le 8 fasi."),
        ("Direttore", "Il pezzo che fa partire le operazioni ogni 20 minuti, in due corsie."),
        ("Corsia", "Leggera (le cose veloci) o pesante (le cose lunghe con l'intelligenza artificiale): girano in parallelo."),
        ("Interruttore", "Acceso o spento di un'operazione, nella tabella operazioni."),
        ("Campanello", "L'avviso di Smartlead che fa partire subito il direttore quando arriva una risposta."),
        ("Sync", "Porta le risposte di Smartlead nel database."),
        ("Lampo", "La catena intera (fit, analisi, bozza, invio) in un giro solo per chi ha appena risposto."),
        ("Google Fit", "Il verdetto: questa azienda può guadagnare con Google Ads? Sì, parziale, no."),
        ("Lettura", "Il controllo del filo vero prima di ogni bozza."),
        ("Seconda testa", "Un secondo modello che rilegge la bozza contro la mail loro e la nostra."),
        ("Revisore", "Rilegge prima che parta; può solo fermare. Era «il poliziotto»."),
        ("Postino", "L'operazione «manda»: spedisce le bozze approvate da Smartlead."),
        ("Segnale", "La mail e la notifica a te: vuole sentirti, sì da servire, prenotato."),
        ("Promemoria", "Il messaggio a chi ha prenotato la conoscitiva, il giorno lavorativo prima."),
        ("Ombra", "Un'operazione che decide e scrive cosa farebbe, ma non fa. Oggi i follow-up automatici."),
        ("Lock umano", "Una scelta fatta da una persona che il sistema non può più riscrivere."),
        ("Ammortizzatore", "Il limite dei follow-up al giorno (5 per casella): l'eccedenza passa al mattino dopo."),
        ("Fusibile", "Il limite di 60 prime risposte al giorno: scatta solo se qualcosa impazzisce."),
        ("Sentinella", "Sorveglia il direttore da fuori e lo rianima se si blocca."),
        ("Ispettore", "Rilegge quello che è uscito davvero da Smartlead."),
        ("Battito", "Il riepilogo dell'outbound: chi aspetta e da quanto."),
        ("Salute", "Il controllo del mattino: errori, operazioni ferme, bozze vecchie."),
        ("Contattabile", "La regola unica che dice se a un lead si può scrivere."),
        ("Proposta", "Una bozza o una domanda per te, nel database."),
    ]], ["Nome", "Cos'è"])}

{pagina("8. Cosa cambia il 19/10 e cosa è in pausa", "p8")}
<h2>Cosa cambia il 19/10</h2>
<ul>
<li><b>Azione e clienti fino a 50k di MRR</b>: si costruisce solo quello che porta una call o un cliente questa settimana; si ripara solo quello che fa perdere un lead.</li>
<li><b>I 12 stati</b> nell'app, in 4 gruppi (Da gestire oggi, Opportunità, In attesa, Chiusi), ognuno con responsabile e prossima azione; e le tue 4 regole.</li>
<li><b>Il foglio con le 8 fasi</b>, che si aggiorna da solo; spostare con copia e incolla, togliere cancellando; celle gialle e «Note» tue.</li>
<li><b>Le note dell'app sono per Achille</b>: le legge, le esegue, risponde «Fatto (Achille)».</li>
<li><b>Il promemoria della conoscitiva</b> il giorno prima, in automatico.</li>
<li><b>Le call in «Chiamate»</b>: gli appunti di Gemini delle tue call finiscono lì, e se manca l'invito della call dopo ti arriva «Manca il link».</li>
<li><b>Il documento «senza ansia»</b> e questa mappa.</li>
<li><b>Il giro della settimana di Achille</b>, ogni lunedì alle 7.</li>
</ul>
<h2>Cosa è in pausa</h2>
<ul>
<li><b>Clara nuova</b> è ferma fino a 50k di MRR. I mattoni già firmati restano. <b>Tranne il lettore</b> delle risposte: Achille lo porta al 90% e lo innesta nel sistema di oggi, prima in ombra (confrontato con quello di adesso), poi acceso.</li>
<li><b>Il doppio attacco</b> (mail più tua telefonata), il consiglio di chiamare più selettivo e le call dei ragazzi in «Chiamate»: seconda fase del foglio.</li>
<li>Le operazioni spente della parte 3 (diario, recap, categorie su Smartlead, orecchio di Gmail, rilettura notturna, Granola).</li>
</ul>
<p style="color:#5b6170"><i>Il documento si rifà con python3 scripts/strumenti/mappa_sistema.py: la tabella delle operazioni la legge dal database, quindi resta vera.</i></p>
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
    ops = sb("GET", "/rest/v1/operazioni?select=chiave,nome,cosa,comando,cadenza_minuti,ora_preferita,attiva&order=chiave") or []
    st = (sb("GET", "/rest/v1/snella_numeri?select=dati->>foglio_id&chiave=eq.foglio") or [{}])[0]
    fid = (st or {}).get("foglio_id")
    foglio = f"https://docs.google.com/spreadsheets/d/{fid}/edit" if fid else "https://drive.google.com/drive/folders/" + COMMERCIALE
    corpo = documento(ops, foglio)
    print(f"  {len(ops)} operazioni, foglio {foglio}")
    if PROVA:
        print(corpo)
        print("(prova: non scrivo il documento)")
        return
    d = scrivi(corpo)
    print(f"mappa del sistema: {d.get('webViewLink')}")


if __name__ == "__main__":
    main()
