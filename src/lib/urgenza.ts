// L'ORDINE DELLA PIPELINE (Dre, 29/9/2026): «la pipeline non può essere sempre
// piena... un modo per far sì che le cose importanti arrivino in alto e le meno
// importanti più in basso, così faccio le cose in ordine guardando dall'alto».
//
// Il numero da cui nasce: 83 aziende in pipeline, 72 ferme da più di un mese, e
// il lavoro vero di oggi erano 11 righe. Ordinate per data dell'ultima loro
// mail, un «no» di ieri stava sopra a una bozza pronta da tre giorni.
//
// Due regole, non una:
//   - il PESO decide chi sta in cima (questo file);
//   - l'ARCHIVIO decide chi esce di scena (scripts/archivio.py).
// Insieme fanno «poche righe, e le prime sono quelle giuste».
//
// LA REGOLA CHE CONTA: ogni riga sa dire PERCHÉ è dov'è. Un ordine che non si
// spiega è un ordine di cui non ci si fida, e dopo tre giorni si torna a
// scorrere tutto.

export type PerUrgenza = {
  id: string
  stage?: string | null
  pipeline_stage?: string | null
  classificazione?: string | null
  last_reply_at?: string | null
  awaiting_us?: boolean | null
  coda?: string | null
  canone?: number | string | null
  analysis_pdf?: string | null
  analysis_sent?: boolean | null
}

export type Urgenza = {
  peso: number
  perche: string          // una riga, in italiano: si mostra accanto al nome
  gruppo: 'adesso' | 'presto' | 'dopo' | 'fermo'
}

const GIORNO = 86_400_000

/** Quanti giorni fa, o null se non si sa. 29/9: prima tornava 9999 e la riga
 *  diceva «ha detto no 9999 giorni fa», che è una data inventata a schermo. */
function giorniDa(iso?: string | null): number | null {
  if (!iso) return null
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  return Math.floor((Date.now() - t) / GIORNO)
}

/** Quanto pesa una riga, e perché. Più alto = più in alto nella lista.
 *
 *  `conBozza` sono gli id delle aziende che hanno una proposta aperta in Posta:
 *  è il segnale più forte di tutti, perché è lavoro già pronto per Dre.
 */
export function urgenza(p: PerUrgenza, conBozza: Set<string>): Urgenza {
  const g = giorniDa(p.last_reply_at)
  const giorni = g ?? 9999            // per i conti: senza data vale «vecchissimo»
  const daQuando = g === null ? '' : `da ${g} giorni`
  const quandoFa = g === null ? '' : ` ${g} giorni fa`
  const classe = (p.classificazione ?? '').toLowerCase()
  const fase = (p.pipeline_stage ?? p.stage ?? '').toLowerCase()

  // 1. C'È UNA BOZZA PRONTA. È lavoro di Dre, adesso: batte tutto il resto.
  if (conBozza.has(p.id)) {
    return { peso: 1000, perche: 'bozza pronta da approvare', gruppo: 'adesso' }
  }

  // 2. QUALCUNO STA ASPETTANDO NOI. Ha scritto e non gli abbiamo risposto.
  if (p.awaiting_us) {
    return {
      peso: 900 - Math.min(giorni, 60),
      perche: g === null || g <= 1 ? 'ha scritto, aspetta una risposta' : `aspetta una risposta ${daQuando}`,
      gruppo: 'adesso',
    }
  }

  // 3. CALL FISSATA. Va preparata, e la preparazione ha una data.
  if (fase === 'call_fissata' || fase === 'conoscitiva' || fase === 'tecnica') {
    return { peso: 800, perche: 'call fissata da preparare', gruppo: 'adesso' }
  }

  // 4. CLIENTE. Il lavoro consegnato viene prima di quello da vendere.
  if (fase === 'cliente' || fase === 'prova' || fase === 'avvio') {
    const canone = Number(p.canone) || 0
    return {
      peso: 700 + Math.min(canone / 100, 50),
      perche: fase === 'prova' ? 'in prova' : 'cliente',
      gruppo: 'adesso',
    }
  }

  // 5. IN CODA PER UN RICONTATTO. Clara ci sta già lavorando.
  if (p.coda) {
    return { peso: 600, perche: `in coda: ${p.coda.toLowerCase()}`, gruppo: 'presto' }
  }

  // 6. IL POSITIVO CHE STA SCIVOLANDO VIA. Il pezzo che l'archivio da solo non
  //    risolve: 13 persone avevano detto sì ed erano ferme da oltre un mese,
  //    invisibili in mezzo a 57 rifiuti. Più tempo passa, più sale.
  if (classe === 'positivo' || classe === 'tiepido') {
    if (giorni >= 15) {
      return {
        peso: 500 + Math.min(giorni, 90),
        perche: `ha detto sì e non si sente ${daQuando}`,
        gruppo: 'presto',
      }
    }
    return { peso: 400 - giorni, perche: 'positivo, seguito di recente', gruppo: 'presto' }
  }

  // 7. RINVIO SCADUTO. Aveva detto «risentiamoci», e il momento è passato.
  if (classe === 'rinvio' && g !== null && g >= 30) {
    return { peso: 450, perche: `aveva chiesto di risentirvi, sono passati ${g} giorni`, gruppo: 'presto' }
  }

  // 8. DA CLASSIFICARE. Serve un occhio, ma non è urgente.
  if (classe === 'da_classificare' || !classe) {
    return { peso: 300, perche: 'da classificare', gruppo: 'dopo' }
  }

  // 9. I NO. In fondo, e più sono vecchi più scendono.
  if (classe === 'negativo') {
    return {
      peso: 100 - Math.min(giorni, 99),
      perche: g !== null && g >= 30 ? `ha detto no${quandoFa}` : 'ha detto no',
      gruppo: giorni >= 30 ? 'fermo' : 'dopo',
    }
  }

  // 10. tutto il resto: fuori target, soppressi, chi non ha mai risposto.
  return { peso: 50 - Math.min(giorni, 49), perche: classe || 'nessuna risposta', gruppo: 'fermo' }
}

/** Ordina una lista dalla più urgente alla meno, a parità di peso la più recente. */
export function perUrgenza<T extends PerUrgenza>(righe: T[], conBozza: Set<string>): T[] {
  return [...righe].sort((a, b) => {
    const ua = urgenza(a, conBozza).peso
    const ub = urgenza(b, conBozza).peso
    if (ua !== ub) return ub - ua
    return (b.last_reply_at ?? '').localeCompare(a.last_reply_at ?? '')
  })
}
