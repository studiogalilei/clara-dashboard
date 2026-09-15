// I MODELLI (14/9): i documenti dello Studio rigenerati col motore del brand.
//   npx tsx scripts/modelli.ts <cartella con i doc-*.json> <cartella di uscita>
// Usa lo stesso motore dei preventivi (src/lib/documento.ts): stesse regole,
// stesso PDF. Il modello delle Condizioni economiche nasce da condizioni.ts
// con i dati segnaposto.
import { readFileSync, writeFileSync, readdirSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
const __dirname = dirname(fileURLToPath(import.meta.url))
import { generaPdf, nomeFile, controllaTono, testoDi, type Documento, type Risorse } from '../src/lib/documento'
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
  sfondi: {
    marketing: readFileSync(join(pub, 'brand', 'sg-sfondo-marketing.png')),
    ai: readFileSync(join(pub, 'brand', 'sg-sfondo-ai.png')),
    software: readFileSync(join(pub, 'brand', 'sg-sfondo-software.png')),
    istituzionale: readFileSync(join(pub, 'brand', 'sg-sfondo-istituzionale.png')),
  },
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
        { nome: 'Fase pilota Google Ads, 2 mesi', descrizione: 'Analisi iniziale, impostazione, gestione e ottimizzazione sui dati', quantita: 1, prezzo: 1500, ricorrenza: 'una_tantum' },
        { nome: 'Lavoro continuativo Google Ads', descrizione: 'Dal terzo mese: gestione operativa, report periodici, call di allineamento', quantita: 1, prezzo: 1400, ricorrenza: 'mese' },
      ] },
    'Nome Azienda', { ragione: 'Ragione sociale completa', indirizzo: 'Via e numero, CAP Città (PR)', piva: '00000000000' }, 'marketing',
    { ragione: 'Studio Galilei', indirizzo: 'Sede dello Studio', piva: '00000000000', iva: 22, giorni: 15, preavviso: 30, firmatario: 'Nome, ruolo e firma' })])

  for (const [nome, doc] of docs) {
    const problemi = controllaTono(testoDi(doc))
    if (problemi.length) { console.error(`  ${nome}: NON PASSA IL TONO: ${problemi.join(', ')}`); continue }
    const bytes = await generaPdf(doc, risorse)
    const file = nomeFile(nome)
    writeFileSync(join(fuori, file), bytes)
    console.log(`  ${file.padEnd(44)} ${(bytes.byteLength / 1024).toFixed(0).padStart(6)} KB`)
  }
}
void main()
