import { supabase } from './supabase'
import { urlFile, dimenticaFile } from './file'
import { nomeFile, LINEA_SIGLA, type Linea, type Risorse } from './tono'
import { documentoDi, type Voce, type Fatturazione, type Ricorrenza } from './condizioni'
import { datiStudio } from './studio'
export { unaTantum, alMese, ePilota, documentoDi } from './condizioni'
export type { Voce, Ricorrenza, Fatturazione } from './condizioni'

// IL PREVENTIVO (Dre, 14/9): nasce bozza, diventa un PDF «Condizioni
// economiche» secondo il brand, si segna inviato, poi accettato o rifiutato.
// Pagato lo scrive Stripe (stripe_sync) o Giacomo. Collegato all'azienda,
// alla sua cartella nei Documenti e, quando accettato, a un progetto.

export type StatoPreventivo = 'bozza' | 'inviato' | 'accettato' | 'rifiutato'
export interface Preventivo {
  id: number
  prospect_id: string
  progetto_id: number | null
  numero: string | null
  linea: Linea | null
  titolo: string | null
  importo: number | null        // la parte una tantum, in euro
  mensile: number | null        // la parte ricorrente, al mese
  voci: Voce[]
  inviato_il: string | null
  stato: StatoPreventivo
  accettato_il: string | null
  rifiutato_il: string | null
  motivo: string | null
  pagato_il: string | null
  pagamento_atteso_il: string | null
  valido_fino: string | null
  pdf_path: string | null
  link_pagamento: string | null
  note: string | null
  owner: string | null
  creato_il: string
  aggiornato_il: string
}
export interface VoceListino { id: number; nome: string; descrizione: string | null; prezzo: number; ricorrenza: Ricorrenza; linea: Linea; ordine: number; attivo: boolean }

export const STATI: Array<[StatoPreventivo, string, string]> = [
  ['bozza', 'bozza', 'bg-velo text-tenue'],
  ['inviato', 'inviato', 'bg-sky-100 text-sky-900'],
  ['accettato', 'accettato', 'bg-green-100 text-green-900'],
  ['rifiutato', 'rifiutato', 'bg-red-50 text-red-700'],
]

export const scaduto = (q: Preventivo) => q.stato === 'inviato' && !!q.valido_fino && q.valido_fino < new Date().toISOString().slice(0, 10)

// la linea la dicono le voci: se ce n'e' piu' d'una, istituzionale (un documento, una linea sola)
export function lineaDi(voci: Voce[], listino: VoceListino[]): Linea {
  const linee = new Set<Linea>()
  for (const v of voci) {
    const l = listino.find((x) => x.nome === v.nome)?.linea
    if (l) linee.add(l)
  }
  if (linee.size === 1) return [...linee][0]
  if (linee.size === 0) return 'marketing'
  return 'istituzionale'
}

// SG-MK-2026-003: sigla di linea, anno, progressivo nell'anno
export async function prossimoNumero(linea: Linea): Promise<string> {
  const anno = new Date().getFullYear()
  const prefisso = `SG-${LINEA_SIGLA[linea]}-${anno}-`
  const { data } = await supabase.from('preventivi').select('numero').like('numero', `${prefisso}%`)
  const n = Math.max(0, ...((data as Array<{ numero: string }>) ?? []).map((r) => Number(r.numero.slice(prefisso.length)) || 0)) + 1
  return `${prefisso}${String(n).padStart(3, '0')}`
}

// il titolo che si legge in lista: la voce principale, o le prime due
export function titoloDi(voci: Voce[]): string {
  const nomi = voci.map((v) => v.nome).filter(Boolean)
  if (nomi.length === 0) return 'Preventivo'
  if (nomi.length <= 2) return nomi.join(' e ')
  return `${nomi[0]} e altre ${nomi.length - 1} voci`
}

// le risorse del brand, dal sito stesso (public/): font e logo, una volta sola
let risorse: Promise<Risorse> | null = null
export function caricaRisorse(): Promise<Risorse> {
  if (!risorse) {
    const base = import.meta.env.BASE_URL
    const prendi = (u: string) => fetch(base + u).then((r) => { if (!r.ok) throw new Error(`manca ${u}`); return r.arrayBuffer() })
    // i segni a pennarello sono un di piu': se mancano il PDF esce lo stesso
    const forse = (u: string) => prendi(u).catch(() => undefined)
    risorse = Promise.all([
      prendi('fonts/Poppins-Regular.ttf'), prendi('fonts/Poppins-SemiBold.ttf'), prendi('brand/SG_logo_blu.png'),
      forse('brand/sg-segno-sottolineatura.png'), forse('brand/sg-segno-tratto.png'), forse('brand/sg-segno-spunta.png'),
      // le copertine: logo bianco e sfondi. Senza, la copertina esce blu
      // piatta e il documento sembra un altro documento (Dre, 16/9)
      forse('brand/SG_logo_bianco.png'),
      forse('brand/sg-sfondo-marketing.png'), forse('brand/sg-sfondo-ai.png'),
      forse('brand/sg-sfondo-software.png'), forse('brand/sg-sfondo-istituzionale.png'),
    ]).then(([regular, semibold, logo, sottolineatura, tratto, spunta, logoBianco, marketing, ai, software, istituzionale]) => ({
      regular, semibold, logo, logoBianco, segni: { sottolineatura, tratto, spunta },
      sfondi: { marketing, ai, software, istituzionale },
    }))
    risorse.catch(() => { risorse = null })
  }
  return risorse
}

// genera il PDF e lo mette nella cartella dell'azienda nei Documenti
export async function generaEArchivia(q: Preventivo, azienda: string, f: Fatturazione): Promise<{ path: string; url: string }> {
  const doc = documentoDi(q, azienda, f, q.linea ?? 'marketing', await datiStudio())
  const { generaPdf } = await import('./documento')   // pdf-lib solo quando serve
  const bytes = await generaPdf(doc, await caricaRisorse())
  const nome = nomeFile('condizioni', azienda)
  const path = `clienti/${q.prospect_id}/${(q.numero ?? String(q.id)).toLowerCase()}-${nome}`
  const { error } = await supabase.storage.from('vault').upload(path, new Blob([bytes as BlobPart], { type: 'application/pdf' }), { upsert: true, contentType: 'application/pdf' })
  if (error) throw new Error(error.message)
  // la riga nei Documenti: una per preventivo, aggiornata se si rigenera
  const { data: gia } = await supabase.from('vault_file').select('id').eq('path', path).maybeSingle()
  if (!gia) {
    await supabase.from('vault_file').insert({ nome: `Condizioni economiche ${q.numero ?? ''}`.trim(), path, mime: 'application/pdf', dimensione: bytes.byteLength, prospect_id: q.prospect_id, sezione: 'clienti', nota: titoloDi(q.voci) })
  } else {
    await supabase.from('vault_file').update({ dimensione: bytes.byteLength, at: new Date().toISOString() }).eq('id', gia.id)
  }
  dimenticaFile(path)
  return { path, url: (await urlFile(path)) ?? '' }
}
