// DATI FINTI per i prototipi del laboratorio (notte 5-6/10/2026).
// Nessun nome vero: il sito e' pubblico. Oggi = martedi' 6 ottobre 2026.
window.LAB = {
  oggi: '2026-10-06',
  io: { id: 'dre', nome: 'Dre', ruolo: 'CEO' },
  squadra: [
    { id: 'dre', nome: 'Dre', ruolo: 'CEO, vendite', colore: '#1C2E6E' },
    { id: 'carlo', nome: 'Carlo', ruolo: 'Delivery, Google Ads', colore: '#2979C4' },
    { id: 'giacomo', nome: 'Giacomo', ruolo: 'Coordinamento', colore: '#0F766E' },
    { id: 'lorenzo', nome: 'Lorenzo', ruolo: 'Outbound', colore: '#B45309' },
    { id: 'salvatore', nome: 'Salvatore', ruolo: 'Progetti', colore: '#7C3AED' },
    { id: 'alex', nome: 'Alex', ruolo: 'Supporto', colore: '#BE123C' },
  ],
  // tappa: risposta | analisi | follow_up | conoscitiva | tecnica | avvio | prova | cliente
  aziende: [
    { id: 'a1', nome: 'Ferramenta Bassi', settore: 'Ferramenta e utensili', citta: 'Padova', persona: 'Giulia Bassi', tappa: 'conoscitiva', palla: 'noi', ultima: '2026-10-05', ticket: '1.500-6.000 €', domanda: 2400, cpc: 0.9, fit: 'SI', valore: 1400,
      dove: 'Ha detto sì il 29/9, ha letto l’analisi e ha fissato la conoscitiva per oggi alle 15.', cosaHa: 'Analisi del 30/9 (PDF)', scomode: ['Pochi prezzi sul sito', 'Concorrenza forte delle catene'] },
    { id: 'a2', nome: 'Studio Dentistico Riva', settore: 'Dentisti', citta: 'Verona', persona: 'Marco Riva', tappa: 'tecnica', palla: 'noi', ultima: '2026-10-02', ticket: '800-4.000 €', domanda: 5200, cpc: 2.1, fit: 'SI', valore: 1800,
      dove: 'Conoscitiva il 1/10: interessato alle implantologie. Tecnica con Carlo giovedì 8 alle 15:30.', cosaHa: 'Analisi del 24/9 + preventivo bozza', scomode: ['Settore sanitario: regole sugli annunci', 'Molti studi in zona'] },
    { id: 'a3', nome: 'Serramenti Vetta', settore: 'Infissi', citta: 'Treviso', persona: 'Paolo Vetta', tappa: 'follow_up', palla: 'loro', ultima: '2026-09-12', ticket: '3.000-12.000 €', domanda: 3100, cpc: 1.4, fit: 'SI', valore: 0,
      dove: 'Analisi mandata il 12/9, poi silenzio. Follow-up pronto.', cosaHa: 'Analisi del 12/9', scomode: ['Sito lento', 'Stagionalità'] },
    { id: 'a4', nome: 'Agriturismo Colle Verde', settore: 'Turismo rurale', citta: 'Siena', persona: 'Anna Rossi', tappa: 'analisi', palla: 'loro', ultima: '2026-10-04', ticket: '300-1.200 €', domanda: 900, cpc: 0.7, fit: 'FORSE', valore: 0,
      dove: 'Ha detto sì il 3/10, analisi partita da sola il 4/10.', cosaHa: 'Analisi del 4/10', scomode: ['Clienti da fuori zona', 'Ticket basso'] },
    { id: 'a5', nome: 'Officina Moretti', settore: 'Autoriparazioni', citta: 'Brescia', persona: 'Luca Moretti', tappa: 'risposta', palla: 'noi', ultima: '2026-10-06', ticket: '200-2.000 €', domanda: 1800, cpc: 1.1, fit: 'SI', valore: 0,
      dove: 'Ha risposto stamattina: «quanto costa?». Clara ha preparato la risposta, aspetta te.', cosaHa: 'Niente ancora', scomode: ['Chiede subito il prezzo', 'Officina piccola'] },
    { id: 'a6', nome: 'Pasticceria Dolce Vita', settore: 'Pasticcerie', citta: 'Bologna', persona: 'Sara Neri', tappa: 'follow_up', palla: 'loro', ultima: '2026-07-22', ticket: '40-400 €', domanda: 4100, cpc: 0.5, fit: 'FORSE', valore: 0,
      dove: 'Analisi a luglio, poi le ferie. Ripresa pronta: si parte dalle torte per le feste.', cosaHa: 'Analisi del 22/7', scomode: ['Ticket basso', 'Molto locale'] },
    { id: 'a7', nome: 'Impianti Solari Nord', settore: 'Fotovoltaico', citta: 'Bergamo', persona: 'Davide Conti', tappa: 'avvio', palla: 'carlo', ultima: '2026-10-05', ticket: '8.000-25.000 €', domanda: 6800, cpc: 1.6, fit: 'SI', valore: 2400,
      dove: 'Tecnica fatta il 3/10, passato a Carlo il 5/10. Preventivo accettato: si parte lunedì.', cosaHa: 'Preventivo accettato', scomode: ['Budget pubblicitario da definire'] },
    { id: 'a8', nome: 'Palestra Forma', settore: 'Palestre', citta: 'Milano', persona: 'Elena Ferri', tappa: 'prova', palla: 'carlo', ultima: '2026-09-28', ticket: '400-900 €', domanda: 9100, cpc: 1.9, fit: 'SI', valore: 1400,
      dove: 'Prova di 2 mesi iniziata il 15/9: giorno 21 di 60.', cosaHa: 'Contratto di prova', scomode: ['Molta concorrenza'] },
    { id: 'a9', nome: 'Cantina Le Vigne', settore: 'Vino', citta: 'Verona', persona: 'Giovanni Sala', tappa: 'cliente', palla: 'salvatore', ultima: '2026-10-01', ticket: '30-600 €', domanda: 2200, cpc: 0.8, fit: 'SI', valore: 1400,
      dove: 'Cliente da agosto, retainer mensile. Report di settembre da mandare.', cosaHa: 'Retainer', scomode: [] },
    { id: 'a10', nome: 'Edilnova Costruzioni', settore: 'Edilizia', citta: 'Vicenza', persona: 'Franco Galli', tappa: 'conoscitiva', palla: 'loro', ultima: '2026-09-30', ticket: '20.000-200.000 €', domanda: 1500, cpc: 2.6, fit: 'SI', valore: 0,
      dove: 'Ha accettato la call ma non ha ancora scelto il giorno. Proposto giovedì 8.', cosaHa: 'Analisi del 26/9', scomode: ['Decide il socio', 'Ciclo di vendita lungo'] },
  ],
  // la posta: conversazioni che aspettano Dre e follow-up pronti
  conversazioni: [
    { id: 'c1', azienda: 'a5', aspetta: 'da 3 ore', perche: 'ha chiesto il prezzo: la risposta è pronta, la approvi tu',
      filo: [
        { chi: 'noi', quando: '30/9', testo: 'Buongiorno, sono Lorenzo di Studio Galilei. Abbiamo preparato un’analisi gratuita su come Officina Moretti appare su Google: le interessa riceverla?' },
        { chi: 'loro', quando: 'oggi 9:12', testo: 'Buongiorno, sì mandatela pure. Ma quanto costa poi il vostro servizio?' },
      ],
      bozza: 'Salve Luca,\n\nle lascio qui l’analisi su Officina Moretti: la trova in allegato.\nSul costo dipende da cosa serve davvero alla vostra officina, ed è proprio quello che vorrei capire con lei in una chiamata di venti minuti.\n\nLe propongo giovedì 8 ottobre alle 15: se le va meglio un altro momento, qui trova il calendario.\n\nUn saluto' },
    { id: 'c2', azienda: 'a10', aspetta: 'da 2 giorni', perche: 'ha scritto «mi chiami» con un numero: decidi tu',
      filo: [
        { chi: 'noi', quando: '26/9', testo: 'Le lascio l’analisi su Edilnova e le propongo una call conoscitiva.' },
        { chi: 'loro', quando: '4/10', testo: 'Mi chiami pure al 347 000 0000, preferisco il telefono.' },
      ],
      bozza: null },
  ],
  seguiti: [
    { id: 's1', azienda: 'a3', giorno: 'giovedì 8 ottobre alle 15', perche: 'Analisi a settembre, poi silenzio',
      bozza: 'Salve Paolo,\n\na settembre le avevo mandato l’analisi su Serramenti Vetta, e immagino che con l’inizio dei cantieri d’autunno le settimane siano volate.\n\nMi piacerebbe sapere che impressione le ha fatto, anche solo in due righe.\n\nLe propongo una chiamata conoscitiva giovedì 8 ottobre alle 15: se le va meglio un altro momento, qui trova il calendario.\n\nUn saluto' },
    { id: 's2', azienda: 'a6', giorno: 'venerdì 9 ottobre alle 15:30', perche: 'Analisi a luglio, poi le ferie',
      bozza: 'Salve Sara,\n\na luglio le avevo lasciato l’analisi su Dolce Vita proprio prima delle ferie.\nCi torno adesso perché per una pasticceria le settimane che portano a Natale sono quelle che pesano di più, e mi piacerebbe sapere come le state preparando.\n\nLe propongo una chiamata conoscitiva venerdì 9 ottobre alle 15:30: se preferisce un altro giorno, dal calendario sceglie lei.\n\nA presto' },
  ],
  call: [
    { quando: 'oggi 15:00', azienda: 'a1', tipo: 'Conoscitiva', chi: ['dre'] },
    { quando: 'giovedì 8, 15:30', azienda: 'a2', tipo: 'Tecnica', chi: ['dre', 'carlo'] },
    { quando: 'lunedì 12, 10:00', azienda: 'a7', tipo: 'Avvio progetto', chi: ['carlo'] },
  ],
  task: [
    { id: 't1', titolo: 'Prendi in carico Impianti Solari Nord: la tecnica è fatta, si parte', da: 'dre', a: 'carlo', azienda: 'a7', scadenza: 'oggi', stato: 'da accettare' },
    { id: 't2', titolo: 'Report di settembre per Cantina Le Vigne', da: 'giacomo', a: 'salvatore', azienda: 'a9', scadenza: 'domani', stato: 'in corso' },
    { id: 't3', titolo: 'Accessi Google Ads di Palestra Forma', da: 'carlo', a: 'alex', azienda: 'a8', scadenza: 'ieri', stato: 'in ritardo' },
    { id: 't4', titolo: 'Fattura della prova, Palestra Forma', da: 'dre', a: 'giacomo', azienda: 'a8', scadenza: 'venerdì', stato: 'in corso' },
    { id: 't5', titolo: 'Preparare il preventivo per Studio Dentistico Riva', da: 'clara', a: 'dre', azienda: 'a2', scadenza: 'giovedì', stato: 'da fare' },
  ],
  outbound: { risposteOggi: 6, consegneOggi: 4, siSenzaAnalisi: 0, followupDovuti: 2, caselleSane: 91 },
  soldi: { canoneMese: 4200, prove: 1, inTrattativa: 4, preventiviInGiro: 1 },
}
