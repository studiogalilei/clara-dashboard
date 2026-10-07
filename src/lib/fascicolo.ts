// IL FASCICOLO IN PDF (Dre, 6/10: «il Workspace e' il fascicolo di ogni azienda,
// facilmente condivisibile, tipo in PDF, da mandare a Carlo o a Giacomo»).
// Un foglio pulito, nel brand, che il browser stampa o salva in PDF: niente
// librerie in piu', niente server. Si costruisce dai dati gia' in pagina.

export interface VoceFascicolo { at: string; titolo: string; testo?: string | null }

export interface Fascicolo {
  nome: string
  codice: string | null
  stato: string
  fase: string | null
  chiSono: string | null
  citta: string | null
  sito: string | null
  punto: string | null
  prossima: string | null
  referenti: Array<{ nome: string; ruolo: string | null; email: string | null; telefono: string | null; decide: string | null; nota: string | null }>
  preventivi: Array<{ numero: string | null; titolo: string | null; cifra: string; stato: string }>
  documenti: string[]
  filo: VoceFascicolo[]
  logo: string
}

const esc = (s: string | null | undefined) => (s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!))
const data = (iso: string) => new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' })

export function htmlFascicolo(f: Fascicolo): string {
  const oggi = new Date().toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })
  const sezione = (titolo: string, corpo: string) => corpo ? `<section><h2>${titolo}</h2>${corpo}</section>` : ''
  return `<!doctype html><html lang="it"><head><meta charset="utf-8"><title>Fascicolo ${esc(f.nome)}</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  @page { size: A4; margin: 18mm 16mm }
  * { box-sizing: border-box }
  body { margin: 0; font-family: 'Plus Jakarta Sans', sans-serif; color: #1c1b18; font-size: 10.5pt; line-height: 1.45 }
  header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1C2E6E; padding-bottom: 10pt; margin-bottom: 14pt }
  header img { height: 26pt }
  .meta { text-align: right; font-size: 8.5pt; color: #5b6170 }
  h1 { margin: 0; font-size: 22pt; font-weight: 800; color: #1C2E6E; line-height: 1.15 }
  .sotto { margin: 3pt 0 0; color: #5b6170 }
  .etichette { margin: 0 0 4pt; font-size: 8.5pt; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #2979C4 }
  h2 { margin: 16pt 0 6pt; font-size: 8.5pt; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #1C2E6E }
  section { break-inside: avoid-page }
  .riquadro { background: #f1f2f6; border-radius: 6pt; padding: 8pt 10pt }
  table { width: 100%; border-collapse: collapse }
  td { padding: 5pt 0; border-bottom: 1px solid #e5e7ec; vertical-align: top }
  td.d { width: 64pt; color: #5b6170; font-size: 9pt; white-space: nowrap }
  td.c { text-align: right; white-space: nowrap; font-weight: 600 }
  b { font-weight: 700 }
  .tenue { color: #5b6170 }
  .attesa { color: #8a5a00; font-weight: 700 }
  footer { margin-top: 20pt; padding-top: 6pt; border-top: 1px solid #e5e7ec; font-size: 8pt; color: #5b6170 }
</style></head><body>
<header>
  <div>
    <p class="etichette">${esc([f.codice, f.stato, f.fase].filter(Boolean).join(', '))}</p>
    <h1>${esc(f.nome)}</h1>
    <p class="sotto">${esc([f.chiSono, f.citta].filter(Boolean).join(', '))}${f.sito ? `, ${esc(f.sito)}` : ''}</p>
  </div>
  <div class="meta"><img src="${esc(f.logo)}" alt="Studio Galilei"><br>Fascicolo al ${oggi}</div>
</header>
${sezione('Adesso', (f.punto || f.prossima) ? `<div class="riquadro">${f.punto ? `<p style="margin:0">${esc(f.punto)}</p>` : ''}${f.prossima ? `<p style="margin:${f.punto ? '5pt' : '0'} 0 0"><b>Prossima call:</b> ${esc(f.prossima)}</p>` : ''}</div>` : '')}
${sezione('Referenti', f.referenti.length ? `<table>${f.referenti.map((r) => `<tr><td><b>${esc(r.nome || 'Senza nome')}</b>${r.ruolo ? `, ${esc(r.ruolo)}` : ''}${r.decide ? ` <span class="tenue">(${esc(r.decide)})</span>` : ''}${r.nota ? `<br><span class="tenue">${esc(r.nota)}</span>` : ''}</td><td class="c" style="font-weight:400">${esc([r.email, r.telefono].filter(Boolean).join('<br>')).replace(/&lt;br&gt;/g, '<br>')}</td></tr>`).join('')}</table>` : '')}
${sezione('Preventivi', f.preventivi.length ? `<table>${f.preventivi.map((q) => `<tr><td><b>${esc(q.titolo || 'Preventivo')}</b><br><span class="tenue">${esc(q.numero)}</span></td><td class="c ${/attesa/i.test(q.stato) ? 'attesa' : ''}">${esc(q.cifra)}<br><span style="font-weight:600">${esc(q.stato)}</span></td></tr>`).join('')}</table>` : '')}
${sezione('Documenti', f.documenti.length ? `<p style="margin:0">${f.documenti.map(esc).join('<br>')}</p>` : '')}
${sezione('Il filo del rapporto', f.filo.length ? `<table>${f.filo.map((v) => `<tr><td class="d">${data(v.at)}</td><td><b>${esc(v.titolo)}</b>${v.testo ? `<br><span class="tenue" style="white-space:pre-wrap">${esc(v.testo)}</span>` : ''}</td></tr>`).join('')}</table>` : '')}
<footer>Studio Galilei. Documento interno: contiene dati del cliente, non inoltrarlo fuori dallo Studio.</footer>
<script>addEventListener('load', () => setTimeout(() => print(), 400))</script>
</body></html>`
}

/** Apre il fascicolo in una scheda e chiede di stamparlo: «Salva come PDF» nel dialogo. */
export function apriFascicolo(f: Fascicolo): boolean {
  const w = window.open('', '_blank')
  if (!w) return false
  w.document.open()
  w.document.write(htmlFascicolo(f))
  w.document.close()
  return true
}
