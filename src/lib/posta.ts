import { scrivi } from './preferenze'

// IL PERCHE' COSI' (gold, 6/10): sopra la bozza, il ragionamento di Clara in una riga,
// cosi' Dre giudica prima di leggere. Senza codici (INT-01, «si':»): parole sue.
export function percheCosi(perche: string | null | undefined): string {
  const t = (perche ?? '')
    .replace(/^\s*s[iì]'?\s*:\s*/i, '')
    .replace(/[,;]?\s*\(?\bINT-[A-Z0-9]+\b\)?/g, '')
    .replace(/\s+,/g, ',').replace(/\s{2,}/g, ' ').trim()
  if (!t) return ''
  const frase = t.length > 220 ? t.slice(0, 220).replace(/[,;\s]+\S*$/, '') + '…' : t
  return frase.charAt(0).toUpperCase() + frase.slice(1)
}

// DA OGGI ALLA POSTA, GIA' APERTA (gold, 6/10): «Leggi e approva» nella carta Adesso porta
// nella Posta sulla conversazione giusta, dentro la fila. Si segna qui quale aprire; la Posta
// la apre appena ha caricato e la dimentica.
// si segna la proposta e, come riserva, l'azienda: se l'azienda ha due proposte aperte la Posta
// potrebbe mostrarne un'altra, e la conversazione non si apriva
let daAprire: { proposta: number; azienda: string | null } | null = null
export function apriInPosta(propostaId: number, aziendaId: string | null = null) {
  daAprire = { proposta: propostaId, azienda: aziendaId }
  scrivi('clara-posta', 'conversazioni')
  window.dispatchEvent(new Event('clara:vai-posta'))
}
export function prendiDaAprire(): { proposta: number; azienda: string | null } | null {
  const id = daAprire
  daAprire = null
  return id
}

// SOLO QUELLO CHE HA SCRITTO LEI (gold, 6/10): la stessa regola di scripts/lettura.py
// (solo_suo), portata qui per «Cosa ci ha gia' detto». Via la nostra mail citata sotto,
// la firma dopo i saluti e il disclaimer legale. Se cambia la', cambia anche qui.
const CITAZIONE = /\n\s*(?:>\s*)?(?:il giorno\s+\w|on\s+\w.{0,60}\bwrote:|-{2,}\s*original message|da:\s|from:\s|inviato:\s|sent:\s|a:\s.{0,60}\noggetto:|_{5,})/i
const SCRITTO = /\b(?:ha scritto|wrote)\s*:/gi
const ORA = /\b\d{1,2}[:.]\d{2}\b/g
const DATA = /\b(?:19|20)\d{2}\b|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b/
const APERTURA = /(?<!\w)(?:il giorno|il|on|am|el|le)\s/gi
const SALUTI = /\n\s*(?:cordiali saluti|distinti saluti|un cordiale saluto|cari saluti|in attesa di|best regards|kind regards|--\s*$|__+\s*$)/im
const DISCLAIMER = /informativa privacy|(?:le |l')informazioni (?:incluse|contenute|trasmesse|presenti)|questo (?:messaggio|documento|e-?mail) (?:e'|è) (?:riservat|confidenzial|destinat)|il (?:presente|contenuto del) messaggio (?:e'|è)|this (?:communication|message|e-?mail|document) is (?:confidential|intended|reserved)|reg\.? ?ue ?2016\/679|regolamento \(?ue\)? ?2016\/679|\bgdpr\b|privacy:\s|destinatario indicato|ai sensi dell|\*{6,}|se (?:avete|hai) ricevuto (?:questo|questa) (?:messaggio|documento|mail|comunicazione) per errore/i

function intestazione(t: string): number | null {
  for (const m of t.matchAll(SCRITTO)) {
    const fine = m.index ?? 0
    const da = Math.max(0, fine - 200)
    const pezzo = t.slice(da, fine)
    const ore = [...pezzo.matchAll(ORA)]
    if (!ore.length || !DATA.test(pezzo)) continue      // «il mio collega ha scritto:» non e' una citazione
    const prima = ore[0].index ?? 0
    const aperture = [...pezzo.slice(0, prima).matchAll(APERTURA)]
    return da + (aperture.length ? (aperture[aperture.length - 1].index ?? 0) : prima)
  }
  return null
}

export function soloSuo(testo: string | null | undefined): string {
  let t = testo ?? ''
  const m = CITAZIONE.exec(t)
  if (m) t = t.slice(0, m.index)
  const h = intestazione(t)
  if (h !== null) t = t.slice(0, h)
  t = t.split('\n').filter((r) => !r.trimStart().startsWith('>')).join('\n').trim()
  const d = DISCLAIMER.exec(t)
  if (d) t = t.slice(0, d.index)
  const f = SALUTI.exec(t)
  if (f && t.slice(0, f.index).trim().length >= 25) t = t.slice(0, f.index)
  return t.trim()
}

// LA FRASE DI CLARA (gold, 6/10, dalla V3): in cima a Oggi Clara dice in una frase sola cosa
// aspetta te, dal vivo. Il saluto del mattino invecchiava alla prima approvazione.
export function fraseDiClara(x: { risposte: string[]; seguiti: number; siSenza?: number | null }): string {
  const pezzi: string[] = []
  const r = x.risposte
  if (r.length === 1) pezzi.push(`${r[0]} aspetta una risposta`)
  else if (r.length === 2) pezzi.push(`${r[0]} e ${r[1]} aspettano una risposta`)
  else if (r.length > 2) pezzi.push(`${r[0]}, ${r[1]} e altre ${r.length - 2} aspettano una risposta`)
  if (x.seguiti === 1) pezzi.push('ho preparato un follow-up')
  else if (x.seguiti > 1) pezzi.push(`ho preparato ${x.seguiti} follow-up`)
  if (x.siSenza === 1) pezzi.push('un sì aspetta ancora l’analisi')
  else if (x.siSenza && x.siSenza > 1) pezzi.push(`${x.siSenza} sì aspettano ancora l’analisi`)
  if (!pezzi.length) return 'Niente aspetta te: la giornata è chiusa.'
  const frase = pezzi.length === 1 ? pezzi[0] : `${pezzi.slice(0, -1).join(', ')} e ${pezzi[pezzi.length - 1]}`
  return frase.charAt(0).toUpperCase() + frase.slice(1) + '.'
}
