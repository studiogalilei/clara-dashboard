// IL COME-SI-USA DI OGNI SCHERMATA (Dre, 5/10: «aggiungere dei tutorial su
// TUTTE le funzioni»). Un posto solo per i testi: il bottone «?» (Aiuto.tsx)
// li apre sulla schermata giusta. Ogni voce racconta il workflow, non i
// bottoni: chi arriva qui, cosa decide, dove va a finire.

export interface Guida {
  titolo: string
  passi: string[]
}

export const AIUTI: Record<string, Guida> = {
  oggi: {
    titolo: 'La tua giornata',
    passi: [
      'In alto c’è quello che aspetta te: bozze da approvare, domande di Clara, call di oggi. Si lavora dall’alto in basso.',
      'Ogni riga porta dove si agisce: click e sei sul punto.',
      'Sotto ci sono le tue task; a destra, quello che arriva dagli altri.',
      'Quando la colonna di sinistra è vuota, la giornata è coperta: il resto corre da solo.',
    ],
  },
  conversazioni: {
    titolo: 'La posta di Clara',
    passi: [
      'Chi risponde alle campagne riceve la prima consegna da sola: qui arrivano solo le conversazioni che chiedono te.',
      'In cima sta chi aspetta da più tempo, col perché in una riga.',
      'Apri, leggi il filo a bolle, e decidi lì: Approva e manda, oppure Lascia stare.',
      'In «Decisioni» stanno le cose tecniche: classificazioni, date, richieste.',
      'Il battito, nella chat, ti dice due volte al giorno se tutto corre.',
    ],
  },
  aziende: {
    titolo: 'Le aziende',
    passi: [
      'La bacheca è il viaggio: ogni colonna una tappa, dalla risposta alla firma.',
      'Si apre un’azienda e si fa tutto dal pannello: avanzare, segnare una call, perdere con un motivo.',
      'Avanzare chiede il riassunto della call: è la memoria che ti serve alla prossima.',
      'Un’azienda ferma si vede dal «fermo da»: quelle vanno mosse o lasciate andare.',
    ],
  },
  preventivi: {
    titolo: 'I preventivi',
    passi: [
      'Si parte dalla call tecnica fatta: qui nasce il preventivo per quella azienda.',
      '«+ Riga» aggiunge una voce dal listino; il totale si fa da solo.',
      'Quando è pronto si manda e si segna la data: da lì parte il conto dei giorni.',
      'Accettato, l’azienda avanza ad Avvio; rifiutato, si scrive il motivo e resta nella storia.',
    ],
  },
  calendario: {
    titolo: 'Il calendario',
    passi: [
      'Le call prenotate arrivano qui da sole, col nome dell’azienda davanti.',
      'Prima della call: la preparazione sta nella scheda dell’azienda.',
      'Dopo la call: si avanza dalla scheda, col riassunto. È quello che muove la pipeline.',
    ],
  },
  metro: {
    titolo: 'Gli esami',
    passi: [
      'Un caso vero alla volta: leggi cosa ha scritto la persona e rispondi come risponderesti tu.',
      'Il commento libero vale quanto la risposta: è lì che insegni il perché.',
      'Le tue risposte diventano regole e esempi: le bozze di Clara imparano da qui.',
    ],
  },
  numeri: {
    titolo: 'I numeri',
    passi: [
      'Il polso in alto dice chi aspetta una risposta adesso: verde promessa tenuta, rosso coi nomi.',
      'Le prenotazioni degli ultimi 30 giorni dicono se l’outbound porta call.',
      'Il resto si legge una volta a settimana, non ogni ora.',
    ],
  },
}
