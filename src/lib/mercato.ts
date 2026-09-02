// Il mercato del prospect, dalla base precalcolata del Keyword Planner
// (333 combinazioni settore x provincia, ODYN Cockpit/data/base_analisi.json).
// Se il prospect non ha p.market salvato a DB, si prova a ricavarlo da qui:
// e' lo stesso dato, calcolato una volta per tutti.
import base from './mercato.json'
import type { Market } from './types'

interface Voce {
  ricerche: number
  cpc: number
  mesi_vivi: number
  bars: Array<[number, 0 | 1]>
  zona: string
  fit: 'si' | 'no'
}

const BASE = base as unknown as Record<string, Voce>

// I nomi dei settori come stanno nella base
const SETTORI = [
  'agenzie_immobiliari', 'carpenteria_metallica', 'case_legno', 'ferro_battuto',
  'fotovoltaico_casa', 'pavimentazioni_esterne', 'pompe_calore_casa', 'serramenti',
]

// alias: come il settore puo' comparire sul prospect -> nome nella base
const ALIAS: Record<string, string> = {
  fotovoltaico: 'fotovoltaico_casa',
  'pompe di calore': 'pompe_calore_casa',
  pompe_calore: 'pompe_calore_casa',
  'case in legno': 'case_legno',
  immobiliare: 'agenzie_immobiliari',
  infissi: 'serramenti',
  carpenteria: 'carpenteria_metallica',
  pavimentazioni: 'pavimentazioni_esterne',
}

function normalizza(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, ' ')
}

function settoreBase(sector: string | null): string | null {
  if (!sector) return null
  const s = normalizza(sector)
  if (SETTORI.includes(s.replace(/ /g, '_'))) return s.replace(/ /g, '_')
  if (ALIAS[s]) return ALIAS[s]
  // match morbido: "serramenti e infissi" -> serramenti
  for (const nome of SETTORI) {
    if (s.includes(nome.replace(/_/g, ' ').split(' ')[0])) return nome
  }
  return null
}

export function mercatoDi(sector: string | null, city: string | null): Market | null {
  const settore = settoreBase(sector)
  if (!settore) return null

  // 1) combinazione esatta settore|provincia
  if (city) {
    const chiave = `${settore}|${normalizza(city)}`
    for (const k of Object.keys(BASE)) {
      if (k.toLowerCase() === chiave) {
        const v = BASE[k]
        return { ...v, misurato_il: '2026-08-24' }
      }
    }
  }

  // 2) solo settore: media onesta sulle province misurate, dichiarata come tale
  const voci = Object.entries(BASE).filter(([k]) => k.startsWith(settore + '|')).map(([, v]) => v)
  if (voci.length === 0) return null
  const media = (f: (v: Voce) => number) => Math.round(voci.reduce((s, v) => s + f(v), 0) / voci.length)
  const bars = voci[0].bars.map((_, i) => {
    const h = media((v) => v.bars[i][0])
    return [h, 0] as [number, 0 | 1]
  })
  const iMax = bars.reduce((im, b, i) => (b[0] > bars[im][0] ? i : im), 0)
  bars[iMax] = [bars[iMax][0], 1]
  return {
    ricerche: media((v) => v.ricerche),
    cpc: Math.round(media((v) => v.cpc * 100)) / 100,
    mesi_vivi: media((v) => v.mesi_vivi),
    bars,
    zona: `media sulle ${voci.length} province misurate`,
    fit: media((v) => v.mesi_vivi) >= 9 ? 'si' : 'no',
    misurato_il: '2026-08-24',
  }
}
