// LE SCHEDE DELLA SQUADRA (15/9/2026): un PDF per persona, col brand.
//   npx tsx scripts/schede_squadra.ts <cartella di uscita>
//
// Dre, il giorno degli accessi: «preparami un documento per ogni operatore su
// cos'e' SG Workspace e su com'e' settato il suo e perche'». Il testo vive in
// docs/squadra/*.md, che si legge e si corregge in due secondi; qui diventa
// il documento che si manda, con lo stesso motore dei preventivi, quindi
// stesse regole di tono e stessa impaginazione.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
const __dirname = dirname(fileURLToPath(import.meta.url))
import { generaPdf, controllaTono, testoDi, ripulisciTono, type Documento, type Blocco, type Risorse } from '../src/lib/documento'

const fuori = process.argv[2] ?? join(__dirname, '..', 'docs', 'squadra', 'pdf')
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
  sfondi: { istituzionale: readFileSync(join(pub, 'brand', 'sg-sfondo-istituzionale.png')) },
}

// ── il testo, dal markdown ──────────────────────────────────────────────
// Il .md e' fatto di sezioni «**Titolo**» e paragrafi. Le righe che iniziano
// con «*Sezione*: » diventano righe di tabella, il resto paragrafi.
interface Pezzo { titolo: string; righe: string[] }

function leggi(file: string): { nome: string; pezzi: Pezzo[] } {
  const testo = readFileSync(file, 'utf8')
  const nome = (testo.match(/# SG Workspace, la scheda di (.+)/) ?? [])[1] ?? '?'
  const pezzi: Pezzo[] = []
  let corrente: Pezzo | null = null
  let paragrafo: string[] = []
  const chiudi = () => {
    if (corrente && paragrafo.length) { corrente.righe.push(paragrafo.join(' ')); paragrafo = [] }
  }
  // una voce di elenco puo' andare a capo nel markdown: le righe rientrate
  // sotto un «1.» sono la stessa voce, se no in PDF diventano due (QA 15/9)
  let inElenco = false
  for (const riga of testo.split('\n').slice(1)) {
    const t = riga.trim()
    const rientrata = /^\s{2,}\S/.test(riga)
    const titolo = t.match(/^\*\*(.+)\*\*$/)
    if (titolo) { chiudi(); inElenco = false; corrente = { titolo: titolo[1], righe: [] }; pezzi.push(corrente); continue }
    if (!t) { chiudi(); inElenco = false; continue }
    if (/^\d\./.test(t) || t.startsWith('- ')) {
      chiudi(); inElenco = true
      corrente?.righe.push(t.replace(/^(\d\.|-)\s*/, ''))
      continue
    }
    if (inElenco && rientrata && corrente?.righe.length) {
      corrente.righe[corrente.righe.length - 1] += ' ' + t
      continue
    }
    paragrafo.push(t)
  }
  chiudi()
  return { nome, pezzi }
}

// «*Pipeline*: le aziende dalla Call Tecnica in poi» → riga di tabella
const RIGA_SEZIONE = /^\*([^*]+)\*:\s*(.+)$/s

function documentoDi(nome: string, pezzi: Pezzo[]): Documento {
  const blocchi: Blocco[] = []
  // la freccia non esiste nel Poppins: in PDF diventa un quadratino vuoto
  const pulisci = (t: string) => ripulisciTono(
    t.replace(/\*\*/g, '').replace(/«|»/g, '"').replace(/\*/g, '').replace(/\s*→\s*/g, ' poi '))

  for (const p of pezzi) {
    const sezioni = p.righe.map((r) => r.match(RIGA_SEZIONE)).filter(Boolean) as RegExpMatchArray[]
    const altre = p.righe.filter((r) => !RIGA_SEZIONE.test(r))
    blocchi.push({ tipo: 'h2', testo: pulisci(p.titolo) })

    if (sezioni.length >= 2) {
      // le sezioni del menu: una tabella, si legge a colpo d'occhio
      for (const r of altre) blocchi.push({ tipo: 'p', testo: pulisci(r) })
      blocchi.push({
        tipo: 'tabella',
        colonne: [{ testo: 'Dove', larghezza: 26 }, { testo: 'Cosa ci fai', larghezza: 74 }],
        righe: sezioni.map((m) => [{ testo: pulisci(m[1]), forte: true }, { testo: pulisci(m[2]) }]),
      })
      continue
    }
    if (p.righe.length > 1 && p.righe.every((r) => r.length < 220) && /regole|beta/i.test(p.titolo)) {
      blocchi.push({ tipo: 'elenco', voci: p.righe.map(pulisci) })
      continue
    }
    for (const r of p.righe) blocchi.push({ tipo: 'p', testo: pulisci(r) })
  }
  return {
    tipo: 'SG Workspace',
    copertina: {
      linea: 'istituzionale',
      occhiello: 'SG Workspace',
      titolo: `La scheda di ${nome}`,
      sottotitolo: 'Cosa vedi, perché è impostato così, e cosa ci serve da te',
      data: new Date().toLocaleDateString('it-IT', { month: 'long', year: 'numeric' }),
    },
    blocchi,
    piede: new Date().toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' }),
  }
}

async function main() {
  const dentro = join(__dirname, '..', 'docs', 'squadra')
  for (const chi of ['carlo', 'salvatore', 'alex', 'lorenzo', 'okay', 'giacomo']) {
    const { nome, pezzi } = leggi(join(dentro, `${chi}.md`))
    const doc = documentoDi(nome, pezzi)
    const problemi = controllaTono(testoDi(doc))
    if (problemi.length) { console.error(`  ${chi}: NON PASSA IL TONO: ${problemi.join(', ')}`); process.exitCode = 1; continue }
    const bytes = await generaPdf(doc, risorse)
    const file = `sg-workspace-${chi}.pdf`
    writeFileSync(join(fuori, file), bytes)
    console.log(`  ${file.padEnd(30)} ${(bytes.byteLength / 1024).toFixed(0).padStart(6)} KB`)
  }
}
void main()
