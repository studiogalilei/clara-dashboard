import { useEffect, useMemo, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Spinner, Micro, sgid, fmtDateShort, Faccia, type FacciaP } from './ui'
import CercaAzienda, { CAMPI_AZIENDA } from './CercaAzienda'
import Editor from './Editor'
import Prezzo from './Prezzo'
import { MODELLI } from '../lib/modelli'
import { creaTask, giorno } from '../lib/regole'
import { apriFile } from '../lib/file'
import { LINEA_NOME, controllaTono, ripulisciTono, testoDi } from '../lib/tono'
import { cosaManca } from '../lib/condizioni'
import { datiStudio, mancaStudio, scriviStudio, STUDIO_VUOTO, type DatiStudio } from '../lib/studio'
import {
  alMese, unaTantum, lineaDi, prossimoNumero, titoloDi, documentoDi, generaEArchivia, scaduto,
  type Preventivo, type Voce, type VoceListino, type Fatturazione,
} from '../lib/preventivo'

// I PREVENTIVI (Dre, 14/9): si crea in modo smooth, esce un PDF secondo il
// brand, si segna inviato, accettato o rifiutato, e si vede cosa gira e per
// chi. Collegato all'azienda (scheda, cartella Documenti), ai progetti
// (accettato = nasce il progetto) e a Stripe (pagato lo scrive Clara).
// Lo vedono Dre e Giacomo: la regola e' nel database (ruolo ceo).

interface Props { onOpen: (id: string) => void }
type Nome = FacciaP & { id: string; email: string; fatturazione: Fatturazione | null }
const comeNome = (a: { id: string }) => a as unknown as Nome
const CAMPI = CAMPI_AZIENDA
const nomeAzienda = (a: Nome) => a.company || a.name || a.email
type Filtro = 'giro' | 'tutti' | 'accettati' | 'pagati' | 'rifiutati' | 'bozze'

interface Incasso {
  id: string; genere: 'addebito' | 'fattura' | 'abbonamento'; importo: number; valuta: string; stato: string | null
  quando: string | null; ricorrenza: string | null; cliente_nome: string | null; cliente_email: string | null
  descrizione: string | null; prospect_id: string | null; preventivo_id: number | null
}
const GENERE: Record<Incasso['genere'], string> = { addebito: 'Pagamento', fattura: 'Fattura', abbonamento: 'Abbonamento' }
function tonoStato(s: string | null) {
  // il fondo resta bianco, il colore sta nel punto (Dre, 16/9)
  if (s === 'succeeded' || s === 'paid' || s === 'active' || s === 'trialing') return 'bg-green-600'
  if (s === 'failed' || s === 'canceled' || s === 'incomplete_expired' || s === 'unpaid') return 'bg-red-600'
  return 'bg-spento'
}
function statoIt(s: string | null) {
  return ({ succeeded: 'riuscito', paid: 'pagata', open: 'aperta', active: 'attivo', trialing: 'in prova', canceled: 'cancellato',
    failed: 'fallito', incomplete: 'incompleto', incomplete_expired: 'scaduto', past_due: 'in ritardo', unpaid: 'non pagato' } as Record<string, string>)[s ?? ''] ?? (s ?? '')
}

const oggi = () => giorno()
const fraGiorni = (n: number) => giorno(new Date(Date.now() + n * 86400e3))
const euro = (n: number | null | undefined) => n == null ? '' : `${Number(n).toLocaleString('it-IT')} €`

// quello che si scrive nel pannello, prima di diventare una riga
interface Bozza {
  id: number | null
  prospect_id: string
  voci: Voce[]
  valido_fino: string
  note: string
  fatturazione: Fatturazione
}
const vuota = (): Bozza => ({ id: null, prospect_id: '', voci: [], valido_fino: fraGiorni(30), note: '', fatturazione: {} })

// I DOCUMENTI (Dre, 16/9): «un luogo dove vengo, vedo, e clicco un + per
// crearne uno nuovo». Il preventivo e' uno dei documenti, non una cosa a
// parte: qui sopra c'e' il foglio bianco con i modelli, sotto i soldi.
interface DocRiga {
  id: number; prospect_id: string | null; modello: string; titolo: string
  stato: string; aggiornato_il: string
}

export default function Preventivi({ onOpen }: Props) {
  const [righe, setRighe] = useState<Preventivo[] | null>(null)
  const [documenti, setDocumenti] = useState<DocRiga[] | null>(null)
  const [apro, setApro] = useState<{ id: number | null; modello: string } | null>(null)
  const [scelgoModello, setScelgoModello] = useState(false)
  const [nomi, setNomi] = useState<Record<string, Nome>>({})
  const [listino, setListino] = useState<VoceListino[]>([])
  const [incassi, setIncassi] = useState<Incasso[] | null>(null)
  const [filtro, setFiltro] = useState<Filtro>('giro')
  const [cerca, setCerca] = useState('')
  const [bozza, setBozza] = useState<Bozza | null>(null)
  const [lavoro, setLavoro] = useState<string | null>(null)       // «Genero il PDF…»
  const [problema, setProblema] = useState<string | null>(null)
  // il toast puo' portarsi dietro il PDF appena fatto: si apre da li'
  const [toast, setToast] = useState<{ testo: string; apri?: Preventivo } | null>(null)
  const [chiedo, setChiedo] = useState<{ id: number; cosa: 'rifiuto' | 'link' } | null>(null)
  const [testoChiesto, setTestoChiesto] = useState('')
  const [studio, setStudio] = useState<DatiStudio>(STUDIO_VUOTO)
  const [studioAperto, setStudioAperto] = useState(false)
  const [studioChiesto, setStudioChiesto] = useState(false)
  const [menu, setMenu] = useState<number | null>(null)   // i tre puntini di una riga
  const [incassiAperti, setIncassiAperti] = useState(false)
  // una domanda di conferma dentro la pagina, non il popup del browser
  const [conferma, setConferma] = useState<{ testo: string; fai: () => void } | null>(null)
  // i dati fiscali presi dal registro europeo: si dichiara, non si nasconde
  const [dallaPiva, setDallaPiva] = useState<string | null>(null)
  // il lucchetto: due clic ravvicinati su «Genera il PDF» facevano due
  // preventivi con due numeri per la stessa trattativa (QA Dre, 15/9)
  const sto = useRef(false)

  useEffect(() => {
    void supabase.from('documenti').select('id,prospect_id,modello,titolo,stato,aggiornato_il')
      .order('aggiornato_il', { ascending: false }).limit(200)
      .then(({ data }) => setDocumenti((data as DocRiga[] | null) ?? []))
    void supabase.from('preventivi').select('*').order('creato_il', { ascending: false }).limit(2000)
      .then(({ data, error }) => { if (error) setProblema(error.message); setRighe((data as Preventivo[]) ?? []) })
    void supabase.from('listino').select('*').eq('attivo', true).order('ordine')
      .then(({ data, error }) => { if (error) setProblema(`Il listino non si carica: ${error.message}`); setListino((data as VoceListino[]) ?? []) })
    void datiStudio().then((d) => {
      setStudio(d)
      // la prima volta in assoluto i dati dello Studio non ci sono: si
      // chiedono subito e una volta sola, invece di bloccare il primo
      // preventivo di un cliente con un messaggio in fondo al pannello
      if (mancaStudio(d).length) { setStudioAperto(true); setStudioChiesto(true) }
    })
    void supabase.from('incassi').select('*').order('quando', { ascending: false }).limit(500)
      .then(({ data, error }) => { if (!error && data && data.length) setIncassi(data as Incasso[]) })
  }, [])

  // i nomi: solo le aziende che compaiono davvero in questa pagina
  useEffect(() => {
    const ids = [...new Set([
      ...(righe ?? []).map((q) => q.prospect_id),
      ...(incassi ?? []).map((i) => i.prospect_id).filter(Boolean) as string[],
    ])]
    setNomi((m) => {
      const mancanti = ids.filter((id) => id && !m[id])
      if (mancanti.length) {
        void supabase.from('prospects').select(CAMPI).in('id', mancanti).limit(1000)
          .then(({ data }) => setNomi((x) => {
            const out = { ...x }
            for (const a of ((data as Nome[]) ?? [])) out[a.id] = a
            return out
          }))
      }
      return m
    })
  }, [righe, incassi])

  // arrivo dalla scheda di un'azienda: il pannello si apre gia' su di lei.
  // Vale sia quando il widget non era montato (l'azienda aspetta in
  // sessionStorage) sia quando lo era gia' (l'evento), se no il secondo
  // «+ Nuovo preventivo» non apriva niente (QA Dre, 14/9).
  useEffect(() => {
    const apri = (id: string | null) => {
      try { sessionStorage.removeItem('preventivo:nuovo') } catch { /* niente */ }
      if (!id) return
      void supabase.from('prospects').select(CAMPI).eq('id', id).single().then(({ data }) => {
        const a = data as Nome | null
        if (!a) return
        setNomi((m) => ({ ...m, [a.id]: a }))
        setBozza({ ...vuota(), prospect_id: a.id, fatturazione: a.fatturazione ?? { ragione: a.company ?? '' } })
      })
    }
    let iniziale: string | null = null
    try { iniziale = sessionStorage.getItem('preventivo:nuovo') } catch { /* niente */ }
    if (iniziale) apri(iniziale)
    const ascolta = (e: Event) => apri((e as CustomEvent<string>).detail ?? null)
    window.addEventListener('preventivo:nuovo', ascolta)
    return () => window.removeEventListener('preventivo:nuovo', ascolta)
  }, [])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), toast.apri ? 9000 : 2800)
    return () => clearTimeout(t)
  }, [toast])

  const nomeDi = (id: string) => { const n = nomi[id]; return n ? nomeAzienda(n) : '…' }
  const avvisa = (testo: string) => setToast({ testo })

  async function scrivi(id: number, patch: Partial<Preventivo>): Promise<Preventivo | null> {
    const { data, error } = await supabase.from('preventivi').update({ ...patch, aggiornato_il: new Date().toISOString() }).eq('id', id).select().single()
    if (error) { setProblema(`Non ho potuto salvare: ${error.message}`); return null }
    setRighe((v) => v!.map((q) => (q.id === id ? (data as Preventivo) : q)))
    return data as Preventivo
  }

  // ── il pannello: nuovo o modifica ─────────────────────────────────────
  function apriNuovo(prospect_id = '') {
    setDallaPiva(null)
    const n = nomi[prospect_id]
    setBozza({ ...vuota(), prospect_id, fatturazione: n?.fatturazione ?? (n ? { ragione: n.company ?? '' } : {}) })
  }
  function apriModifica(q: Preventivo) {
    const n = nomi[q.prospect_id]
    setBozza({ id: q.id, prospect_id: q.prospect_id, voci: q.voci ?? [], valido_fino: q.valido_fino ?? fraGiorni(30), note: q.note ?? '', fatturazione: n?.fatturazione ?? { ragione: n?.company ?? '' } })
  }
  // LA PARTITA IVA CHE SI COMPILA DA SOLA (15/9). Ragione sociale e sede
  // sono dati pubblici: si chiedono al registro europeo invece di farli
  // battere a mano. Si riempiono solo i campi vuoti, e si dice da dove
  // arrivano, cosi' restano correggibili.
  async function cercaPiva(grezzo: string) {
    const t = grezzo.replace(/[^A-Za-z0-9]/g, '')
    if (t.length < 8) return
    try {
      const r = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/piva?p=${encodeURIComponent(t)}`, {
        headers: { Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_ANON_KEY}` },
      })
      const d = await r.json() as { trovata: boolean; ragione?: string; indirizzo?: string }
      if (!d.trovata) return
      setBozza((b) => {
        if (!b) return b
        const f = { ...b.fatturazione }
        if (!f.ragione?.trim() && d.ragione) f.ragione = d.ragione
        if (!f.indirizzo?.trim() && d.indirizzo) f.indirizzo = d.indirizzo
        return { ...b, fatturazione: f }
      })
      setDallaPiva(d.ragione ?? null)
    } catch { /* il registro non risponde: si scrive a mano, come prima */ }
  }

  function scegliAzienda(a: Nome) {
    setNomi((m) => ({ ...m, [a.id]: a }))
    setBozza((b) => b && ({ ...b, prospect_id: a.id, fatturazione: a.fatturazione ?? { ragione: a.company ?? '' } }))
  }
  // il pannello a meta' non si butta: se ci sono voci, si chiede
  function chiudiBozza() {
    if (bozza && bozza.voci.length > 0) {
      setConferma({ testo: 'Butto via questo preventivo a metà?', fai: () => setBozza(null) })
      return
    }
    setBozza(null)
  }
  function aggiungiVoce(v: VoceListino) {
    setBozza((b) => b && ({ ...b, voci: [...b.voci, { nome: v.nome, descrizione: v.descrizione ?? undefined, quantita: 1, prezzo: Number(v.prezzo), ricorrenza: v.ricorrenza }] }))
  }
  function cambiaVoce(i: number, patch: Partial<Voce>) {
    setBozza((b) => b && ({ ...b, voci: b.voci.map((v, k) => (k === i ? { ...v, ...patch } : v)) }))
  }

  // salva la bozza (riga + dati di fatturazione sull'azienda) e, se chiesto, genera il PDF
  async function salva(conPdf: boolean) {
    if (!bozza || sto.current) return
    if (!bozza.prospect_id) { setProblema('Scegli l\'azienda prima.'); return }
    if (bozza.voci.length === 0) { setProblema('Un preventivo senza voci non è un preventivo.'); return }
    if (bozza.voci.some((v) => !v.nome.trim())) { setProblema('Ogni voce ha un nome.'); return }
    // un preventivo a zero euro non e' un preventivo: in listino c'e' una
    // voce senza prezzo e finiva in un contratto cosi' com'era (QA Dre, 15/9)
    if (unaTantum(bozza.voci) + alMese(bozza.voci) <= 0) { setProblema('Metti un prezzo: questo preventivo vale zero euro.'); return }
    // il PDF e' un documento intestato: senza i dati veri non esce (mai «[da verificare]» a un cliente)
    const buchi = conPdf ? [...cosaManca(bozza.fatturazione), ...mancaStudio(studio)] : []
    if (buchi.length) { setProblema(`Per il PDF serve ${buchi.join(', ')}.`); setStudioAperto(buchi.some((b) => b.includes('Studio'))); return }
    // i segni vietati si correggono da soli; se resta una parola vietata si
    // dice in quale voce sta, non «il testo non passa il controllo»
    const voci = bozza.voci.map((v) => ({
      ...v,
      nome: ripulisciTono(v.nome),
      descrizione: v.descrizione ? ripulisciTono(v.descrizione) : v.descrizione,
      prezzo: Math.max(0, Number(v.prezzo) || 0),
    }))
    if (conPdf) {
      for (const v of voci) {
        const suoi = [...controllaTono(v.nome), ...controllaTono(v.descrizione ?? '')]
        if (suoi.length) { setProblema(`Nella voce «${v.nome}»: ${suoi.join(', ')}. Riscrivila e riprova.`); return }
      }
    }
    sto.current = true
    setLavoro(conPdf ? 'Salvo e genero il PDF…' : 'Salvo…')
    try {
      const linea = lineaDi(voci, listino)
      const base = {
        prospect_id: bozza.prospect_id, linea, voci, titolo: titoloDi(voci),
        importo: unaTantum(voci), mensile: alMese(voci) || null, valido_fino: bozza.valido_fino || null,
        note: bozza.note || null, aggiornato_il: new Date().toISOString(),
      }
      let riga: Preventivo
      if (bozza.id) {
        // se cambiando le voci cambia la linea, il numero la segue (SG-SW-… non resta SG-MK-…)
        const vecchio = righe?.find((x) => x.id === bozza.id)
        const numero = vecchio && vecchio.stato === 'bozza' && vecchio.linea !== linea ? await prossimoNumero(linea) : undefined
        const { data, error } = await supabase.from('preventivi').update(numero ? { ...base, numero } : base).eq('id', bozza.id).select().single()
        if (error) throw new Error(error.message)
        riga = data as Preventivo
      } else {
        const numero = await prossimoNumero(linea)
        const { data: sess } = await supabase.auth.getSession()
        const { data, error } = await supabase.from('preventivi').insert({ ...base, numero, stato: 'bozza', owner: sess.session?.user?.id ?? null }).select().single()
        if (error) throw new Error(error.message)
        riga = data as Preventivo
        // la riga nel database ora esiste: il pannello se ne ricorda subito,
        // se no un PDF fallito e un secondo tentativo facevano un doppione
        setBozza((b) => b && ({ ...b, id: riga.id, voci }))
        setRighe((v) => [riga, ...(v ?? [])])
      }
      // i dati di fatturazione restano sull'azienda: servono anche a Giacomo
      const f = bozza.fatturazione
      if (f.ragione || f.indirizzo || f.piva || f.pec || f.sdi) {
        await supabase.from('prospects').update({ fatturazione: f }).eq('id', bozza.prospect_id)
        setNomi((m) => ({ ...m, [bozza.prospect_id]: { ...m[bozza.prospect_id], fatturazione: f } }))
      }
      if (conPdf) {
        const doc = documentoDi(riga, nomeDi(riga.prospect_id), f, riga.linea ?? 'marketing', studio)
        const tono = controllaTono(testoDi(doc))
        if (tono.length) throw new Error(`Il testo non passa il controllo del tono: ${tono.join(', ')}`)
        const { path } = await generaEArchivia(riga, nomeDi(riga.prospect_id), f)
        const { data } = await supabase.from('preventivi').update({ pdf_path: path }).eq('id', riga.id).select().single()
        if (data) riga = data as Preventivo
      }
      setRighe((v) => { const l = (v ?? []).filter((q) => q.id !== riga.id); return [riga, ...l] })
      setBozza(null)
      // niente apertura automatica: dopo tre await Safari la blocca come
      // popup e il PDF non si vedeva (QA Dre, 14/9). Il bottone sta nel toast.
      setToast(conPdf
        ? { testo: `${riga.numero}: PDF pronto, nella cartella di ${nomeDi(riga.prospect_id)}`, apri: riga }
        : { testo: `${riga.numero} salvato come bozza` })
    } catch (e) {
      const m = (e as Error).message
      setProblema(m.includes('idx_preventivi_numero')
        ? 'Quel numero l\'ha appena preso un altro preventivo: ripremi Salva e ne prende uno nuovo.'
        : m)
    } finally {
      sto.current = false
      setLavoro(null)
    }
  }

  // un incasso che Clara non ha riconosciuto (nome diverso, gmail): lo colleghi tu
  async function collega(incassoId: string, prospectId: string) {
    if (!prospectId) return
    const { error } = await supabase.from('incassi').update({ prospect_id: prospectId }).eq('id', incassoId)
    if (error) { setProblema(error.message); return }
    setIncassi((v) => (v ?? []).map((i) => (i.id === incassoId ? { ...i, prospect_id: prospectId } : i)))
    avvisa(`Incasso collegato a ${nomeDi(prospectId)}`)
  }

  async function apri(q: Preventivo) {
    if (!q.pdf_path) return
    if (!(await apriFile(q.pdf_path))) setProblema('Il PDF non si apre: rigeneralo dal preventivo')
  }

  // ── gli esiti: inviato, accettato (nasce il progetto), rifiutato, pagato ──
  async function segnaInviato(q: Preventivo) {
    if (!q.pdf_path) {
      setConferma({ testo: `${q.numero} non ha ancora il PDF. Lo segno mandato lo stesso?`, fai: () => void inviato(q) })
      return
    }
    await inviato(q)
  }
  async function inviato(q: Preventivo) {
    const r = await scrivi(q.id, { stato: 'inviato', inviato_il: q.inviato_il ?? oggi() })
    if (r) avvisa(`${q.numero} segnato mandato`)
  }
  // prima di scrivere quattro cose nel database si dice quali sono: e' la
  // stessa regola di Clara («propone, non scrive di nascosto»), applicata a
  // un bottone umano (rapporto attriti, 15/9)
  function chiediAccettato(q: Preventivo) {
    const pilota = q.voci?.some((v) => /pilota|prova/i.test(v.nome))
    const cose = [
      q.progetto_id ? null : `nasce il progetto «${q.titolo ?? 'senza nome'}»`,
      q.mensile ? `il canone diventa ${euro(q.mensile)} al mese` : null,
      pilota ? 'parte come prova' : null,
      'una task per fissare la call di avvio',
    ].filter(Boolean)
    setConferma({
      testo: `${nomeDi(q.prospect_id)} ha accettato ${q.numero}: ${cose.join(', ')}.`,
      fai: () => void segnaAccettato(q),
    })
  }

  async function segnaAccettato(q: Preventivo) {
    const r = await scrivi(q.id, { stato: 'accettato', accettato_il: oggi() })
    if (!r) return
    let messaggio = `${q.numero} accettato`
    // il progetto: se ce n'e' gia' uno con lo stesso nome ci si aggancia, non se ne fa un altro
    if (!q.progetto_id) {
      const tipo = q.voci?.some((v) => /pilota|prova/i.test(v.nome)) ? 'trial' : q.mensile ? 'retainer' : null
      const { data: suoi } = await supabase.from('progetti').select('id,nome').eq('prospect_id', q.prospect_id).neq('stato', 'consegnato')
      const gia = (suoi as Array<{ id: number; nome: string }> | null)?.find((g) => g.nome.trim().toLowerCase() === (q.titolo ?? '').trim().toLowerCase())
      if (gia) { await scrivi(q.id, { progetto_id: gia.id }); messaggio += ', agganciato al progetto che c\'era' }
      else {
        const { data: g } = await supabase.from('progetti').insert({
          prospect_id: q.prospect_id, nome: q.titolo ?? 'Progetto', valore: q.importo ?? 0, stato: 'da_iniziare', tipo,
          data_inizio: oggi(), note: `Dal preventivo ${q.numero}`,
        }).select('id').single()
        if (g) { await scrivi(q.id, { progetto_id: g.id }); messaggio += ', progetto creato' }
      }
    }
    // il canone del cliente e' quello che ha appena accettato: una verita' sola
    if (q.mensile) {
      await supabase.from('prospects').update({ canone: q.mensile }).eq('id', q.prospect_id)
      messaggio += `, canone ${euro(q.mensile)} al mese`
    }
    // e la call di avvio va fissata: una task in cima alla lista
    const { task } = await creaTask({ titolo: `Fissare la call di avvio con ${nomeDi(q.prospect_id)}`, prospect_id: q.prospect_id, scadenza: fraGiorni(3) })
    if (task) messaggio += ', task per la call di avvio'
    avvisa(messaggio)
  }
  async function segnaRifiutato(q: Preventivo, motivo: string) {
    const r = await scrivi(q.id, { stato: 'rifiutato', rifiutato_il: oggi(), motivo: motivo || null })
    if (r) avvisa(`${q.numero} segnato rifiutato`)
  }
  async function segnaPagato(q: Preventivo) {
    const r = await scrivi(q.id, { pagato_il: oggi(), note: [q.note, 'segnato a mano'].filter(Boolean).join(', ') })
    if (r) avvisa(`${q.numero} pagato`)
  }
  async function riapri(q: Preventivo) {
    const r = await scrivi(q.id, { stato: 'inviato', accettato_il: null, rifiutato_il: null, motivo: null })
    if (r) avvisa(`${q.numero} di nuovo in attesa`)
  }
  async function copiaLink(q: Preventivo) {
    if (!q.link_pagamento) {
      setChiedo({ id: q.id, cosa: 'link' })
      // il link l'hai appena copiato da Stripe: se e' negli appunti, e' gia'
      // nel campo e ti resta solo Invio
      let dagliAppunti = ''
      try {
        const t = (await navigator.clipboard.readText()).trim()
        if (/^https:\/\/(buy\.)?stripe\.com\/|^https:\/\/buy\.stripe\.com\//.test(t)) dagliAppunti = t
      } catch { /* niente permesso, pazienza */ }
      setTestoChiesto(dagliAppunti)
      return
    }
    try { await navigator.clipboard.writeText(q.link_pagamento); avvisa('Link di pagamento copiato') } catch { setProblema('Non riesco a copiare') }
  }
  function elimina(q: Preventivo) {
    if (q.stato !== 'bozza') { setProblema('Si elimina solo una bozza: un preventivo mandato resta, semmai si segna rifiutato.'); return }
    setConferma({
      testo: `Elimino la bozza ${q.numero}?`,
      fai: async () => {
        const { error } = await supabase.from('preventivi').delete().eq('id', q.id)
        if (error) { setProblema(error.message); return }
        setRighe((v) => v!.filter((x) => x.id !== q.id))
      },
    })
  }

  // ── la lista ───────────────────────────────────────────────────────────
  const t = cerca.trim().toLowerCase()
  const visibili = useMemo(() => (righe ?? []).filter((q) => {
    if (filtro === 'giro' && !(q.stato === 'inviato')) return false
    if (filtro === 'accettati' && !(q.stato === 'accettato' && !q.pagato_il)) return false
    if (filtro === 'pagati' && !q.pagato_il) return false
    if (filtro === 'rifiutati' && q.stato !== 'rifiutato') return false
    if (filtro === 'bozze' && q.stato !== 'bozza') return false
    if (!t) return true
    const n = nomi[q.prospect_id]
    return (q.numero ?? '').toLowerCase().includes(t) || (q.titolo ?? '').toLowerCase().includes(t)
      || nomeDi(q.prospect_id).toLowerCase().includes(t) || (sgid(n?.sg_id, n) ?? '').toLowerCase().includes(t)
  }), [righe, filtro, t, nomi])   // eslint-disable-line react-hooks/exhaustive-deps

  if (righe === null) return <Spinner />

  // i buchi che fermano il PDF: si vedono prima di premere, non dopo, e
  // divisi per chi sono (prima «la partita IVA» compariva due volte nella
  // stessa frase, una per il cliente e una per lo Studio)
  const buchiCliente = bozza ? cosaManca(bozza.fatturazione) : []
  const buchiStudio = bozza ? mancaStudio(studio) : []
  const manca = [...buchiCliente, ...buchiStudio]

  const somma = (l: Preventivo[]) => l.reduce((s, q) => s + (Number(q.importo) || 0), 0)
  const inGiro = righe.filter((q) => q.stato === 'inviato')
  const scaduti = inGiro.filter(scaduto)
  const daIncassare = righe.filter((q) => q.stato === 'accettato' && !q.pagato_il)
  const incassati = righe.filter((q) => q.pagato_il)
  // sotto l'euro sono le prove fatte da noi: non sono incassi
  const veri = (incassi ?? []).filter((i) => i.importo >= 1)
  const senzaAzienda = veri.filter((i) => !i.prospect_id).length
  const abbonamenti = veri.filter((i) => i.genere === 'abbonamento' && (i.stato === 'active' || i.stato === 'trialing'))
  const mensile = abbonamenti.reduce((s, i) => s + (i.ricorrenza === 'year' ? i.importo / 12 : i.importo), 0)

  // IL PROSSIMO PASSO (Dre, 15/9): su ogni riga un'azione sola, quella che
  // faresti adesso. Il resto sta sotto i tre puntini. Prima erano sei
  // bottoni uguali in fila e non si capiva cosa fare.
  function prossimoPasso(q: Preventivo): { testo: string; fai: () => void; tono: string } | null {
    if (q.stato === 'bozza' && !q.pdf_path) return { testo: 'Genera il PDF', fai: () => apriModifica(q), tono: 'bg-blu hover:bg-blu-scuro' }
    if (q.stato === 'bozza') return { testo: 'Segna mandato', fai: () => void segnaInviato(q), tono: 'bg-navy hover:bg-blu' }
    if (q.stato === 'inviato') return { testo: 'Ha accettato', fai: () => chiediAccettato(q), tono: 'bg-green-700 hover:bg-green-800' }
    if (q.stato === 'accettato' && !q.pagato_il) return { testo: 'Segna pagato', fai: () => void segnaPagato(q), tono: 'bg-green-700 hover:bg-green-800' }
    return null
  }

  // lo stato in una riga, come sulle carte della Pipeline: un pallino e una
  // frase, non un'etichetta colorata che compete col nome del cliente
  function statoRiga(q: Preventivo): { testo: string; pallino: string; testo_colore: string } {
    if (q.pagato_il) return { testo: `Pagato il ${fmtDateShort(q.pagato_il)}`, pallino: 'bg-green-600', testo_colore: 'text-green-800' }
    if (q.stato === 'rifiutato') return { testo: `Ha detto no${q.motivo ? `: ${q.motivo}` : ''}`, pallino: 'bg-gray-300', testo_colore: 'text-spento' }
    if (q.stato === 'accettato') return { testo: `Accettato il ${fmtDateShort(q.accettato_il)}, da incassare`, pallino: 'bg-amber-500', testo_colore: 'text-amber-800' }
    if (q.stato === 'inviato') {
      if (scaduto(q)) return { testo: `Scaduto il ${fmtDateShort(q.valido_fino)}, nessuna risposta`, pallino: 'bg-amber-500', testo_colore: 'font-semibold text-amber-800' }
      const g = q.inviato_il ? Math.max(0, Math.round((Date.now() - new Date(`${q.inviato_il}T12:00:00`).getTime()) / 86400e3)) : null
      return {
        testo: `Mandato il ${fmtDateShort(q.inviato_il)}${g && g > 1 ? `, aspetta da ${g} giorni` : ''}`,
        pallino: 'bg-sky-500', testo_colore: 'text-tenue',
      }
    }
    return { testo: q.pdf_path ? 'Bozza, il PDF è pronto' : 'Bozza, senza PDF', pallino: 'bg-gray-300', testo_colore: 'text-spento' }
  }

  // l'editor prende tutta la pagina: quando scrivi un documento, scrivi e basta
  if (apro) {
    return (
      <Editor
        id={apro.id}
        modello={apro.modello}
        onEsci={() => {
          setApro(null)
          void supabase.from('documenti').select('id,prospect_id,modello,titolo,stato,aggiornato_il')
            .order('aggiornato_il', { ascending: false }).limit(200)
            .then(({ data }) => setDocumenti((data as DocRiga[] | null) ?? []))
        }}
      />
    )
  }

  return (
    <div className="space-y-4 pb-24 sm:pb-8">
      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 rounded-full px-2 py-1.5 text-xs font-bold text-red-600 hover:text-red-900">Chiudi</button>
        </div>
      )}

      {/* I DATI DELLO STUDIO: la controparte del documento. Si scrivono una volta */}
      {studioAperto && (
        <Card className="salta-su space-y-3 border-blu/40 p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="text-base font-extrabold">
              Dati dello Studio
              {studioChiesto && <span className="ml-2 text-sm font-semibold text-tenue">vanno in ogni PDF, si scrivono una volta</span>}
            </h2>
            <button onClick={() => setStudioAperto(false)} className="text-xs font-semibold text-spento hover:text-inchiostro">Chiudi</button>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {([['ragione', 'Ragione sociale'], ['piva', 'Partita IVA'], ['indirizzo', 'Sede'], ['pec', 'PEC'], ['iban', 'IBAN'], ['firmatario', 'Chi firma'], ['foro', 'Foro competente']] as Array<[keyof DatiStudio, string]>).map(([k, n]) => (
              <label key={k}>
                <span className="text-[10px] font-bold uppercase tracking-wide text-spento">{n}</span>
                <input value={String(studio[k] ?? '')} onChange={(e) => setStudio({ ...studio, [k]: e.target.value })}
                       className="mt-0.5 w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu" />
              </label>
            ))}
            {([['iva', 'IVA %'], ['giorni', 'Pagamento entro (giorni)'], ['preavviso', 'Preavviso disdetta (giorni)']] as Array<[keyof DatiStudio, string]>).map(([k, n]) => (
              <label key={k}>
                <span className="text-[10px] font-bold uppercase tracking-wide text-spento">{n}</span>
                <input type="number" value={Number(studio[k] ?? 0)} onChange={(e) => setStudio({ ...studio, [k]: Number(e.target.value) || 0 })}
                       className="mt-0.5 w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm tabular-nums outline-none focus:border-blu" />
              </label>
            ))}
          </div>
          <button onClick={async () => { const e = await scriviStudio(studio); if (e) setProblema(e); else { setStudioAperto(false); setStudioChiesto(false); avvisa('Dati dello Studio salvati') } }}
                  className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro">Salva</button>
        </Card>
      )}

      {/* I DOCUMENTI: il foglio bianco sta in cima, perche' e' la cosa che
          si viene a fare qui. I modelli si aprono con un clic, non con un
          modale: la scelta e' una riga di chip */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={() => setScelgoModello((v) => !v)}
                  className="flex items-center gap-2 rounded-full bg-blu px-4 py-1.5 text-sm font-bold text-white shadow-[0_4px_12px_rgba(6,23,115,0.25)] hover:bg-blu-scuro">
            <span className="text-base leading-none">+</span> Nuovo documento
          </button>
          {scelgoModello && (
            <div className="flex flex-wrap gap-1.5">
              <button title="Il documento che si firma: voci, prezzi, condizioni"
                      onClick={() => { setScelgoModello(false); apriNuovo() }}
                      className="rounded-[6px] border border-bordo bg-white px-3 py-1.5 text-xs font-semibold text-navy hover:border-blu">
                Condizioni economiche
              </button>
              {MODELLI.map((m) => (
                <button key={m.chiave} title={m.cosa}
                        onClick={() => { setScelgoModello(false); setApro({ id: null, modello: m.chiave }) }}
                        className="rounded-[6px] border border-bordo bg-white px-3 py-1.5 text-xs font-semibold text-navy hover:border-blu">
                  {m.nome}
                </button>
              ))}
            </div>
          )}
          {!scelgoModello && documenti && documenti.length > 0 && (
            <span className="text-sm text-tenue">{documenti.length} document{documenti.length === 1 ? 'o' : 'i'}</span>
          )}
        </div>
        {documenti && documenti.length > 0 && (
          <ul className="mt-3 divide-y divide-velo border-t border-velo">
            {documenti.slice(0, 8).map((d) => (
              <li key={d.id}>
                <button onClick={() => setApro({ id: d.id, modello: d.modello })}
                        className="flex w-full flex-wrap items-baseline gap-x-3 gap-y-0.5 px-1 py-2.5 text-left hover:bg-velo/60">
                  <span className="text-sm font-semibold">{d.titolo}</span>
                  <span className="text-xs text-tenue">{nomeDi(d.prospect_id ?? '') || 'senza azienda'}</span>
                  <span className="ml-auto text-[11px] text-spento">{fmtDateShort(d.aggiornato_il.slice(0, 10))}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* quanto chiedere: sta qui perche' e' il momento in cui lo decidi */}
      <Prezzo />

      {/* I NUMERI: uno grande, quello che aspetta una risposta. Gli altri
          sono di contorno: prima erano quattro riquadri uguali e uno diceva
          zero, quindi non guardavi nessuno (Dre, 15/9) */}
      <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2 rounded-2xl border border-bordo bg-white px-5 py-4">
        <span className="flex items-baseline gap-2">
          <span className="text-[26px] font-extrabold leading-none tabular-nums">{somma(inGiro).toLocaleString('it-IT')} €</span>
          <Micro>in giro, in attesa</Micro>
        </span>
        {scaduti.length > 0 && (
          <span className="text-sm font-bold text-amber-800">{scaduti.length} scadut{scaduti.length === 1 ? 'o' : 'i'}</span>
        )}
        <span className="text-sm text-tenue">
          <b className="font-bold tabular-nums text-inchiostro">{somma(daIncassare).toLocaleString('it-IT')} €</b> da incassare
        </span>
        <span className="text-sm text-tenue">
          <b className="font-bold tabular-nums text-green-800">{somma(incassati).toLocaleString('it-IT')} €</b> incassati
        </span>
        {incassi && (
          <span className="ml-auto text-sm text-tenue">
            <b className="font-bold tabular-nums text-inchiostro">{Math.round(mensile).toLocaleString('it-IT')} €</b> al mese su Stripe,{' '}
            {abbonamenti.length} attiv{abbonamenti.length === 1 ? 'o' : 'i'}
          </span>
        )}
      </div>

      {/* la barra: filtri, ricerca, nuovo */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1.5">
          {([['giro', 'In giro'], ['accettati', 'Da incassare'], ['pagati', 'Pagati'], ['rifiutati', 'Rifiutati'], ['bozze', 'Bozze'], ['tutti', 'Tutti']] as Array<[Filtro, string]>).map(([k, n]) => (
            <button key={k} onClick={() => setFiltro(k)}
                    className={`rounded-full px-3 py-1 text-[13px] font-semibold ${filtro === k ? 'bg-navy text-white' : 'bg-white text-tenue ring-1 ring-bordo hover:text-inchiostro'}`}>{n}</button>
          ))}
        </div>
        <div className="ml-auto flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <input type="search" value={cerca} onChange={(e) => setCerca(e.target.value)} placeholder="Cerca azienda o numero…"
                 className="w-full min-w-0 rounded-full border border-bordo bg-white px-4 py-1.5 text-sm outline-none focus:border-blu sm:w-48" />
          <button onClick={() => setStudioAperto((v) => !v)} title="Ragione sociale, P.IVA, IVA, termini: vanno nei PDF"
                  className="rounded-full px-2 py-1.5 text-sm font-semibold text-tenue hover:text-navy">Dati Studio</button>

        </div>
      </div>

      {/* IL PANNELLO: azienda, voci, validita', PDF. Tutto in una schermata */}
      {bozza && (
        <Card className="salta-su space-y-5 border-blu/40 p-5 lg:pb-16">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-base font-extrabold">{bozza.id ? 'Modifica il preventivo' : 'Nuovo preventivo'}</h2>
            <button onClick={chiudiBozza} className="text-xs font-semibold text-spento hover:text-inchiostro">Annulla</button>
          </div>

          {/* 1. l'azienda */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Micro>Azienda</Micro>
              {bozza.prospect_id ? (
                <div className="mt-1 flex items-center gap-2.5 rounded-xl border border-bordo bg-white px-3 py-2">
                  {nomi[bozza.prospect_id] && <Faccia p={nomi[bozza.prospect_id]} size={28} />}
                  <span className="min-w-0 flex-1 truncate text-sm font-semibold">{nomeDi(bozza.prospect_id)}</span>
                  {!bozza.id && <button onClick={() => setBozza({ ...bozza, prospect_id: '' })} className="text-xs font-semibold text-blu hover:underline">Cambia</button>}
                </div>
              ) : (
                <div className="mt-1">
                  <CercaAzienda onScegli={(a) => scegliAzienda(comeNome(a))} placeholder="Scrivi il nome dell'azienda…" />
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <p className="col-span-2 -mb-1 text-[11px] text-spento">
                {dallaPiva
                  ? <span className="font-semibold text-navy">Presi dal registro europeo: {dallaPiva}</span>
                  : buchiCliente.length > 0
                  ? <span className="font-semibold text-amber-800">Per il PDF manca {buchiCliente.join(', ')}</span>
                  : 'Valgono per tutti i preventivi e le fatture di questa azienda'}
              </p>
              {([['ragione', 'Ragione sociale'], ['piva', 'Partita IVA'], ['indirizzo', 'Indirizzo'], ['pec', 'PEC'], ['sdi', 'Codice SDI']] as Array<[keyof Fatturazione, string]>).map(([k, n]) => (
                <label key={k} className={k === 'indirizzo' ? 'col-span-2' : ''}>
                  <span className="text-[10px] font-bold uppercase tracking-wide text-spento">{n}</span>
                  <input value={bozza.fatturazione[k] ?? ''}
                         onChange={(e) => setBozza({ ...bozza, fatturazione: { ...bozza.fatturazione, [k]: e.target.value } })}
                         onBlur={(e) => { if (k === 'piva') void cercaPiva(e.target.value) }}
                         placeholder={k === 'piva' ? 'Scrivila e il resto arriva' : undefined}
                         className="mt-0.5 w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu" />
                </label>
              ))}
            </div>
          </div>

          {/* 2. le voci: dal listino con un clic, o scritte a mano */}
          <div>
            <div className="flex flex-wrap items-center gap-1.5">
              <Micro>Voci</Micro>
              {listino.length === 0 && <span className="text-xs text-amber-800">Il catalogo è vuoto: le voci si aggiungono dal listino</span>}
              {listino.map((v) => (
                <button key={v.id} onClick={() => aggiungiVoce(v)} title={v.descrizione ?? undefined}
                        className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-semibold text-tenue hover:border-navy hover:text-navy">
                  + {v.nome}<span className={v.prezzo ? 'text-spento' : 'font-bold text-amber-700'}> {euro(Number(v.prezzo) || 0)}{v.ricorrenza === 'mese' ? '/mese' : ''}</span>
                </button>
              ))}
              <button onClick={() => setBozza({ ...bozza, voci: [...bozza.voci, { nome: '', quantita: 1, prezzo: 0, ricorrenza: 'una_tantum' }] })}
                      className="rounded-full border border-dashed border-bordo px-3 py-1 text-xs font-semibold text-tenue hover:border-navy hover:text-navy">+ voce a mano</button>
            </div>
            {bozza.voci.length > 0 && (
              <div className="mt-2 overflow-hidden rounded-xl border border-bordo bg-white">
                {bozza.voci.map((v, i) => (
                  <div key={i} className="grid grid-cols-[1fr_28px] items-center gap-2 border-b border-velo px-3 py-2 last:border-0 sm:grid-cols-[1fr_64px_110px_120px_28px]">
                    <div className="col-span-2 min-w-0 sm:col-span-1">
                      <input value={v.nome} onChange={(e) => cambiaVoce(i, { nome: e.target.value })} placeholder="Cosa"
                             className="w-full rounded bg-transparent text-sm font-semibold outline-none focus:bg-velo" />
                      <input value={v.descrizione ?? ''} onChange={(e) => cambiaVoce(i, { descrizione: e.target.value })} placeholder="Una riga che spiega (va nel PDF)"
                             className="w-full rounded bg-transparent text-xs text-tenue outline-none focus:bg-velo" />
                    </div>
                    <input type="number" min={1} value={v.quantita} onChange={(e) => cambiaVoce(i, { quantita: Math.max(1, Number(e.target.value) || 1) })}
                           aria-label="Quantità"
                           className="w-full rounded-lg border border-bordo px-2 py-1 text-right text-sm tabular-nums outline-none focus:border-blu" />
                    <div className="flex items-center gap-1">
                      <input type="number" min={0} step={1} value={v.prezzo} onChange={(e) => cambiaVoce(i, { prezzo: Math.max(0, Number(e.target.value) || 0) })}
                             className="w-full rounded-lg border border-bordo px-2 py-1 text-right text-sm tabular-nums outline-none focus:border-blu" />
                      <span className="text-xs text-spento">€</span>
                    </div>
                    <div className="flex overflow-hidden rounded-lg border border-bordo text-[11px] font-semibold">
                      {(['una_tantum', 'mese'] as const).map((r) => (
                        <button key={r} onClick={() => cambiaVoce(i, { ricorrenza: r })}
                                className={`flex-1 px-1.5 py-1 ${v.ricorrenza === r ? 'bg-blu text-white' : 'bg-white text-tenue hover:bg-velo'}`}>
                          {r === 'mese' ? 'al mese' : 'una tantum'}
                        </button>
                      ))}
                    </div>
                    <button onClick={() => setBozza({ ...bozza, voci: bozza.voci.filter((_, k) => k !== i) })} aria-label="Togli" className="text-spento hover:text-red-700">×</button>
                  </div>
                ))}
                <div className="flex flex-wrap items-baseline justify-end gap-x-5 gap-y-1 bg-velo/60 px-3 py-2 text-sm">
                  {unaTantum(bozza.voci) > 0 && <span><span className="text-tenue">alla firma</span> <b className="tabular-nums">{euro(unaTantum(bozza.voci))}</b></span>}
                  {alMese(bozza.voci) > 0 && <span><span className="text-tenue">poi</span> <b className="tabular-nums">{euro(alMese(bozza.voci))}</b> <span className="text-tenue">al mese</span></span>}
                  <span className="text-xs text-spento">IVA esclusa, linea {LINEA_NOME[lineaDi(bozza.voci, listino)]}</span>
                </div>
              </div>
            )}
          </div>

          {/* 3. validita' e note, poi il PDF */}
          <div className="flex flex-wrap items-end gap-3">
            <label>
              <span className="text-[10px] font-bold uppercase tracking-wide text-spento">Valido fino al</span>
              <input type="date" value={bozza.valido_fino} onChange={(e) => setBozza({ ...bozza, valido_fino: e.target.value })}
                     className="mt-0.5 block rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu" />
            </label>
            <label className="min-w-[240px] flex-1">
              <span className="text-[10px] font-bold uppercase tracking-wide text-spento">Note interne (non vanno nel PDF)</span>
              <input value={bozza.note} onChange={(e) => setBozza({ ...bozza, note: e.target.value })}
                     className="mt-0.5 block w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu" />
            </label>
            <div className="ml-auto flex items-center gap-2 lg:mr-24">
              <button onClick={() => salva(false)} disabled={!!lavoro} className="rounded-full border border-bordo bg-white px-4 py-2 text-sm font-semibold text-tenue hover:border-navy hover:text-navy disabled:opacity-40">Salva bozza</button>
              <button onClick={() => salva(true)} disabled={!!lavoro || manca.length > 0 || bozza.voci.length === 0}
                      title={manca.length ? `Manca ${manca.join(', ')}` : undefined}
                      className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-40">{lavoro ?? 'Genera il PDF'}</button>
            </div>
          </div>
        </Card>
      )}

      {conferma && (
        <Card className="salta-su flex flex-wrap items-center gap-3 border-blu/40 p-4">
          <span className="flex-1 text-sm font-semibold">{conferma.testo}</span>
          <button onClick={() => { conferma.fai(); setConferma(null) }} className="rounded-full bg-blu px-4 py-1.5 text-sm font-bold text-white hover:bg-blu-scuro">Sì, vai</button>
          <button onClick={() => setConferma(null)} className="rounded-full border border-bordo bg-white px-4 py-1.5 text-sm font-semibold text-tenue hover:border-spento">No, lascia stare</button>
        </Card>
      )}

      {/* una domanda veloce: il motivo del no, o il link di pagamento */}
      {chiedo && (
        <Card className="salta-su flex flex-wrap items-center gap-2 border-blu/40 p-3">
          <span className="text-sm font-semibold">{chiedo.cosa === 'rifiuto' ? 'Perché ha detto no?' : 'Incolla il link di pagamento Stripe'}</span>
          <input autoFocus value={testoChiesto} onChange={(e) => setTestoChiesto(e.target.value)} placeholder={chiedo.cosa === 'rifiuto' ? 'In due parole, o lascia vuoto' : 'https://buy.stripe.com/…'}
                 onKeyDown={(e) => { if (e.key === 'Escape') setChiedo(null) }}
                 className="min-w-[260px] flex-1 rounded-lg border border-bordo bg-white px-3 py-1.5 text-sm outline-none focus:border-blu" />
          <button onClick={async () => {
            const q = righe.find((x) => x.id === chiedo.id)!
            if (chiedo.cosa === 'rifiuto') await segnaRifiutato(q, testoChiesto.trim())
            else { const r = await scrivi(q.id, { link_pagamento: testoChiesto.trim() || null }); if (r) avvisa('Link salvato') }
            setChiedo(null)
          }} className="rounded-full bg-blu px-4 py-1.5 text-sm font-bold text-white">Ok</button>
          <button onClick={() => setChiedo(null)} className="text-xs text-spento hover:text-inchiostro">annulla</button>
        </Card>
      )}

      {/* LA LISTA: una riga per preventivo, con l'esito a portata di mano */}
      {visibili.length === 0 ? (
        <Card><p className="px-4 py-8 text-center text-sm text-spento">
          {righe.length === 0 ? 'Nessun preventivo ancora.' : t ? `Niente per «${cerca.trim()}»` : filtro === 'giro' ? 'Nessuno sta aspettando una risposta.' : 'Nessuno qui dentro.'}
        </p></Card>
      ) : (
        <div className="space-y-2">
          {visibili.map((q) => {
            const n = nomi[q.prospect_id]
            const st = statoRiga(q)
            const passo = prossimoPasso(q)
            const apertoQui = menu === q.id
            return (
              <Card key={q.id} className="px-4 py-3">
                <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4">
                  <button onClick={() => onOpen(q.prospect_id)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
                    {n && <Faccia p={n} size={36} />}
                    <span className="min-w-0">
                      <span className="flex items-baseline gap-2">
                        <span className="truncate text-[15px] font-bold">{nomeDi(q.prospect_id)}</span>
                        <span className="shrink-0 text-[11px] text-spento">{q.numero}</span>
                      </span>
                      <span className="mt-0.5 flex items-center gap-1.5">
                        <span className={`inline-block h-[7px] w-[7px] shrink-0 rounded-full ${st.pallino}`} />
                        <span className={`truncate text-[12px] ${st.testo_colore}`}>{st.testo}</span>
                      </span>
                    </span>
                  </button>

                  <div className="flex items-center justify-between gap-3 pl-[48px] sm:contents">
                  <span className="shrink-0 text-right sm:w-32">
                    <span className="block text-[17px] font-extrabold leading-tight tabular-nums">
                      {q.importo ? euro(q.importo) : q.mensile ? euro(q.mensile) : '0 €'}
                    </span>
                    <span className="block truncate text-[11px] text-tenue">
                      {q.mensile && q.importo ? `più ${euro(q.mensile)} al mese` : q.mensile ? 'al mese' : (q.titolo || 'una tantum')}
                    </span>
                  </span>

                  <span className="flex shrink-0 items-center justify-end gap-2 sm:w-[250px]">
                    {passo && (
                      <button onClick={passo.fai}
                              className={`whitespace-nowrap rounded-full px-4 py-1.5 text-xs font-bold text-white ${passo.tono}`}>
                        {passo.testo}
                      </button>
                    )}
                    {q.stato === 'inviato' && (
                      <button onClick={() => { setChiedo({ id: q.id, cosa: 'rifiuto' }); setTestoChiesto('') }}
                              className="whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold text-tenue hover:text-red-700">
                        Ha detto no
                      </button>
                    )}
                    <div className="relative">
                      <button onClick={() => setMenu(apertoQui ? null : q.id)} aria-label="Altro"
                              className="flex h-8 w-8 items-center justify-center rounded-full text-tenue hover:bg-velo hover:text-inchiostro">
                        <svg viewBox="0 0 24 24" className="h-4 w-4"><path fill="currentColor" d="M6 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" /></svg>
                      </button>
                      {apertoQui && (
                        <>
                          <button className="fixed inset-0 z-10 cursor-default" aria-label="Chiudi" onClick={() => setMenu(null)} />
                          <div className="absolute right-0 top-9 z-20 w-56 overflow-hidden rounded-xl border border-bordo bg-white py-1 text-left shadow-[0_12px_32px_rgba(16,24,40,0.16)]">
                            {q.pdf_path && (
                              <button onClick={() => { setMenu(null); void apri(q) }} className="block w-full px-3.5 py-2 text-sm hover:bg-velo">Apri il PDF</button>
                            )}
                            {(q.stato === 'bozza' || q.stato === 'inviato') && (
                              <button onClick={() => { setMenu(null); apriModifica(q) }} className="block w-full px-3.5 py-2 text-left text-sm hover:bg-velo">Modifica</button>
                            )}
                            <button onClick={() => { setMenu(null); void copiaLink(q) }} className="block w-full px-3.5 py-2 text-left text-sm hover:bg-velo">
                              {q.link_pagamento ? 'Copia il link di pagamento' : 'Metti il link di pagamento'}
                            </button>
                            <button onClick={() => { setMenu(null); onOpen(q.prospect_id) }} className="block w-full px-3.5 py-2 text-left text-sm hover:bg-velo">Apri la scheda</button>
                            {(q.stato === 'accettato' || q.stato === 'rifiutato') && !q.pagato_il && (
                              <button onClick={() => { setMenu(null); void riapri(q) }} className="block w-full px-3.5 py-2 text-left text-sm hover:bg-velo">Rimetti in attesa</button>
                            )}
                            {q.stato === 'bozza' && (
                              <button onClick={() => { setMenu(null); elimina(q) }} className="block w-full px-3.5 py-2 text-left text-sm text-red-700 hover:bg-red-50">Elimina</button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </span>
                  </div>
                </div>
                {q.note && <p className="mt-1.5 pl-[48px] text-[11px] text-spento">{q.note}</p>}
              </Card>
            )
          })}
        </div>
      )}

      {/* GLI INCASSI DA STRIPE: Clara li legge ogni ora (stripe_sync.py).
          Stanno chiusi: si aprono quando si cerca un pagamento */}
      {incassi && (
        <section className="rounded-2xl border border-bordo bg-white">
          <button onClick={() => setIncassiAperti((v) => !v)}
                  className="flex w-full items-center gap-2.5 px-4 py-3 text-left">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                 className={`h-3.5 w-3.5 text-spento transition-transform ${incassiAperti ? 'rotate-90' : ''}`}>
              <path d="M9 6l6 6-6 6" />
            </svg>
            <span className="text-sm font-bold">Incassi su Stripe</span>
            <span className="text-sm text-tenue">
              {veri.length} movimenti, {senzaAzienda > 0 ? `${senzaAzienda} da collegare a un'azienda` : 'tutti collegati'}
            </span>
          </button>
          {incassiAperti && (
            <div className="overflow-x-auto border-t border-velo">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-velo text-left text-[11px] font-semibold text-spento">
                    <th className="min-w-[88px] px-3 py-2 font-semibold">Quando</th>
                    <th className="min-w-[96px] px-3 py-2 font-semibold">Cosa</th>
                    <th className="min-w-[160px] px-3 py-2 font-semibold">Cliente</th>
                    <th className="min-w-[160px] px-3 py-2 font-semibold">Descrizione</th>
                    <th className="min-w-[90px] px-3 py-2 text-right font-semibold">Importo</th>
                    <th className="min-w-[150px] px-3 py-2 font-semibold">Azienda</th>
                  </tr>
                </thead>
                <tbody>
                  {veri.map((i) => (
                    <tr key={i.id} className="border-b border-velo last:border-0 hover:bg-velo/40">
                      <td className="px-3 py-2 text-sm tabular-nums">{fmtDateShort(i.quando ? i.quando.slice(0, 10) : null)}</td>
                      <td className="px-3 py-2 text-sm">
                        {GENERE[i.genere]}{i.ricorrenza ? <span className="text-spento">, {i.ricorrenza === 'year' ? 'ogni anno' : 'ogni mese'}</span> : null}
                        <span className="ml-1.5 inline-flex items-center gap-1 rounded-[4px] border border-bordo bg-white px-1.5 py-[2px] text-[10px] font-bold uppercase tracking-[0.06em] text-tenue">
                          <span className={`h-[5px] w-[5px] shrink-0 rounded-[1px] ${tonoStato(i.stato)}`} />
                          {statoIt(i.stato)}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <p className="text-sm font-semibold">{i.cliente_nome || <span className="font-normal text-spento">senza nome</span>}</p>
                        {i.cliente_email && <p className="text-[11px] text-spento">{i.cliente_email}</p>}
                      </td>
                      <td className="px-3 py-2 text-sm text-tenue">{i.descrizione || <span className="text-spento">senza descrizione</span>}</td>
                      <td className="px-3 py-2 text-right text-sm font-bold tabular-nums">{i.importo.toLocaleString('it-IT', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} {i.valuta.toUpperCase()}</td>
                      <td className="px-3 py-2 text-xs">
                        {i.prospect_id
                          ? <button onClick={() => onOpen(i.prospect_id!)} className="font-semibold hover:text-navy">{nomeDi(i.prospect_id)}{i.preventivo_id ? <span className="text-spento">, preventivo pagato</span> : null}</button>
                          : <CercaAzienda piccolo placeholder="collega a un'azienda…" onScegli={(a) => { setNomi((m) => ({ ...m, [a.id]: comeNome(a) })); void collega(i.id, a.id) }} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {toast && (
        <div className="salta-su fixed bottom-20 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-full border border-green-200 bg-green-50 px-5 py-2.5 text-sm font-bold text-green-800 shadow-[0_8px_24px_rgba(16,24,40,0.2)] sm:bottom-6">
          <span>{toast.testo}</span>
          {toast.apri && (
            <button onClick={() => void apri(toast.apri!)} className="rounded-full bg-green-700 px-3 py-1 text-xs font-bold text-white hover:bg-green-800">
              Apri il PDF
            </button>
          )}
        </div>
      )}
    </div>
  )
}
