// Modalita' dimostrativa: la Dashboard piena di dati realistici, senza login.
// Si accende aggiungendo ?demo alla URL. Serve a due cose: far vedere la forma
// a Dre con un click, e permettere i collaudi visivi automatici.
// Le modifiche restano in memoria: chiudi la pagina e sparisce tutto.
import type { Prospect, Interaction, AgendaItem } from './types'

const oggi = new Date()
const gg = (n: number) => new Date(oggi.getTime() - n * 86400000).toISOString()
const fra = (n: number) => new Date(oggi.getTime() + n * 86400000).toISOString()
const data = (n: number) => gg(n).slice(0, 10)
// n ore fa: i messaggi della demo devono restare sempre prima di quelli
// che scrivi tu adesso (QA browser, 15/9)
const oreFa = (n: number) => new Date(Date.now() - n * 3600000).toISOString()

const vuoto = {
  role: null, phone: null, linkedin: null, website: null, owner_name: null,
  socials: {}, first_reply_at: null, analysis_pdf: null, next_action: null,
  next_action_date: null, no_followup: false, deal_value: null, lost_reason: null,
  notes: null, enriched: {}, followup_due: null, ooo_until: null, prova_inizio: null, prova_fine: null,
  fuori: false, fuori_at: null, pipeline_stage: null,
  fuori_binario: null, market: null, contratto: null, canone: null,
  descrizione: null, sg_id: null, chi_segue: null,
} as const

export const prospects: Prospect[] = [
  {
    ...vuoto, id: 'p1', sg_id: 127, email: 'ufficio@x-holding.it', name: null,
    company: 'Serenergy', website: 'serenergy.it', sector: 'fotovoltaico_casa',
    city: 'Padova', campaign: 'Casa 2, fotovoltaico',
    descrizione: 'Installano fotovoltaico sulle case private in provincia di Padova. Scrive dalla casella dell’ufficio, il nome del titolare non compare.',
    stage: 'analisi_inviata', classificazione: 'positivo', awaiting_us: false,
    analysis_sent: true, analysis_sent_at: gg(49), last_reply_at: gg(53),
    updated_at: gg(1),
  },
  {
    ...vuoto, id: 'p2', sg_id: 84, email: 'info@primarysecuritykey.it', name: 'Marco R.',
    company: 'Primary Security Key', sector: 'serramenti', city: 'Vicenza',
    campaign: 'Casa 1, serramenti', stage: 'analisi_inviata',
    classificazione: 'positivo', awaiting_us: false,
    analysis_sent: true, analysis_sent_at: gg(63), last_reply_at: gg(67),
    updated_at: gg(2),
  },
  {
    ...vuoto, id: 'p3', sg_id: 133, email: 'amministrazione@apiemme.it', name: 'Paolo A.',
    company: 'Apiemme Engineering', sector: 'fotovoltaico_casa', city: 'Treviso',
    campaign: 'Casa 2, fotovoltaico', stage: 'in_follow_up',
    classificazione: 'rinvio', awaiting_us: false, ooo_until: data(3),
    analysis_sent: true, analysis_sent_at: gg(40), last_reply_at: gg(12),
    notes: 'Era in ospedale: delicato, niente pressione.', updated_at: gg(3),
  },
  {
    ...vuoto, id: 'p4', sg_id: 156, email: 'segreteria@ceritalia.it', name: 'Lucia B.',
    company: 'CER Italia', sector: 'fotovoltaico_casa', city: 'Verona',
    campaign: 'Casa 2, fotovoltaico', stage: 'risposto',
    classificazione: 'tiepido', awaiting_us: true,
    analysis_sent: false, analysis_sent_at: null, last_reply_at: gg(1),
    updated_at: gg(0),
  },
  {
    ...vuoto, id: 'p5', sg_id: 141, email: 'anna@venicedesignweek.com', name: 'Anna',
    company: 'Venice Design Week', website: 'venicedesignweek.com',
    sector: null, city: 'Venezia', campaign: 'Eventi',
    descrizione: 'Organizzano la settimana del design a Venezia, a ottobre. Vendono biglietti e spazi espositivi: la campagna serve nei tre mesi prima dell’evento.',
    stage: 'call_fissata', classificazione: 'positivo', awaiting_us: false,
    analysis_sent: true, analysis_sent_at: gg(35), last_reply_at: gg(10),
    fuori: true, fuori_at: gg(9), pipeline_stage: 'conoscitiva',
    fuori_binario: 'no', next_action: 'Conoscitiva fissata',
    next_action_date: fra(1).slice(0, 10), updated_at: gg(0),
  },
  {
    ...vuoto, id: 'p6', sg_id: 98, email: 'info@zenisicurezza.it', name: 'Alberto Zeni',
    company: 'Zeni Sicurezza', website: 'zenisicurezza.it',
    sector: 'serramenti', city: 'Belluno', campaign: 'Casa 1, serramenti',
    stage: 'call_fissata', classificazione: 'rinvio', awaiting_us: false,
    analysis_sent: true, analysis_sent_at: gg(45), last_reply_at: gg(29),
    fuori: true, fuori_at: gg(28), pipeline_stage: 'conoscitiva',
    fuori_binario: 'si', updated_at: gg(5),
  },
  {
    ...vuoto, id: 'p7', sg_id: 12, email: 'amministrazione@klavzar.it', name: 'Klavzar',
    company: 'Klavzar', sector: null, city: 'Gorizia', campaign: null,
    stage: 'cliente', classificazione: 'positivo', awaiting_us: false,
    analysis_sent: true, analysis_sent_at: gg(120), last_reply_at: gg(20),
    fuori: true, fuori_at: gg(90), pipeline_stage: 'cliente',
    fuori_binario: 'si', contratto: 'stable', canone: 1400, updated_at: gg(4),
  },
  {
    ...vuoto, id: 'p8', sg_id: 158, email: 'info@bimoutgroup.com', name: null,
    company: 'Bimout Group', sector: 'carpenteria_metallica', city: 'Pordenone',
    campaign: 'Casa 1, serramenti', stage: 'risposto',
    classificazione: 'positivo', awaiting_us: true,
    analysis_sent: false, analysis_sent_at: null, last_reply_at: gg(2),
    updated_at: gg(0),
  },
]

prospects.push(
  {
    ...vuoto, id: 'p9', sg_id: 201, email: 'marco@tecnolegno.it', name: 'Marco Bianchi',
    company: 'Tecnolegno', sector: 'serramenti', city: 'Udine',
    campaign: 'LinkedIn, profilo 2', chi_segue: 'Dre', stage: 'risposto',
    classificazione: 'positivo', awaiting_us: false,
    analysis_sent: false, analysis_sent_at: null, last_reply_at: gg(4), updated_at: gg(4),
  },
  {
    ...vuoto, id: 'p10', sg_id: 202, email: 'info@verdeurbano.it', name: null,
    company: 'Verde Urbano', sector: 'giardinaggio', city: 'Treviso',
    campaign: 'LinkedIn, profilo 1', chi_segue: 'Dre', stage: 'risposto',
    classificazione: 'tiepido', awaiting_us: false,
    analysis_sent: false, analysis_sent_at: null, last_reply_at: gg(11), updated_at: gg(11),
  },
)

export const interactions: Interaction[] = [
  { id: 'i1', prospect_id: 'p1', at: gg(66), kind: 'email_out', body: 'Prima mail: chiediamo il permesso di mandare l’analisi' },
  { id: 'i2', prospect_id: 'p1', at: gg(64), kind: 'email_out', body: 'Secondo tentativo' },
  { id: 'i3', prospect_id: 'p1', at: gg(53), kind: 'email_out', body: '«Chiudo qui se non è il momento»' },
  { id: 'i4', prospect_id: 'p1', at: gg(53), kind: 'email_in', body: '«Sentiamo»: da qui diventa prospect' },
  { id: 'i5', prospect_id: 'p1', at: gg(49), kind: 'analisi', body: 'Analisi inviata, con la presentazione dello studio' },
  { id: 'i6', prospect_id: 'p5', at: gg(37), kind: 'email_out', body: 'Prima mail' },
  { id: 'i7', prospect_id: 'p5', at: gg(37), kind: 'email_in', body: 'Anna: «Sì, volentieri»' },
  { id: 'i8', prospect_id: 'p5', at: gg(35), kind: 'analisi', body: 'Analisi inviata' },
  { id: 'i9', prospect_id: 'p5', at: gg(10), kind: 'email_in', body: 'Anna: «Facciamo una call»' },
  { id: 'i10', prospect_id: 'p6', at: gg(29), kind: 'email_in', body: '«Sentiamoci a settembre»' },
  { id: 'i11', prospect_id: 'p7', at: gg(90), kind: 'nota', body: 'Firmato: periodo di prova, poi stable 1.400 €/mese' },
]


// Storico sintetico per i grafici di Analytics: volumi plausibili sulle
// ultime 9 settimane (solo aggregati, non si aprono dalle liste).
const RITMO = [
  // [giorni fa, email_out, email_in, analisi, followup, transcript]
  [63, 60, 2, 1, 0, 0], [56, 80, 3, 2, 1, 0], [49, 90, 4, 3, 1, 1],
  [42, 70, 3, 2, 2, 0], [35, 40, 2, 2, 1, 1], [28, 10, 1, 1, 1, 0],
  [21, 0, 1, 0, 1, 0], [14, 0, 1, 1, 1, 1], [7, 20, 2, 1, 2, 0],
  [2, 30, 3, 1, 1, 1],
]
let seq = 0
for (const [giorniFa, out, dentro, analisi, followup, call] of RITMO) {
  const pezzi: Array<[Interaction['kind'], number]> = [
    ['email_out', out], ['email_in', dentro], ['analisi', analisi],
    ['followup', followup], ['transcript', call],
  ]
  for (const [kind, n] of pezzi) {
    for (let k = 0; k < n; k++) {
      interactions.push({
        id: `st-${seq++}`,
        prospect_id: 'storico',
        at: gg(giorniFa - (k % 5)),
        kind,
        body: null,
      })
    }
  }
}

// la prep pre-call di esempio (il formato vero del protocollo)
interactions.push({
  id: 'prep-1', prospect_id: 'p5', at: gg(0), kind: 'prep',
  body: `PREP, Conoscitiva Venice Design Week (Anna)

CHI SONO
Organizzano la settimana del design a Venezia, terza settimana di ottobre.
Vendono biglietti (25-60 EUR) e spazi espositivi alle aziende del design
(da 800 EUR a salire). Pubblico: designer, architetti, appassionati.

COME E' ARRIVATA
Ha risposto alla prima mail il 26/7: "Si', volentieri". Il 22/8: "Facciamo
una call". Tono caldo, decide lei.

COSA DICE L'ANALISI CHE HA IN MANO
2.400 ricerche/mese sul design a Venezia, CPC 0,85 EUR, domanda che esplode
a settembre-ottobre. Ora comprano biglietti: la finestra e' ADESSO.

LE 10 DOMANDE (dal generico al preciso)
1. Com'e' nata la Design Week e che edizione e' questa?
2. Chi e' il pubblico che pagate di piu' per raggiungere?
3. Come vi trovano oggi le persone che comprano il biglietto?
4. Quanto pesa la biglietteria rispetto agli spazi espositivi?
5. Cosa avete provato finora per promuovervi online?
6. Quanto vale un espositore in piu' rispetto a cento biglietti?
7. Nelle settimane prima dell'evento, quanto traffico regge il sito?
8. Se le ricerche esplodono a settembre, chi le intercetta oggi? (leva: l'analisi)
9. Con 2.400 ricerche/mese a 0,85 EUR, che budget avrebbe senso per voi?
10. Se vi portiamo compratori a ottobre, chi decide e in quanto tempo?

DA VALIDARE PER LA TECNICA
Budget reale, chi decide, accesso al sito/tag, obiettivo (biglietti o espositori).`,
})

export const agenda: AgendaItem[] = [
  { id: 4, at: gg(3).slice(0, 11) + '11:00:00', titolo: 'Conoscitiva, Zeni Sicurezza', tipo: 'conoscitiva', prospect_id: 'p6', fonte: 'gcal' },
  { id: 5, at: fra(12).slice(0, 11) + '10:00:00', titolo: 'Check mensile, Klavzar', tipo: 'altro', prospect_id: 'p7', fonte: 'gcal' },
  { id: 1, at: fra(1).slice(0, 11) + '15:00:00', titolo: 'Conoscitiva, Venice Design Week', tipo: 'conoscitiva', prospect_id: 'p5', link: 'https://meet.google.com/abc-defg-hij', fonte: 'gcal',
    preparata_il: oreFa(3),
    preparazione: `Chi sono: Venice Design Week, organizzano la settimana del design a Venezia a ottobre. Vendono biglietti e spazi espositivi, la stagione buona sono i tre mesi prima.

A che punto siamo
- Analisi mandata il 12 agosto, Anna ha risposto subito.
- Il 6 settembre ha chiesto lei di sentirsi: e' il momento giusto, l'evento e' a ottobre.
- Nessun preventivo ancora, nessun budget dichiarato.

Cosa chiedere
- Quanti biglietti vendono oggi online e quanti vorrebbero venderne.
- Chi decide sulla spesa, e entro quando.
- Se hanno gia' provato campagne e con chi.

Attento a
- L'evento e' a ottobre: se si parte, si parte adesso o non ha senso.` },
  { id: 2, at: fra(4).slice(0, 11) + '09:00:00', titolo: 'Invio follow-up, 30 mail pronte', tipo: 'invio', prospect_id: null, fonte: 'gcal' },
  { id: 3, at: fra(8).slice(0, 11) + '09:00:00', titolo: 'Ripartono le campagne', tipo: 'altro', prospect_id: null, fonte: 'gcal' },
  // le scadenze degli account, quelle di Salvatore: si mettono dal Calendario
  // e compaiono anche in Oggi, a chi le ha messe
  { id: 6, at: fra(0).slice(0, 11) + '09:00:00', titolo: 'Rifare il budget di ottobre', tipo: 'budget', prospect_id: 'p7', owner: 'demo', fonte: 'workspace' },
  { id: 7, at: fra(2).slice(0, 11) + '09:00:00', titolo: 'Rinnovo campagna brand', tipo: 'rinnovo', prospect_id: 'p3', owner: 'demo', fonte: 'workspace' },
  { id: 8, at: fra(12).slice(0, 11) + '09:00:00', titolo: 'Budget del trimestre', tipo: 'budget', prospect_id: 'p5', owner: 'demo', fonte: 'workspace' },
] as AgendaItem[]

export const clara_messaggi = [
  {
    id: 0, at: oreFa(6), tipo: 'saluto', letto: true, prospect_id: null,
    testo: 'Buongiorno Dre. Giornata leggera: una call domani, oggi si chiude la coda.',
  },
  {
    id: 1, at: oreFa(6.1), tipo: 'brief', letto: true, prospect_id: null,
    testo: 'Buongiorno Dre. Il punto di oggi:\n15:00: Conoscitiva, Venice Design Week (domani, ti preparo il foglio)\nIn coda: 2 da rispondere, 3 follow-up dovuti.\nHo controllato tutto io, il resto sta in Oggi.',
  },
  {
    id: 2, at: oreFa(5.9), tipo: 'promemoria', letto: false, prospect_id: 'p7',
    testo: 'Klavzar: giorno 52 di 60 del periodo di prova. Prepariamo il rinnovo?',
  },
  {
    id: 3, at: oreFa(5.8), tipo: 'domanda', letto: false, prospect_id: 'p1',
    testo: 'Serenergy tace da 49 giorni dopo l\'analisi. Lo tengo nel follow-up del 1° settembre o lo lasciamo andare?',
  },
  {
    id: 5, at: oreFa(3), tipo: 'domanda', letto: false, prospect_id: 'p4',
    testo: 'Ciao Dre, ho visto che su Smartlead hai fissato una call con CER Italia, però in Calendar non vedo nulla. Vuoi che la preparo io?',
  },
  {
    id: 4, at: oreFa(14), tipo: 'controllo', letto: true, prospect_id: null,
    testo: 'Controllati gli invii di ieri: tutti consegnati, nessun bounce. Le caselle sono in salute.',
  },
]

export const vault_file = [
  { id: 1, at: gg(4), nome: 'Analisi Google Ads, Serenergy', path: 'demo/analisi-serenergy.pdf', mime: 'application/pdf', dimensione: 482000, prospect_id: 'p1', sezione: 'clienti', gruppo: null, nota: null },
  { id: 2, at: gg(1), nome: 'Contratto Klavzar firmato', path: 'demo/contratto-klavzar.pdf', mime: 'application/pdf', dimensione: 130000, prospect_id: 'p7', sezione: 'clienti', gruppo: null, nota: null },
  { id: 3, at: gg(20), nome: 'sg-logo-blu.svg', path: 'demo/sg-logo-blu.svg', mime: 'image/svg+xml', dimensione: 8400, prospect_id: null, sezione: 'brand', gruppo: 'loghi', nota: null },
  { id: 4, at: gg(20), nome: 'sg-condizioni-modello.pdf', path: 'demo/sg-condizioni-modello.pdf', mime: 'application/pdf', dimensione: 96000, prospect_id: null, sezione: 'modelli', gruppo: 'modelli', nota: 'Le condizioni economiche, il modello' },
  { id: 5, at: gg(30), nome: 'Visura camerale', path: 'demo/visura.pdf', mime: 'application/pdf', dimensione: 210000, prospect_id: null, sezione: 'azienda', gruppo: null, nota: null },
]

// ---- il finto Supabase: quel poco che serve alle viste --------------------
type Riga = Record<string, unknown>

const sync_runs: Riga[] = [{ id: 1, finished_at: new Date(Date.now() - 13 * 60000).toISOString(), ok: true }]

const task: Riga[] = [
  { id: 1, at: gg(1), titolo: 'Mandare i 30 follow-up su Smartlead', dettagli: 'le bozze sono pronte', scadenza: data(-1), ordine: 0, fatta: false, fatta_il: null, owner: 'demo', da: 'demo', stato: 'accettata' },
  { id: 2, at: gg(2), titolo: 'Rispondere a Giacomo sul form', dettagli: null, scadenza: null, ordine: 1, fatta: true, fatta_il: gg(1), owner: 'demo', da: 'demo', stato: 'fatta' },
  // il pod di Carlo: due persone con roba in mano, una scaduta
  { id: 3, at: gg(3), titolo: 'Rifare il budget di Klavzar', dettagli: null, scadenza: data(2), ordine: 2, fatta: false, fatta_il: null, owner: 'salvatore', da: 'carlo', stato: 'accettata' },
  { id: 4, at: gg(1), titolo: 'Controllare le conversioni di settembre', dettagli: null, scadenza: data(-3), ordine: 3, fatta: false, fatta_il: null, owner: 'salvatore', da: 'carlo', stato: 'accettata' },
  { id: 5, at: gg(6), titolo: 'Pubblicare la landing di Zeni', dettagli: null, scadenza: null, ordine: 4, fatta: true, fatta_il: gg(2), owner: 'alex', da: 'carlo', stato: 'fatta' },
  { id: 6, at: gg(1), titolo: 'Sistemare i moduli del sito Klavzar', dettagli: null, scadenza: data(4), ordine: 5, fatta: false, fatta_il: null, owner: 'alex', da: 'carlo', stato: 'accettata' },
]

// le persone dentro la Dashboard: servono per mandarsi le task
const profili: Riga[] = [
  { id: 'demo', nome: 'Dre', ruolo: 'ceo' },
  { id: 'giacomo', nome: 'Giacomo Facchin', ruolo: 'ceo' },
  { id: 'carlo', nome: 'Carlo Durigon', ruolo: 'manager' },
  { id: 'salvatore', nome: 'Salvatore', ruolo: 'specialist' },
  { id: 'alex', nome: 'Alex', ruolo: 'frontend' },
]

// la chat della squadra: due scambi, uno con un documento taggato al cliente
const chat: Riga[] = [
  { id: 1, at: oreFa(20), da: 'carlo', a: null, testo: 'Il modello delle condizioni economiche, aggiornato: usate questo.', prospect_id: 'p7', file_id: 4, letto: true },
  { id: 2, at: oreFa(4), da: 'carlo', a: 'demo', testo: 'Il contratto firmato, da mandare a Giacomo per la fattura.', prospect_id: 'p7', file_id: 2, letto: false },
  { id: 3, at: oreFa(2), da: 'demo', a: 'salvatore', testo: 'L\'analisi che gli abbiamo mandato: guarda le campagne prima della call.', prospect_id: 'p1', file_id: 1, letto: false },
]

// i progetti: il lavoro a scadenza del cliente demo (Klavzar, p7)
const progetti: Riga[] = [
  { id: 1, at: gg(12), prospect_id: 'p7', nome: 'Sito vetrina', natura: 'sito', chi_segue: 'Alex',
    scadenza: data(-18), valore: 1500, stato: 'in_corso', note: null, owner: null },
  { id: 2, at: gg(3), prospect_id: 'p7', nome: 'Setup campagne Google Ads', natura: 'setup', chi_segue: 'Carlo',
    scadenza: data(-40), valore: 800, stato: 'da_iniziare', note: null, owner: null },
  { id: 3, at: gg(90), prospect_id: 'p7', nome: 'Audit iniziale', natura: 'audit', chi_segue: 'Carlo',
    scadenza: data(60), valore: 350, stato: 'consegnato', note: null, owner: null },
]


// I PREVENTIVI, IL LISTINO E GLI INCASSI (15/9): la squadra impara qui dentro,
// quindi anche la pagina dei soldi deve avere qualcosa da mostrare
const listino: Riga[] = [
  { id: 1, nome: 'Fase pilota Google Ads, 2 mesi', descrizione: 'Due mesi di lavoro reale: analisi, impostazione, gestione e ottimizzazione sui dati.', prezzo: 1500, ricorrenza: 'una_tantum', linea: 'marketing', ordine: 1, attivo: true },
  { id: 2, nome: 'Lavoro continuativo Google Ads', descrizione: 'Dal terzo mese: gestione, report periodici e call di allineamento.', prezzo: 1400, ricorrenza: 'mese', linea: 'marketing', ordine: 2, attivo: true },
  { id: 3, nome: 'Sito web', descrizione: 'Progettazione, sviluppo e pubblicazione, con il tracciamento impostato.', prezzo: 800, ricorrenza: 'una_tantum', linea: 'software', ordine: 3, attivo: true },
  { id: 4, nome: 'Landing page', descrizione: 'Una pagina di atterraggio per le campagne.', prezzo: 400, ricorrenza: 'una_tantum', linea: 'software', ordine: 4, attivo: true },
]
const preventivi: Riga[] = [
  { id: 1, prospect_id: 'p7', progetto_id: null, numero: 'SG-MK-2026-001', linea: 'marketing', titolo: 'Fase pilota Google Ads, 2 mesi e Lavoro continuativo', importo: 1500, mensile: 1400,
    voci: [{ nome: 'Fase pilota Google Ads, 2 mesi', quantita: 1, prezzo: 1500, ricorrenza: 'una_tantum' }, { nome: 'Lavoro continuativo Google Ads', quantita: 1, prezzo: 1400, ricorrenza: 'mese' }],
    inviato_il: data(12), stato: 'accettato', accettato_il: data(5), rifiutato_il: null, motivo: null, pagato_il: data(4), pagamento_atteso_il: null,
    valido_fino: data(-18), pdf_path: null, link_pagamento: null, note: null, owner: 'demo', creato_il: gg(12), aggiornato_il: gg(4) },
  { id: 2, prospect_id: 'p3', progetto_id: null, numero: 'SG-SW-2026-001', linea: 'software', titolo: 'Sito web', importo: 800, mensile: null,
    voci: [{ nome: 'Sito web', quantita: 1, prezzo: 800, ricorrenza: 'una_tantum' }],
    inviato_il: data(6), stato: 'inviato', accettato_il: null, rifiutato_il: null, motivo: null, pagato_il: null, pagamento_atteso_il: null,
    valido_fino: data(-24), pdf_path: null, link_pagamento: null, note: 'mandato via mail il giorno della call', owner: 'demo', creato_il: gg(6), aggiornato_il: gg(6) },
  { id: 3, prospect_id: 'p5', progetto_id: null, numero: 'SG-MK-2026-002', linea: 'marketing', titolo: 'Fase pilota Google Ads, 2 mesi', importo: 1500, mensile: null,
    voci: [{ nome: 'Fase pilota Google Ads, 2 mesi', quantita: 1, prezzo: 1500, ricorrenza: 'una_tantum' }],
    inviato_il: null, stato: 'bozza', accettato_il: null, rifiutato_il: null, motivo: null, pagato_il: null, pagamento_atteso_il: null,
    valido_fino: data(-30), pdf_path: null, link_pagamento: null, note: null, owner: 'demo', creato_il: gg(1), aggiornato_il: gg(1) },
]
const incassi: Riga[] = [
  { id: 'ch_demo1', genere: 'addebito', importo: 1500, valuta: 'eur', stato: 'succeeded', quando: gg(4), ricorrenza: null, metodo: 'carta',
    prossimo_il: null, fine_il: null, cliente_nome: 'Dän Ink', cliente_email: 'steven@danink.it', stripe_cliente: 'cus_demo1',
    descrizione: 'Fase pilota Google Ads', prospect_id: 'p7', preventivo_id: 1, letto_il: gg(0) },
  { id: 'sub_demo1', genere: 'abbonamento', importo: 1400, valuta: 'eur', stato: 'active', quando: gg(4), ricorrenza: 'month', metodo: 'sepa',
    prossimo_il: data(-12), fine_il: null, cliente_nome: 'Dän Ink', cliente_email: 'steven@danink.it', stripe_cliente: 'cus_demo1',
    descrizione: 'Lavoro continuativo', prospect_id: 'p7', preventivo_id: null, letto_il: gg(0) },
  { id: 'ch_demo2', genere: 'addebito', importo: 350, valuta: 'eur', stato: 'succeeded', quando: gg(20), ricorrenza: null, metodo: 'carta',
    prossimo_il: null, fine_il: null, cliente_nome: 'GR Box', cliente_email: 'info@grbox.it', stripe_cliente: 'cus_demo2',
    descrizione: 'Modifiche sito', prospect_id: 'p3', preventivo_id: null, letto_il: gg(0) },
]

// le cose da decidere: la Posta di Clara della demo. Senza, la pagina
// diceva «niente da chiedere» mentre la pallina aveva tre messaggi, e
// sembrava un errore (QA browser, 15/9)
const proposte: Riga[] = [
  {
    id: 1, at: oreFa(2), tipo: 'risposta', stato: 'aperta', prospect_id: 'p4', owner: null,
    titolo: 'CER Italia: risposta pronta',
    perche: 'Ha chiesto quanto costa. Gli propongo la call conoscitiva di giovedì.',
    azione: { bozza: 'Buongiorno,\n\ngrazie del riscontro. Le propongo una call giovedì alle 15, mezz\'ora: le mostro i numeri della sua zona e le dico cosa faremmo, senza impegno.\n\nSe le va bene, le mando l\'invito.\n\nUn saluto', template: 'INT-CALL' },
  },
  {
    id: 2, at: oreFa(4), tipo: 'avanza', stato: 'aperta', prospect_id: 'p7', owner: null,
    titolo: 'Klavzar: giorno 52 dei 60 di prova, preparo il rinnovo?',
    perche: 'La prova finisce fra otto giorni e il canone stabile è già nel preventivo accettato.',
    azione: { task: { titolo: 'Chiamare Klavzar per il rinnovo' } },
  },
  {
    id: 3, at: oreFa(5), tipo: 'classifica', stato: 'aperta', prospect_id: 'p1', owner: null,
    titolo: 'Serenergy tace da 49 giorni: lo lascio andare?',
    perche: 'Analisi mandata il 28 luglio, due follow-up, nessuna risposta.',
    azione: { prospects: { classificazione: 'negativo', awaiting_us: false } },
  },
  // tre dello stesso tipo: così si vede la risposta di gruppo, che compare
  // solo quando le domande uguali sono più di una (Dre, 15/9)
  {
    id: 4, at: oreFa(5), tipo: 'classifica', stato: 'aperta', prospect_id: 'p2', owner: null,
    titolo: 'Primary Security Key tace da 63 giorni: lo lascio andare?',
    perche: 'Analisi mandata a luglio, nessuna risposta da allora.',
    azione: { prospects: { classificazione: 'negativo', awaiting_us: false } },
  },
  {
    id: 5, at: oreFa(6), tipo: 'classifica', stato: 'aperta', prospect_id: 'p6', owner: null,
    titolo: 'Zeni Sicurezza tace da 29 giorni: lo lascio andare?',
    perche: 'Aveva detto «sentiamoci a settembre», la call è passata e non ha più scritto.',
    azione: { prospects: { classificazione: 'negativo', awaiting_us: false } },
  },
]

// in demo la sezione «Cosa cambieresti» parte vuota: si scrive e si vede
// comparire, come nel vero
const feedback: Riga[] = []

// i documenti scritti dentro l'editor: in demo si parte da zero e si vede
// nascere il primo
const documenti: Riga[] = []

const TABELLE: Record<string, Riga[]> = {
  feedback,
  documenti,
  proposte,
  chat,
  sync_runs,
  listino,
  preventivi,
  incassi,
  profili,
  progetti,
  task,
  vault_file: vault_file as unknown as Riga[],
  clara_messaggi: clara_messaggi as unknown as Riga[],
  prospects: prospects as unknown as Riga[],
  interactions: interactions as unknown as Riga[],
  agenda: agenda as unknown as Riga[],
}

function dentroLista(spec: unknown): string[] {
  if (Array.isArray(spec)) return spec.map(String)
  return String(spec).replace(/[()"]/g, '').split(',').map((s) => s.trim())
}

class Query {
  private tabella: string
  private filtri: Array<(r: Riga) => boolean> = []
  private ordina: { col: string; asc: boolean } | null = null
  private max: number | null = null
  private patch: Riga | null = null
  private nuovo: Riga | null = null
  private uno = false
  private cancella = false
  private conta = false
  private testa = false

  constructor(tabella: string) {
    this.tabella = tabella
  }

  select(_c?: string, o?: { count?: string; head?: boolean }) { this.conta = Boolean(o?.count); this.testa = Boolean(o?.head); return this }
  eq(c: string, v: unknown) { this.filtri.push((r) => r[c] === v); return this }
  neq(c: string, v: unknown) { this.filtri.push((r) => r[c] !== v); return this }
  is(c: string, v: unknown) { this.filtri.push((r) => (v === null ? r[c] == null : r[c] === v)); return this }
  in(c: string, v: unknown) { const l = dentroLista(v); this.filtri.push((r) => l.includes(String(r[c]))); return this }
  not(c: string, op: string, v: unknown) {
    if (op === 'is' && v === null) this.filtri.push((r) => r[c] != null)
    else if (op === 'in') { const l = dentroLista(v); this.filtri.push((r) => !l.includes(String(r[c]))) }
    return this
  }
  lte(c: string, v: unknown) { this.filtri.push((r) => r[c] != null && String(r[c]) <= String(v)); return this }
  gte(c: string, v: unknown) { this.filtri.push((r) => r[c] != null && String(r[c]) >= String(v)); return this }
  // .or() era un no-op: la demo mostrava gente che il DB vero esclude (2/9)
  or(s: string) {
    const clausole = spezzaOr(s).map(leggiClausola).filter(Boolean) as Array<(r: Riga) => boolean>
    if (clausole.length) this.filtri.push((r) => clausole.some((c) => c(r)))
    return this
  }
  order(c: string, o?: { ascending?: boolean }) { this.ordina = { col: c, asc: o?.ascending !== false }; return this }
  limit(n: number) { this.max = n; return this }
  single() { this.uno = true; return this }
  // i metodi che il codice vero usa e che qui mancavano: bastava uno per
  // mandare a schermo bianco tutta la pagina (QA browser, 15/9)
  maybeSingle() { this.uno = true; return this }
  like(c: string, v: string) { return this.ilike(c, v) }
  ilike(c: string, v: string) {
    const ago = String(v).replace(/^%|%$/g, '').toLowerCase()
    this.filtri.push((r) => String(r[c] ?? '').toLowerCase().includes(ago))
    return this
  }
  contains(c: string, v: unknown) {
    const cerca = Array.isArray(v) ? v.map(String) : [String(v)]
    this.filtri.push((r) => {
      const dentro = Array.isArray(r[c]) ? (r[c] as unknown[]).map(String) : []
      return cerca.every((x) => dentro.includes(x))
    })
    return this
  }
  range(da: number, a: number) { this.max = a - da + 1; return this }
  upsert(riga: Riga) { this.nuovo = riga; return this }
  delete() { this.cancella = true; return this }
  update(patch: Riga) { this.patch = patch; return this }
  insert(riga: Riga | Riga[]) { this.nuovo = riga as Riga; return this }

  then(risolvi: (r: { data: unknown; error: null; count?: number }) => unknown) {
    let righe = (TABELLE[this.tabella] ?? []).filter((r) => this.filtri.every((f) => f(r)))
    if (this.cancella) {
      const via = new Set(righe)
      TABELLE[this.tabella] = (TABELLE[this.tabella] ?? []).filter((r) => !via.has(r))
      return Promise.resolve(risolvi({ data: [], error: null }))
    }
    if (this.nuovo) {
      // sul DB vero `at` ha default now(): senza, i messaggi nuovi
      // saltavano in cima alla chat e il Vault mostrava data vuota (2/9)
      // e si inserisce anche una lista, come fa la coda di Oggi
      const nuove = (Array.isArray(this.nuovo) ? this.nuovo : [this.nuovo]) as Riga[]
      righe = nuove.map((n) => {
        const r = { id: 'demo-' + Math.random().toString(36).slice(2, 8), at: new Date().toISOString(), ...n }
        if (r.at == null) r.at = new Date().toISOString()
        TABELLE[this.tabella] ??= []
        TABELLE[this.tabella].push(r)
        return r
      })
    }
    if (this.patch) righe.forEach((r) => Object.assign(r, this.patch))
    if (this.ordina) {
      const { col, asc } = this.ordina
      // i numeri si ordinano da numeri: come stringhe 10 veniva prima di 2
      righe = [...righe].sort((a, b) => {
        const x = a[col], y = b[col]
        const n = typeof x === 'number' && typeof y === 'number'
          ? x - y
          : String(x ?? '').localeCompare(String(y ?? ''))
        return n * (asc ? 1 : -1)
      })
    }
    if (this.max != null) righe = righe.slice(0, this.max)
    // copie fresche: se si restituisse l'oggetto vero del magazzino, React
    // vedrebbe lo stesso riferimento dopo un update e non ridisegnerebbe
    const out = righe.map((r) => ({ ...r }))
    const quanti = this.conta ? righe.length : undefined
    if (this.testa) return Promise.resolve(risolvi({ data: null, error: null, count: quanti }))
    return Promise.resolve(risolvi({ data: this.uno ? (out[0] ?? null) : out, error: null, count: quanti }))
  }
}

// ── il dialetto dei filtri di PostgREST, quel tanto che ci serve ────
// Si spezza sulle virgole di primo livello: quelle dentro le parentesi
// appartengono alla lista di un `in`.
function spezzaOr(s: string): string[] {
  const out: string[] = []
  let buf = '', dentro = 0
  for (const ch of s) {
    if (ch === '(') dentro++
    if (ch === ')') dentro--
    if (ch === ',' && dentro === 0) { out.push(buf); buf = ''; continue }
    buf += ch
  }
  if (buf.trim()) out.push(buf)
  return out.map((x) => x.trim()).filter(Boolean)
}

function leggiClausola(c: string): ((r: Riga) => boolean) | null {
  // and(a.eq.1,b.eq.2): tutte le sue, dentro un or che ne vuole una
  const gruppo = /^and\((.*)\)$/.exec(c.trim())
  if (gruppo) {
    const dentro = spezzaOr(gruppo[1]).map(leggiClausola).filter(Boolean) as Array<(r: Riga) => boolean>
    return dentro.length ? (r: Riga) => dentro.every((f) => f(r)) : null
  }
  const m = /^([\w]+)\.(not\.)?(\w+)\.(.*)$/.exec(c)
  if (!m) return null
  const [, col, negato, op, grezzo] = m
  const nega = (f: (r: Riga) => boolean) => (negato ? (r: Riga) => !f(r) : f)
  if (op === 'is') return nega((r) => (grezzo === 'null' ? r[col] == null : String(r[col]) === grezzo))
  if (op === 'in') return nega((r) => dentroLista(grezzo).includes(String(r[col])))
  if (op === 'eq') return nega((r) => String(r[col]) === grezzo)
  if (op === 'neq') return nega((r) => String(r[col]) !== grezzo)
  if (op === 'gte') return nega((r) => r[col] != null && String(r[col]) >= grezzo)
  if (op === 'lte') return nega((r) => r[col] != null && String(r[col]) <= grezzo)
  if (op === 'ilike') {
    const ago = grezzo.replace(/^%|%$/g, '').toLowerCase()
    return nega((r) => String(r[col] ?? '').toLowerCase().includes(ago))
  }
  return null
}

const urlFinti = new Map<string, string>()

export const demoClient = {
  from(tabella: string) { return new Query(tabella) },
  // in demo si e' Dre: senza questa, `sono_ceo` andava in errore cinque
  // volte per pagina e i soldi restavano nascosti proprio nella modalita'
  // fatta per far vedere com'e' (QA Dre, 15/9)
  async rpc(nome: string) {
    if (nome === 'sono_ceo') return { data: true, error: null }
    // in demo il sistema e' appena passato: la riga verde si vede com'e'
    if (nome === 'ultimo_giro') return { data: new Date(Date.now() - 4 * 60000).toISOString(), error: null }
    if (nome === 'chi_sono') {
      return {
        data: {
          uid: 'demo', nome: 'Dre', ruolo: 'ceo',
          // in demo si e' Dre e si ha un pod: cosi' si vede com'e' fatta la
          // card del manager senza dover entrare come Carlo
          pod: [
            { id: 'salvatore', nome: 'Salvatore', ruolo: 'specialist' },
            { id: 'alex', nome: 'Alex', ruolo: 'frontend' },
          ],
          concessi: [], vista: null,
        },
        error: null,
      }
    }
    return { data: null, error: null }
  },
  // in demo Clara non chiama il cervello vero: dice che qui non si puo'
  functions: {
    async invoke(_nome: string) {
      return { data: { errore: 'Nella demo non scrivo davvero: entra con il tuo account' }, error: null }
    },
  },
  storage: {
    from(_bucket: string) {
      return {
        async upload(path: string, file: File) {
          try { urlFinti.set(path, URL.createObjectURL(file)) } catch { /* niente */ }
          return { data: { path }, error: null }
        },
        getPublicUrl(path: string) {
          return { data: { publicUrl: urlFinti.get(path) ?? '#' } }
        },
        async createSignedUrl(path: string) {
          return { data: { signedUrl: urlFinti.get(path) ?? '#' }, error: null }
        },
        async createSignedUrls(paths: string[]) {
          return { data: paths.map((path) => ({ path, signedUrl: urlFinti.get(path) ?? '#', error: null })), error: null }
        },
        async list() { return { data: [], error: null } },
        async remove() { return { data: [], error: null } },
      }
    },
  },
  auth: {
    getSession: async () => ({ data: { session: { user: { id: 'demo', email: 'demo@studiogalilei' } } } }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
    signOut: async () => ({}),
    signInWithPassword: async () => ({ error: null }),
  },
}
