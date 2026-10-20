// La versione snella: le regole di chi chiamare, con dati finti.
import { describe, expect, it } from 'vitest'
import type { Decisione, Domanda, RigaLead, Telefono } from './dati'
import {
  DA_APP, FASI, NOTE_APP, allegaAnalisi, azioneApprovata, cellulareDi, cerca, chiamateInRitardo, contaStati, eSeguito, faseDi, giornoRoma, listaDaChiamare,
  messaggioInAttesa, motivoFermo, nomeGiorno, perAzienda, piuGiorni, primaRiga, quando,
  infoStato, nomeStato, prossimoMessaggio, scrittoDopo, scritturaNonMandare, scrittureChiusura, sitoBreve, sitoCliccabile, spiegaDomanda, statoDi,
  tasso, titoloDomanda, tonoStato,
  type LeadPerProssimo, type PropostaLead,
} from './regole'
import { GRUPPI, INFO_STATI, STATI } from './dati'
import statiJson from './stati.json'

const ORA = new Date('2026-10-19T08:00:00Z')          // lunedi' 19/10, le 10 a Roma

type RigaProva = RigaLead & { scheda?: { telefoni: Telefono[] } }
const CELL: Telefono = { numero: '333 0000000', tel: '+393330000000', etichetta: 'cellulare, dalla firma', tipo: 'cellulare', fonte: 'firma' }
const FISSO: Telefono = { numero: '02 0000000', tel: '+3920000000', etichetta: 'fisso, dalla firma', tipo: 'fisso', fonte: 'firma' }
const CENTRALINO: Telefono = { numero: '02 0000001', tel: '+3920000001', etichetta: 'centralino, dal sito', tipo: 'fisso', fonte: 'sito' }
function riga(id: string, cambia: Partial<RigaProva> = {}): RigaProva {
  return { prospect_id: id, azienda: `Azienda ${id}`, persona: `Persona ${id}`, email: `${id}@esempio.it`, stato: 'Da chiamare',
           ultima_risposta: '2026-10-18T09:00:00Z', frase: 'Ci sentiamo?', da_chiamare: true, perche_chiamare: 'Ha chiesto una chiamata',
           scheda: { telefoni: [CELL, FISSO] }, ...cambia }
}
function dec(id: string, cambia: Partial<Decisione> = {}): Decisione {
  return { prospect_id: id, stato: null, prossima_mossa: null, prossima_il: null, chiamata: null, chiamata_il: null,
           richiamare_il: null, tentativi: 0, ...cambia }
}

describe('chi chiamare', () => {
  it('chi vuole sentirti c\'e\', chi no non c\'e\'', () => {
    const l = listaDaChiamare([riga('a'), riga('b', { da_chiamare: false })], new Map(), ORA)
    expect(l.map((x) => x.riga.prospect_id)).toEqual(['a'])
  })
  it('Da chiamare solo con un cellulare suo (20/10 sera): solo il fisso, solo il centralino del sito o nessun numero non bastano', () => {
    const righe = [riga('a'), riga('b', { scheda: { telefoni: [FISSO] } }), riga('c', { scheda: { telefoni: [CENTRALINO] } }),
      riga('d', { scheda: { telefoni: [] } }), riga('e', { scheda: undefined }),
      riga('f', { scheda: { telefoni: [{ numero: '334 0000000', tel: '+393340000000', etichetta: 'cellulare, dal sito', tipo: 'cellulare', fonte: 'sito' }] } })]
    expect(listaDaChiamare(righe, new Map(), ORA).map((x) => x.riga.prospect_id)).toEqual(['a'])
    // il cellulare e' quello che si mostra, anche se la scheda vecchia ha solo l'etichetta
    expect(cellulareDi({ telefoni: [FISSO, CELL] })?.numero).toBe('333 0000000')
    expect(cellulareDi({ telefoni: [{ numero: '335 0000000', tel: '+393350000000', etichetta: 'cellulare, dalla scheda del Workspace' }] })?.numero).toBe('335 0000000')
    expect(cellulareDi({ telefoni: [{ numero: '336 0000000', tel: '+393360000000', etichetta: 'cellulare, dal sito' }] })).toBeNull()
    expect(cellulareDi(null)).toBeNull()
    // il gesto di Dre («richiamare il») resta anche senza cellulare: l'ha deciso lui
    const d = new Map([['b', dec('b', { chiamata: 'richiamare', chiamata_il: '2026-10-18T10:00:00Z', richiamare_il: '2026-10-19' })]])
    expect(listaDaChiamare([riga('b', { scheda: { telefoni: [FISSO] } })], d, ORA).map((x) => x.motivo)).toEqual(['richiamare'])
  })
  it('chiamato dopo la sua risposta esce; una risposta nuova dopo la chiamata lo riporta', () => {
    const d = new Map([['a', dec('a', { chiamata: 'chiamato', chiamata_il: '2026-10-18T10:00:00Z' })]])
    expect(listaDaChiamare([riga('a')], d, ORA)).toHaveLength(0)
    expect(listaDaChiamare([riga('a', { ultima_risposta: '2026-10-18T11:00:00Z' })], d, ORA)).toHaveLength(1)
  })
  it('richiamare: sparisce fino al giorno scelto, poi torna in cima', () => {
    const domani = dec('a', { chiamata: 'richiamare', chiamata_il: '2026-10-18T10:00:00Z', richiamare_il: '2026-10-20' })
    expect(listaDaChiamare([riga('a'), riga('b')], new Map([['a', domani]]), ORA).map((x) => x.riga.prospect_id)).toEqual(['b'])
    const oggi = { ...domani, richiamare_il: '2026-10-19' }
    const l = listaDaChiamare([riga('b'), riga('a', { da_chiamare: false })], new Map([['a', oggi]]), ORA)
    expect(l.map((x) => [x.riga.prospect_id, x.motivo])).toEqual([['a', 'richiamare'], ['b', 'chiamare']])
  })
  it('non risponde: resta, ma in fondo', () => {
    const d = new Map([['a', dec('a', { chiamata: 'non_risponde', chiamata_il: '2026-10-18T10:00:00Z', tentativi: 1 })]])
    const l = listaDaChiamare([riga('a', { ultima_risposta: '2026-10-17T09:00:00Z' }), riga('b')], d, ORA)
    expect(l.map((x) => [x.riga.prospect_id, x.nonRisponde])).toEqual([['b', false], ['a', true]])
  })
  it('chi Dre ha messo in Non interessato o in Call fissata non si chiama; oltre 21 giorni neanche', () => {
    const d = new Map([['a', dec('a', { stato: 'Non interessato' })], ['b', dec('b', { stato: 'Call fissata' })]])
    const vecchio = riga('c', { ultima_risposta: '2026-09-20T09:00:00Z' })
    expect(listaDaChiamare([riga('a'), riga('b'), vecchio], d, ORA)).toHaveLength(0)
  })
  it('in ritardo: chi aspetta da piu\' di un giorno senza un tentativo', () => {
    const l = listaDaChiamare([riga('a', { ultima_risposta: '2026-10-17T07:00:00Z' }), riga('b')], new Map(), ORA)
    expect(chiamateInRitardo(l, ORA).map((x) => x.riga.prospect_id)).toEqual(['a'])
  })
})

describe('lista e ricerca', () => {
  it('lo stato deciso da Dre vince su quello calcolato', () => {
    const m = contaStati([riga('a'), riga('b')], new Map([['a', dec('a', { stato: 'Analisi inviata' })]]))
    expect(m.get('Analisi inviata')).toBe(1)
    expect(m.get('Da chiamare')).toBe(1)
  })
  it('cerca per azienda o persona, senza accenti', () => {
    const r = [riga('a', { azienda: 'Caffè Rossi' }), riga('b', { persona: 'Mario Verdi' })]
    expect(cerca(r, 'caffe').map((x) => x.prospect_id)).toEqual(['a'])
    expect(cerca(r, 'mario ver').map((x) => x.prospect_id)).toEqual(['b'])
    expect(cerca(r, '  ')).toHaveLength(2)
  })
})

describe('date e numeri', () => {
  it('il giorno e\' quello di Roma, anche a mezzanotte UTC', () => {
    expect(giornoRoma(new Date('2026-10-18T22:30:00Z'))).toBe('2026-10-19')
    expect(piuGiorni('2026-10-31', 1)).toBe('2026-11-01')
  })
  it('quando, detto come una persona', () => {
    expect(quando('2026-10-19T07:31:00Z', ORA)).toBe('oggi alle 09:31')
    expect(quando('2026-10-18T16:02:00Z', ORA)).toBe('ieri alle 18:02')
    expect(nomeGiorno('2026-10-20', ORA)).toBe('Domani')
  })
  it('il tasso non si inventa', () => {
    expect(tasso(120, 1606)).toBe('7,5%')
    expect(tasso(null, 1606)).toBeNull()
    expect(tasso(3, 0)).toBeNull()
  })
  it('le domande della Posta: una riga per azienda, titolo senza codici', () => {
    const d: Domanda[] = [
      { id: 1, tipo: 'umano', titolo: 'Da guardare tu: Azienda A, INT-09', perche: null, at: '2026-10-19T07:00:00Z', prospect_id: 'a' },
      { id: 2, tipo: 'umano', titolo: 'Da guardare tu: Azienda A, INT-07', perche: null, at: '2026-10-19T07:10:00Z', prospect_id: 'a' },
      { id: 3, tipo: 'risposta', titolo: 'Bozza per Azienda B, INT-01', perche: null, at: '2026-10-18T07:00:00Z', prospect_id: 'b' },
    ]
    const g = perAzienda(d)
    expect(g.map((x) => [x.ultima.id, x.quante])).toEqual([[2, 2], [3, 1]])
    expect(titoloDomanda(g[0].ultima.titolo)).toBe('Azienda A')
    expect(titoloDomanda(g[1].ultima.titolo)).toBe('Azienda B')
  })
  it('la Posta detta senza parole interne: niente INT, FOLLOW UP doppio, seconda testa, CANCELLO', () => {
    expect(titoloDomanda('Follow up 1: Azienda C, FOLLOW UP 1')).toBe('Azienda C')
    expect(titoloDomanda('Da guardare tu: Azienda D, INT-08 ')).toBe('Azienda D')
    expect(eSeguito({ titolo: 'Azienda C, FOLLOW UP 1', intento: 'FOLLOW UP 1' })).toBe(true)
    expect(eSeguito({ titolo: 'Bozza per Azienda E, INT-01', intento: 'INT-01' })).toBe(false)
    expect(spiegaDomanda("si': la seconda testa dice INCOERENTE: non risponde alla domanda")).toBe('Il controllo ha fermato la bozza: non risponde alla domanda')
    expect(spiegaDomanda("sì: è un'autorisposta, CANCELLO: regola 3h")).toBe("È un'autorisposta")
    expect(spiegaDomanda('il template di Dre parola per parola (INT-01); va bene')).toBe('Il template di Dre parola per parola; va bene')
    expect(spiegaDomanda(null)).toBe('')
  })
  it('cosa gli abbiamo scritto dopo la sua risposta', () => {
    const filo = [
      { at: '2026-10-12T14:37:00Z', chi: 'lui' as const, testo: 'Possiamo sentirci mercoledì?' },
      { at: '2026-10-15T15:05:00Z', chi: 'noi' as const, testo: 'Buongiorno Andrea,\nmi scusi: mercoledì è passato.\nA presto' },
    ]
    const d = scrittoDopo(filo, '2026-10-12T14:37:00Z')
    expect(d?.at).toBe('2026-10-15T15:05:00Z')
    expect(primaRiga(d!.testo)).toBe('mi scusi: mercoledì è passato.')
    expect(scrittoDopo(filo, '2026-10-16T00:00:00Z')).toBeNull()
  })
})

describe('i 12 stati (Dre, 19/10)', () => {
  it('dodici, in quattro gruppi, in quest\'ordine, nient\'altro', () => {
    expect(STATI).toEqual(['Da chiamare', 'Da rispondere', 'Analisi inviata', 'Call fissata', 'Proposta inviata', 'Cliente acquisito',
      'Da ricontattare', 'Assente', 'Nessuna risposta', 'Non interessato', 'Perso', 'Non contattare'])
    expect(GRUPPI).toEqual(['Da gestire oggi', 'Opportunità', 'In attesa', 'Chiusi'])
  })
  it('ogni stato ha un responsabile e una prossima azione di default', () => {
    for (const s of INFO_STATI) {
      expect(['Dramane', 'Claude']).toContain(s.responsabile)
      expect(s.azione.trim().length).toBeGreaterThan(0)
      expect(GRUPPI).toContain(s.gruppo)
    }
    expect(infoStato('Da chiamare')?.responsabile).toBe('Dramane')
    expect(infoStato('Da rispondere')?.responsabile).toBe('Claude')
  })
  it('i nomi vecchi passano ai nuovi, mai si mostrano', () => {
    expect(nomeStato('No grazie')).toBe('Non interessato')
    expect(nomeStato('Non scrivere più')).toBe('Non contattare')
    expect(nomeStato('Fuori ufficio')).toBe('Assente')
    expect(nomeStato('Conoscitiva')).toBe('Call fissata')
    expect(nomeStato('Analisi mandata')).toBe('Analisi inviata')
    expect(nomeStato('Vuole sentirti')).toBe('Da chiamare')
    expect(nomeStato('Follow-up')).toBe('Analisi inviata')
    expect(nomeStato('Da riprendere')).toBe('Da ricontattare')
    expect(nomeStato('In conversazione')).toBe('Da rispondere')
    for (const v of Object.values(statiJson.dai_vecchi)) expect(STATI).toContain(v)
    expect(statoDi({ stato: 'Vuole sentirti' })).toBe('Da chiamare')
    expect(statoDi({ stato: 'Nel Workspace' })).toBe('Da rispondere')
  })
})

describe('il colore degli stati', () => {
  it('verde il si\', rosso il no, ambra da rispondere, blu quello che seguiamo noi, viola le opportunita\'', () => {
    expect(tonoStato('Da chiamare')).toBe('ok')
    expect(tonoStato('Cliente acquisito')).toBe('ok')
    expect(tonoStato('Da rispondere')).toBe('attesa')
    expect(tonoStato('Analisi inviata')).toBe('noi')
    expect(tonoStato('Call fissata')).toBe('opp')
    expect(tonoStato('Proposta inviata')).toBe('opp')
    expect(tonoStato('Da ricontattare')).toBe('giallo')
    expect(tonoStato('Non interessato')).toBe('no')
    expect(tonoStato('Perso')).toBe('no')
    expect(tonoStato('Non contattare')).toBe('stop')
  })
  it('grigi: assente, nessuna risposta, e uno stato che non conosce', () => {
    expect(tonoStato('Assente')).toBe('neutro')
    expect(tonoStato('Nessuna risposta')).toBe('neutro')
    expect(tonoStato('Uno stato nuovo')).toBe('neutro')
  })
})

describe('le 8 fasi del foglio della pipeline (19/10)', () => {
  it('sono otto, nell\'ordine del design, e ogni stato ha la sua fase o il suo conteggio', () => {
    expect(FASI.map((f) => f.nome)).toEqual(['Analisi in preparazione', 'Analisi inviata', 'Conversazione',
      'Chiamata conoscitiva', 'Chiamata tecnica', 'Chiamata di avvio', 'Periodo di prova', 'Cliente'])
    for (const s of STATI) expect(faseDi(s)).not.toBeNull()
  })
  it('quella del foglio vince su quella di partenza dello stato', () => {
    expect(faseDi('Da rispondere')).toEqual({ nome: 'Analisi in preparazione', dentro: true })
    expect(faseDi('Da rispondere', 'Conversazione')).toEqual({ nome: 'Conversazione', dentro: true })
    expect(faseDi('Call fissata', 'Chiamata tecnica')).toEqual({ nome: 'Chiamata tecnica', dentro: true })
    expect(faseDi('Assente')).toEqual({ nome: 'Fuori ufficio', dentro: false })
    expect(faseDi('Analisi inviata', 'Persi')).toEqual({ nome: 'Persi', dentro: false })
    expect(faseDi('Vuole sentirti')).toEqual({ nome: 'Analisi in preparazione', dentro: true })   // un nome vecchio si traduce
    expect(faseDi(null)).toBeNull()
  })
})

describe('la scheda pulita (20/10): il prossimo messaggio di Clara e il sito', () => {
  const ADESSO = new Date('2026-10-20T08:00:00Z')        // martedi' 20/10, le 10 a Roma
  const lead: LeadPerProssimo = {
    analysis_sent_at: '2026-10-19T09:00:00Z', last_reply_at: '2026-10-18T09:00:00Z', no_followup: false, fuori: false,
    stage: 'risposto', classificazione: 'positivo', coda: null, awaiting_us: false,
  }
  const proposta = (cambia: Partial<PropostaLead> = {}): PropostaLead => ({
    id: 1, tipo: 'risposta', stato: 'approvata', at: '2026-10-20T07:00:00Z', bozza: 'Salve,\n\ntorno sull\'analisi.', template: 'FOLLOW UP 1', risposta: null, ...cambia,
  })

  it('una proposta approvata: parte a minuti, col testo esatto, e si sa cosa chiudere', () => {
    const p = prossimoMessaggio(lead, [proposta()], null, [], ADESSO)
    expect(p).toMatchObject({ testo: 'Salve,\n\ntorno sull\'analisi.', tipo: 'Primo follow-up', da_chiudere: [1] })
    expect(p?.quando).toMatch(/parte a minuti/i)
  })
  it('l\'approvata vince sull\'aperta; chiuse e altri tipi non contano', () => {
    const p = prossimoMessaggio(lead, [proposta({ id: 2, stato: 'aperta', template: null, bozza: 'Altro' }), proposta({ id: 3 }),
      proposta({ id: 4, stato: 'fatta' }), proposta({ id: 5, stato: 'aperta', bozza: null, tipo: 'umano' }),
      proposta({ id: 6, stato: 'aperta', tipo: 'avanza' })], null, [], ADESSO)
    expect(p?.da_chiudere).toEqual([2, 3, 5])
    expect(p?.testo).toBe('Salve,\n\ntorno sull\'analisi.')
  })
  it('una proposta aperta: scritta, non ancora partita', () => {
    expect(prossimoMessaggio(lead, [proposta({ stato: 'aperta', template: null })], null, [], ADESSO))
      .toMatchObject({ tipo: 'Risposta', quando: 'Scritto, non ancora partito' })
  })
  it('senza proposte e senza analisi: niente', () => {
    expect(prossimoMessaggio({ ...lead, analysis_sent_at: null }, [], null, [], ADESSO)).toBeNull()
  })
  it('il calendario dei follow-up (followup.py) dice il giorno; il testo lo scrive Clara quel giorno', () => {
    const p = prossimoMessaggio(lead, [], { gruppo: 'MINI FOLLOW UP', il: '2026-10-22' }, [], ADESSO)
    expect(p).toMatchObject({ giorno: '2026-10-22', testo: null, tipo: 'Mini follow-up', da_chiudere: [] })
    expect(p?.quando).toMatch(/22/)
  })
  it('senza calendario: come followup.py, analisi + 5 giorni se non ha piu\' scritto', () => {
    expect(prossimoMessaggio(lead, [], null, [], ADESSO)).toMatchObject({ giorno: '2026-10-24', tipo: 'Primo follow-up' })
    // in ritardo: oggi, non nel passato
    expect(prossimoMessaggio({ ...lead, analysis_sent_at: '2026-10-01T09:00:00Z', last_reply_at: '2026-09-30T09:00:00Z' }, [], null, [], ADESSO)?.giorno).toBe('2026-10-20')
  })
  it('niente follow-up se ha scritto dopo l\'analisi, se e\' fermato, fuori, perso, o l\'ha gia\' avuto', () => {
    expect(prossimoMessaggio({ ...lead, last_reply_at: '2026-10-19T10:00:00Z' }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio({ ...lead, no_followup: true }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio({ ...lead, fuori: true }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio({ ...lead, stage: 'perso' }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio({ ...lead, classificazione: 'negativo' }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio(lead, [proposta({ stato: 'fatta' })], null, [], ADESSO)).toBeNull()
    // una nostra mail partita dopo il giorno dell'analisi e' gia' un follow-up
    expect(prossimoMessaggio(lead, [], null, ['2026-10-21T09:00:00Z'], ADESSO)).toBeNull()
    // un follow-up rifiutato «a mano» da Dre conta come avuto; chiuso dagli script no
    expect(prossimoMessaggio(lead, [proposta({ stato: 'no', risposta: 'NO: non serve' })], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio(lead, [proposta({ stato: 'no', risposta: 'chiusa da sola' })], null, [], ADESSO)).not.toBeNull()
  })
  it('fermato da Dre: il calendario non conta piu\'', () => {
    expect(prossimoMessaggio({ ...lead, no_followup: true }, [], { gruppo: 'FOLLOW UP 1', il: '2026-10-22' }, [], ADESSO)).toBeNull()
  })

  it('il sito si apre sempre, con o senza https', () => {
    expect(sitoCliccabile('esempio.it')).toBe('https://esempio.it')
    expect(sitoCliccabile(' www.esempio.it/ ')).toBe('https://www.esempio.it/')
    expect(sitoCliccabile('http://esempio.it')).toBe('http://esempio.it')
    expect(sitoCliccabile('HTTPS://Esempio.it')).toBe('HTTPS://Esempio.it')
    expect(sitoCliccabile('')).toBeNull()
    expect(sitoCliccabile(null)).toBeNull()
    expect(sitoCliccabile('non un sito')).toBeNull()
    expect(sitoBreve('https://www.esempio.it/')).toBe('esempio.it')
    expect(sitoBreve('https://esempio.it/chi-siamo')).toBe('esempio.it/chi-siamo')
  })
})

describe('risolvere da soli un lead fermo (20/10 sera): Manda, Non mandare, Chiudi', () => {
  const ADESSO = new Date('2026-10-20T18:00:00Z')
  const lead = { analysis_pdf: 'https://x.supabase.co/storage/v1/object/vault/analisi/a.pdf', analysis_sent_at: null as string | null }
  const p = (cambia: Partial<PropostaLead> = {}): PropostaLead => ({
    id: 1, tipo: 'umano', stato: 'aperta', at: '2026-10-20T07:00:00Z', bozza: 'Buongiorno,\n\nle rispondo.', template: 'INT-13', risposta: null,
    titolo: 'Da guardare tu: Azienda A, INT-13', perche: "si': la seconda testa dice INCOERENTE: evita la domanda (INT-13)", ...cambia,
  })

  it('il messaggio in attesa e\' la proposta aperta piu\' recente col testo; approvate, chiuse, senza testo e altri tipi no', () => {
    const a = messaggioInAttesa([p(), p({ id: 2, at: '2026-10-20T09:00:00Z', bozza: 'Più recente' }), p({ id: 3, stato: 'approvata', at: '2026-10-20T10:00:00Z' }),
      p({ id: 4, at: '2026-10-20T11:00:00Z', bozza: null }), p({ id: 5, tipo: 'avanza', at: '2026-10-20T12:00:00Z' }), p({ id: 6, stato: 'no', at: '2026-10-20T12:00:00Z' })])
    expect(a).toMatchObject({ id: 2, testo: 'Più recente', tipo: 'Risposta' })
    expect(messaggioInAttesa([p({ stato: 'approvata' })])).toBeNull()
    expect(messaggioInAttesa([])).toBeNull()
  })
  it('il motivo per cui e\' fermo, senza parole interne: il perche\', poi il controllo, poi l\'ombra, poi il titolo', () => {
    expect(motivoFermo(p())).toBe('Il controllo ha fermato la bozza: evita la domanda')
    expect(motivoFermo(p({ perche: null, motivo_controllo: 'dice «grazie» al contatto nuovo' }))).toBe('Il controllo ha fermato la bozza: dice «grazie» al contatto nuovo')
    expect(motivoFermo(p({ perche: '', motivo_controllo: '', ombra: 'in ombra: il lettore non era sicuro' }))).toBe('In ombra: il lettore non era sicuro')
    expect(motivoFermo(p({ perche: null }))).toBe('Clara non era sicura: la guardi tu.')
    expect(motivoFermo(p({ perche: null, titolo: 'Bozza per Azienda A, INT-01' }))).toBe('Aspetta un tuo sì.')
  })
  it('il prossimo messaggio sa da quale proposta viene, cosi\' la scheda non lo mostra due volte', () => {
    const lp: LeadPerProssimo = { analysis_sent_at: null, last_reply_at: '2026-10-20T06:00:00Z', no_followup: false, fuori: false, stage: 'risposto', classificazione: 'positivo', coda: null, awaiting_us: true }
    expect(prossimoMessaggio(lp, [p()], null, [], ADESSO)?.proposta).toBe(1)
  })
  it('Manda: approvata da «Dre (app)» adesso, il resto di azione intatto; l\'analisi in allegato solo se non e\' mai partita', () => {
    const az = { bozza: 'Buongiorno', intento: 'INT-13', template: 'INT-13', lettura: { coerenza: 'INCOERENTE' } }
    const dopo = azioneApprovata(az, lead, ADESSO)
    expect(dopo).toMatchObject({ ...az, approvata_da: DA_APP, approvata_il: '2026-10-20T18:00:00.000Z', allega: true })
    expect(az).not.toHaveProperty('approvata_da')
    // analisi gia' mandata: non si rimanda; bozza che la porta gia' dentro: niente doppione; senza PDF: niente
    expect(azioneApprovata(az, { ...lead, analysis_sent_at: '2026-10-19T09:00:00Z' }, ADESSO)).not.toHaveProperty('allega')
    expect(allegaAnalisi({ bozza: `ecco ${lead.analysis_pdf}` }, lead)).toBe(false)
    expect(allegaAnalisi({ bozza: 'x' }, { analysis_pdf: null, analysis_sent_at: null })).toBe(false)
    // una spunta gia' accesa resta
    expect(allegaAnalisi({ bozza: 'x', allega: true }, { analysis_pdf: null, analysis_sent_at: '2026-10-19T09:00:00Z' })).toBe(true)
  })
  it('Non mandare e Chiudi scrivono quello che poi il sistema rispetta', () => {
    expect(scritturaNonMandare(ADESSO)).toEqual({ stato: 'no', risposta: "NO: Dre dall'app", risposta_il: '2026-10-20T18:00:00.000Z' })
    const c = scrittureChiusura(ADESSO)
    expect(c.lead).toEqual({ classificazione: 'negativo', no_followup: true, coda: null })
    expect(c.decisione.stato).toBe('Non interessato')
    expect(STATI).toContain(c.decisione.stato)
    expect(c.proposte.stato).toBe('no')
    expect(c.proposte.risposta.startsWith('NO:')).toBe(true)     // un no «a mano» (prossimoMessaggio lo conta come avuto)
    // chiuso: niente follow-up da nessuna strada
    const lp: LeadPerProssimo = { analysis_sent_at: '2026-10-15T09:00:00Z', last_reply_at: '2026-10-14T09:00:00Z', fuori: false, stage: 'risposto', awaiting_us: false, ...c.lead }
    expect(prossimoMessaggio(lp, [], { gruppo: 'FOLLOW UP 1', il: '2026-10-22' }, [], ADESSO)).toBeNull()
    for (const n of Object.values(NOTE_APP)) expect(n.startsWith("Dall'app: ")).toBe(true)
  })
})
