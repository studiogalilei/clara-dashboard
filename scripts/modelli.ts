// I MODELLI (14/9): i documenti dello Studio rigenerati col motore del brand.
//   npx tsx scripts/modelli.ts <cartella con i doc-*.json> <cartella di uscita>
// Usa lo stesso motore dei preventivi (src/lib/documento.ts): stesse regole,
// stesso PDF. Il modello delle Condizioni economiche nasce da condizioni.ts
// con i dati segnaposto.
//   Oltre al tono si controlla anche l'impaginazione: le etichette maiuscole
//   sono disegnate lettera per lettera, quindi occupano piu' spazio di quanto
//   il motore misuri, e se sono lunghe si accavallano fra una colonna e
//   l'altra. Qui si vede prima di stampare, non dopo (QA Dre, 15/9).
import { readFileSync, writeFileSync, readdirSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { PDFDocument, type PDFFont } from 'pdf-lib'
import fontkit from '@pdf-lib/fontkit'
const __dirname = dirname(fileURLToPath(import.meta.url))
import { generaPdf, nomeFile, controllaTono, testoDi, type Documento, type Blocco, type Risorse } from '../src/lib/documento'
import { documentoDi } from '../src/lib/condizioni'

const [, , dentro, fuori] = process.argv
if (!dentro || !fuori) { console.error('uso: npx tsx scripts/modelli.ts <json> <uscita>'); process.exit(1) }
mkdirSync(fuori, { recursive: true })

const pub = join(__dirname, '..', 'public')
const risorse: Risorse = {
  regular: readFileSync(join(pub, 'fonts', 'Poppins-Regular.ttf')),
  semibold: readFileSync(join(pub, 'fonts', 'Poppins-SemiBold.ttf')),
  logo: readFileSync(join(pub, 'brand', 'SG_logo_blu.png')),
  logoBianco: readFileSync(join(pub, 'brand', 'SG_logo_bianco.png')),
  segni: {
    sottolineatura: readFileSync(join(pub, 'brand', 'sg-segno-sottolineatura.png')),
    spunta: readFileSync(join(pub, 'brand', 'sg-segno-spunta.png')),
    tratto: readFileSync(join(pub, 'brand', 'sg-segno-tratto.png')),
  },
  sfondi: {
    marketing: readFileSync(join(pub, 'brand', 'sg-sfondo-marketing.png')),
    ai: readFileSync(join(pub, 'brand', 'sg-sfondo-ai.png')),
    software: readFileSync(join(pub, 'brand', 'sg-sfondo-software.png')),
    istituzionale: readFileSync(join(pub, 'brand', 'sg-sfondo-istituzionale.png')),
  },
}

// ── il controllo dell'impaginazione ─────────────────────────────────────
// Stesse misure del motore (src/lib/documento.ts): se cambiano li', cambiano qui.
const MM = 72 / 25.4
const LARGH = 166 * MM
const PAD = 2.5 * MM

// quanto e' larga davvero un'etichetta maiuscola disegnata lettera per lettera
const largoSpaziato = (t: string, f: PDFFont, size: number, spazio: number) =>
  f.widthOfTextAtSize(t.toUpperCase(), size) + spazio * t.length

// lo stesso a capo del motore, per contare le righe di un'etichetta
function aCapo(testo: string, f: PDFFont, size: number, largh: number): string[] {
  const righe: string[] = []
  let riga = ''
  for (const w of testo.split(/\s+/).filter(Boolean)) {
    const prova = riga ? `${riga} ${w}` : w
    if (f.widthOfTextAtSize(prova, size) <= largh) riga = prova
    else { if (riga) righe.push(riga); riga = w }
  }
  righe.push(riga)
  return righe
}

function controllaImpaginazione(doc: Documento, reg: PDFFont, sb: PDFFont): string[] {
  const guai: string[] = []
  const stretto = (che: string, testo: string, largo: number, spazio: number) => {
    if (largo > spazio) guai.push(`${che} «${testo}» sborda di ${Math.round(largo - spazio)} pt`)
  }
  for (const b of doc.blocchi as Blocco[]) {
    if (b.tipo === 'numeri') {
      const n = Math.max(1, Math.min(4, b.voci.length))
      const colW = LARGH / n
      for (const v of b.voci.slice(0, 4)) {
        // il valore grande: se uno solo e' lungo, il motore rimpicciolisce tutti
        if (sb.widthOfTextAtSize(v.valore, 40) > (colW - 5 * MM) * 1.6) guai.push(`numero «${v.valore}» costringe il blocco sotto i 25 pt`)
        for (const r of aCapo(v.etichetta.toUpperCase(), sb, 7, colW - 6 * MM)) stretto('etichetta', r, largoSpaziato(r, sb, 7, 0.9), colW - 3 * MM)
      }
    }
    if (b.tipo === 'tabella') {
      const tot = b.colonne.reduce((t, c) => t + c.larghezza, 0)
      b.colonne.forEach((c, i) => {
        const w = (c.larghezza / tot) * LARGH
        stretto('intestazione di colonna', c.testo, largoSpaziato(c.testo, sb, 7.4, 1.1), w - PAD * (i === 0 ? 1 : 2))
        for (const riga of b.righe) {
          const cella = riga[i]
          if (!cella) continue
          const f = cella.forte ? sb : reg
          const size = cella.forte ? 10.5 : 9.2
          const utile = w - PAD * (i === 0 ? 1 : 2)
          // una cella di una riga sola che non ci sta a capo va verificata a occhio
          if (f.widthOfTextAtSize(cella.testo, size) > utile && !cella.testo.includes(' ')) stretto('cella', cella.testo, f.widthOfTextAtSize(cella.testo, size), utile)
        }
      })
    }
    if (b.tipo === 'anagrafica') {
      const colW = LARGH / b.colonne.length
      for (const c of b.colonne) {
        stretto('titolo di anagrafica', c.titolo, largoSpaziato(c.titolo, sb, 7, 1), colW - 3 * MM)
        for (const r of c.righe) stretto('riga di anagrafica', r, reg.widthOfTextAtSize(r, 9.8), colW - 3 * MM)
      }
    }
    if (b.tipo === 'due_colonne') {
      const colW = (LARGH - 8 * MM) / 2
      for (const c of [b.sinistra, b.destra]) stretto('titolo di colonna', c.titolo, largoSpaziato(c.titolo, sb, 7, 1), colW)
    }
    if (b.tipo === 'riquadro') stretto('titolo di riquadro', b.titolo, largoSpaziato(b.titolo, sb, 7, 1), LARGH - 10 * MM)
    if (b.tipo === 'tappe') {
      const colW = LARGH / b.tappe.length
      for (const t of b.tappe) stretto('etichetta di tappa', t.quando, largoSpaziato(t.quando, sb, 7.2, 1.1), colW - 8 * MM)
    }
    if (b.tipo === 'kicker') stretto('occhiello', b.testo, largoSpaziato(b.testo, sb, 7.4, 1.6), LARGH)
    // il titolo grande va su 145 mm: oltre le due righe l'interlinea si vede
    // troppo, e una parola sola sull'ultima riga resta li' appesa
    if (b.tipo === 'h1') {
      const righe = aCapo(b.testo, sb, 22, 145 * MM)
      if (righe.length > 2) guai.push(`titolo «${b.testo}» va su piu' di due righe`)
      else if (righe.length === 2 && righe[1].trim().split(/\s+/).length < 2) guai.push(`titolo «${b.testo}» lascia «${righe[1]}» da solo sulla seconda riga`)
    }
  }
  return guai
}

async function main() {
  const docs: Array<[string, Documento]> = []
  for (const f of readdirSync(dentro).filter((x) => x.startsWith('doc-') && x.endsWith('.json')).sort()) {
    docs.push([f.replace(/^doc-/, '').replace(/\.json$/, ''), JSON.parse(readFileSync(join(dentro, f), 'utf8')) as Documento])
  }
  // il modello delle condizioni economiche: dati segnaposto, testo vero
  docs.push(['condizioni-modello', documentoDi(
    { numero: 'SG-MK-AAAA-NNN', valido_fino: new Date(Date.now() + 30 * 86400e3).toISOString().slice(0, 10),
      voci: [
        { nome: 'Fase pilota Google Ads, 2 mesi', descrizione: 'Analisi iniziale, impostazione, gestione e correzione sui dati', quantita: 1, prezzo: 1500, ricorrenza: 'una_tantum' },
        { nome: 'Lavoro continuativo Google Ads', descrizione: 'Dal terzo mese: gestione operativa, report periodici, call di allineamento', quantita: 1, prezzo: 1400, ricorrenza: 'mese' },
      ] },
    'Nome Azienda', { ragione: 'Ragione sociale completa', indirizzo: 'Via e numero, CAP Città (PR)', piva: '00000000000' }, 'marketing',
    { ragione: 'Studio Galilei', indirizzo: 'Sede dello Studio', piva: '00000000000', iva: 22, giorni: 15, preavviso: 30, firmatario: 'Nome, ruolo e firma' })])

  const misura = await PDFDocument.create()
  misura.registerFontkit(fontkit)
  const reg = await misura.embedFont(risorse.regular)
  const sb = await misura.embedFont(risorse.semibold)

  let guai = 0
  for (const [nome, doc] of docs) {
    const problemi = controllaTono(testoDi(doc))
    if (problemi.length) { console.error(`  ${nome}: NON PASSA IL TONO: ${problemi.join(', ')}`); guai += 1; continue }
    for (const g of controllaImpaginazione(doc, reg, sb)) { console.error(`  ${nome}: ${g}`); guai += 1 }
    const bytes = await generaPdf(doc, risorse)
    const file = nomeFile(nome)
    writeFileSync(join(fuori, file), bytes)
    console.log(`  ${file.padEnd(44)} ${(bytes.byteLength / 1024).toFixed(0).padStart(6)} KB`)
  }
  if (guai) { console.error(`\n  ${guai} cose da sistemare prima di mandare fuori questi PDF`); process.exitCode = 1 }
}
void main()
