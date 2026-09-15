import { PDFDocument, PDFFont, PDFImage, PDFPage, rgb, type RGB } from 'pdf-lib'
import fontkit from '@pdf-lib/fontkit'

// IL MOTORE DEI DOCUMENTI (14/9): un solo modo di impaginare, le regole
// del brand dentro (sg-regole-documenti.md). Lo usano i preventivi nel
// browser e lo script dei modelli in node: stessi blocchi, stesso PDF.
//   Poppins Regular per il corpo, SemiBold per i titoli. Due colori dentro
//   il documento: nero per il testo, Blu SG per la struttura. Lavanda per
//   i riquadri. Il colore di linea vive solo sulla copertina.
//   Niente trattino lungo, niente puntino centrale, niente punto esclamativo.

export const BLU = rgb(6 / 255, 23 / 255, 115 / 255)
export const NERO = rgb(10 / 255, 10 / 255, 26 / 255)
export const LAVANDA = rgb(238 / 255, 241 / 255, 250 / 255)
export const SOFFICE = rgb(201 / 255, 206 / 255, 223 / 255)
export const BIANCO = rgb(1, 1, 1)
export const GRIGIO = rgb(118 / 255, 118 / 255, 135 / 255)

export * from './tono'
import { controllaTono, testoDi, type Documento, type Blocco, type Copertina, type Risorse } from './tono'

// ── misure ──────────────────────────────────────────────────────────────
const MM = 72 / 25.4
const A4 = { w: 210 * MM, h: 297 * MM }
const MARG = { alto: 20 * MM, destra: 22 * MM, basso: 18 * MM, sinistra: 22 * MM }
const LARGH = A4.w - MARG.sinistra - MARG.destra
const CORPO = 9.8, INTERLINEA = 1.62

// il corsivo/lettere spaziate non ce l'abbiamo: il kicker si disegna lettera per lettera
function spaziato(page: PDFPage, testo: string, x: number, y: number, font: PDFFont, size: number, colore: RGB, spazio: number) {
  let cx = x
  for (const ch of testo.toUpperCase()) {
    page.drawText(ch, { x: cx, y, size, font, color: colore })
    cx += font.widthOfTextAtSize(ch, size) + spazio
  }
  return cx - x
}

function aCapo(testo: string, font: PDFFont, size: number, largh: number): string[] {
  const righe: string[] = []
  for (const paragrafo of testo.split('\n')) {
    const parole = paragrafo.split(/\s+/).filter(Boolean)
    let riga = ''
    for (const w of parole) {
      const prova = riga ? `${riga} ${w}` : w
      if (font.widthOfTextAtSize(prova, size) <= largh) riga = prova
      else { if (riga) righe.push(riga); riga = w }
    }
    righe.push(riga)
  }
  return righe
}

class Impaginatore {
  pdf!: PDFDocument
  reg!: PDFFont
  sb!: PDFFont
  logo!: PDFImage
  page!: PDFPage
  y = 0
  n = 0                 // numero di pagina di contenuto
  usata = false         // c'e' gia' qualcosa su questa pagina?
  // IL SEGNO A PENNARELLO (regole dei documenti): la sottolineatura sotto il
  // titolo di pagina, il tratto corto in chiusura. Uno per pagina: si nota
  // perche' e' raro, e sui documenti formali non c'e' proprio.
  segnoSotto?: PDFImage
  segnoTratto?: PDFImage
  segnato = false       // gia' segnata questa pagina?
  readonly doc: Documento
  constructor(doc: Documento) { this.doc = doc }

  nuovaPagina(prima = false) {
    this.page = this.pdf.addPage([A4.w, A4.h])
    this.segnato = false
    this.n += 1
    this.y = A4.h - MARG.alto
    this.usata = false
    if (prima) {
      // il logo in alto a sinistra, 15 mm di altezza, poi aria
      const h = 15 * MM
      const w = h * (this.logo.width / this.logo.height)
      this.page.drawImage(this.logo, { x: MARG.sinistra, y: this.y - h, width: w, height: h })
      this.y -= h + 9 * MM
    } else {
      // la testata delle pagine interne: il tipo a sinistra, lo Studio a destra
      const y = A4.h - MARG.alto + 5 * MM
      spaziato(this.page, this.doc.tipo, MARG.sinistra, y, this.sb, 7.4, BLU, 1.2)
      const t = 'Studio Galilei'
      this.page.drawText(t, { x: A4.w - MARG.destra - this.sb.widthOfTextAtSize(t, 7.4), y, size: 7.4, font: this.sb, color: BLU })
    }
    // il numero di pagina, in basso a destra (non sulla prima)
    if (!prima) {
      const t = String(this.n)
      this.page.drawText(t, { x: A4.w - MARG.destra - this.reg.widthOfTextAtSize(t, 8), y: MARG.basso - 6 * MM, size: 8, font: this.reg, color: BLU })
    }
  }

  serve(h: number) {
    if (this.y - h < MARG.basso) this.nuovaPagina()
  }

  paragrafo(testo: string, size = CORPO, font = this.reg, colore = NERO, largh = LARGH, x = MARG.sinistra, dopo = 8) {
    const righe = aCapo(testo, font, size, largh)
    const lh = size * INTERLINEA
    for (const r of righe) {
      this.serve(lh)
      this.page.drawText(r, { x, y: this.y - size, size, font, color: colore })
      this.y -= lh
    }
    this.y -= dopo
  }

  // quanto e' alto un testo a capo, per non spezzare male
  altezza(testo: string, size: number, font: PDFFont, largh: number) {
    return aCapo(testo, font, size, largh).length * size * INTERLINEA
  }

  blocco(b: Blocco) {
    const pg = () => this.page
    if (b.tipo === 'pagina') {
      // si volta pagina solo se questa e' usata per davvero: sotto un quarto
      // si continua, perche' una pagina quasi vuota e' peggio di un capitolo
      // che comincia a meta' (Dre: niente lasciato al caso)
      const usato = (A4.h - MARG.alto - this.y) / (A4.h - MARG.alto - MARG.basso)
      if (this.usata && usato >= 0.25) this.nuovaPagina()
      else if (this.usata) this.y -= 8 * MM
      return
    }
    this.usata = true
    switch (b.tipo) {
      case 'kicker': {
        this.serve(7.4 * 2)
        if (this.y > A4.h - MARG.alto - 1) this.y -= 2 * MM
        spaziato(pg(), b.testo, MARG.sinistra, this.y - 7.4, this.sb, 7.4, BLU, 1.6)
        this.y -= 7.4 + 3 * MM
        break
      }
      case 'h1': {
        this.paragrafo(b.testo, 22, this.sb, NERO, 145 * MM, MARG.sinistra, 4 * MM)
        // la mano che passa sotto il titolo: larga circa meta' del titolo
        if (this.segnoSotto && !this.segnato) {
          const largo = Math.min(145 * MM, this.sb.widthOfTextAtSize(b.testo, 22)) * 0.5
          const alto = largo * (this.segnoSotto.height / this.segnoSotto.width)
          pg().drawImage(this.segnoSotto, { x: MARG.sinistra, y: this.y + 2.5 * MM, width: largo, height: alto })
          this.segnato = true
          this.y -= alto * 0.6
        }
        break
      }
      case 'h2': {
        this.serve(12 * INTERLINEA + 4 * MM + 3 * CORPO * INTERLINEA)
        this.y -= 4 * MM
        this.paragrafo(b.testo, 12, this.sb, NERO, LARGH, MARG.sinistra, 2 * MM)
        break
      }
      case 'p': this.paragrafo(b.testo, b.piccolo ? 8.4 : CORPO, this.reg, b.piccolo ? GRIGIO : NERO, 152 * MM); break
      case 'numeri': {
        // i numeri grandi in fila: il dato prima dell'aggettivo, in Blu SG
        const n = Math.max(1, Math.min(4, b.voci.length))
        const colW = LARGH / n
        const h = 46 * 1.05 + 2 * MM + 8 * 1.5 * 2 + 6 * MM
        this.serve(h)
        const top = this.y
        // la misura piu' grande che ci sta per tutti: 40 pt se possibile, meno se i numeri sono lunghi
        const misura = Math.min(40, ...b.voci.slice(0, 4).map((v) => 40 * (colW - 5 * MM) / Math.max(1, this.sb.widthOfTextAtSize(v.valore, 40))))
        b.voci.slice(0, 4).forEach((v, i) => {
          const x = MARG.sinistra + i * colW
          pg().drawText(v.valore, { x, y: top - 40, size: misura, font: this.sb, color: BLU })
          let y = top - 40 - 3 * MM
          for (const r of aCapo(v.etichetta.toUpperCase(), this.sb, 7, colW - 6 * MM)) {
            spaziato(pg(), r, x, y - 7, this.sb, 7, GRIGIO, 0.9); y -= 7 * 1.6
          }
        })
        this.y = top - h
        break
      }
      case 'spazio': this.y -= b.mm * MM; break
      case 'anagrafica': {
        const colW = LARGH / b.colonne.length
        const h = Math.max(...b.colonne.map((c) => 8 * 1.5 + c.righe.length * CORPO * 1.45)) + 6 * MM
        this.serve(h)
        const top = this.y
        b.colonne.forEach((c, i) => {
          const x = MARG.sinistra + i * colW
          let y = top
          spaziato(pg(), c.titolo, x, y - 7, this.sb, 7, BLU, 1)
          y -= 7 + 2.5 * MM
          for (const r of c.righe) { pg().drawText(r, { x, y: y - CORPO, size: CORPO, font: this.reg, color: NERO }); y -= CORPO * 1.45 }
        })
        this.y = top - h
        break
      }
      case 'elenco': {
        for (const v of b.voci) {
          const largh = LARGH - 6 * MM
          const h = this.altezza(v, CORPO, this.reg, largh)
          this.serve(h + 3)
          pg().drawRectangle({ x: MARG.sinistra, y: this.y - CORPO + 1.5, width: 3.2, height: 3.2, color: BLU })
          this.paragrafo(v, CORPO, this.reg, NERO, largh, MARG.sinistra + 6 * MM, 3)
        }
        this.y -= 5
        break
      }
      case 'due_colonne': {
        const gap = 8 * MM
        const colW = (LARGH - gap) / 2
        const alt = (c: { titolo: string; voci: string[] }) => 8 + 3 * MM + c.voci.reduce((t, v) => t + this.altezza(v, CORPO, this.reg, colW - 6 * MM) + 3, 0)
        const h = Math.max(alt(b.sinistra), alt(b.destra))
        this.serve(h)
        const top = this.y
        ;[b.sinistra, b.destra].forEach((c, i) => {
          const x = MARG.sinistra + i * (colW + gap)
          this.y = top
          spaziato(pg(), c.titolo, x, this.y - 7, this.sb, 7, BLU, 1)
          this.y -= 7 + 3 * MM
          for (const v of c.voci) {
            pg().drawRectangle({ x, y: this.y - CORPO + 1.5, width: 3.2, height: 3.2, color: BLU })
            this.paragrafo(v, CORPO, this.reg, NERO, colW - 6 * MM, x + 6 * MM, 3)
          }
        })
        this.y = top - h - 4 * MM
        break
      }
      case 'riquadro': {
        const pad = 5 * MM
        const largh = LARGH - pad * 2 - 6 * MM
        const h = pad + 8 + 3 * MM + b.voci.reduce((t, v) => t + this.altezza(v, CORPO, this.reg, largh) + 3, 0) + pad
        this.serve(h)
        pg().drawRectangle({ x: MARG.sinistra, y: this.y - h, width: LARGH, height: h, color: LAVANDA })
        const top = this.y
        this.y -= pad
        spaziato(pg(), b.titolo, MARG.sinistra + pad, this.y - 7, this.sb, 7, BLU, 1)
        this.y -= 7 + 3 * MM
        for (const v of b.voci) {
          pg().drawRectangle({ x: MARG.sinistra + pad, y: this.y - CORPO + 1.5, width: 3.2, height: 3.2, color: BLU })
          this.paragrafo(v, CORPO, this.reg, NERO, largh, MARG.sinistra + pad + 6 * MM, 3)
        }
        this.y = top - h - 5 * MM
        break
      }
      case 'tappe': {
        const n = b.tappe.length
        const colW = LARGH / n
        const testoW = colW - 8 * MM
        const righeTitolo = Math.max(...b.tappe.map((t) => aCapo(t.titolo, this.sb, 10.4, testoW).length))
        const h = 7 * MM + 3.5 * MM + 7.2 + 1.5 * MM + 10.4 * 1.3 * righeTitolo + 2 * MM + Math.max(...b.tappe.map((t) => aCapo(t.testo, this.reg, 8.6, testoW).length * 8.6 * 1.42)) + 4 * MM
        this.serve(h)
        const top = this.y
        b.tappe.forEach((t, i) => {
          const x = MARG.sinistra + i * colW
          const cy = top - 1.6 * MM - 1.6 * MM
          pg().drawCircle({ x: x + 1.6 * MM, y: cy, size: 1.6 * MM, color: BLU })
          if (i < n - 1) pg().drawRectangle({ x: x + 3.2 * MM, y: cy - 0.35 * MM, width: colW - 3.2 * MM, height: 0.7 * MM, color: SOFFICE })
          let y = top - 7 * MM - 3.5 * MM
          spaziato(pg(), t.quando, x, y - 7.2, this.sb, 7.2, BLU, 1.1)
          y -= 7.2 + 1.5 * MM
          for (const r of aCapo(t.titolo, this.sb, 10.4, testoW)) { pg().drawText(r, { x, y: y - 10.4, size: 10.4, font: this.sb, color: NERO }); y -= 10.4 * 1.3 }
          y -= 2 * MM
          for (const r of aCapo(t.testo, this.reg, 8.6, testoW)) { pg().drawText(r, { x, y: y - 8.6, size: 8.6, font: this.reg, color: NERO }); y -= 8.6 * 1.42 }
        })
        this.y = top - h
        break
      }
      case 'tabella': {
        const tot = b.colonne.reduce((t, c) => t + c.larghezza, 0)
        const xs: number[] = []
        let acc = MARG.sinistra
        for (const c of b.colonne) { xs.push(acc); acc += (c.larghezza / tot) * LARGH }
        const wDi = (i: number) => (b.colonne[i].larghezza / tot) * LARGH
        const pad = 2.5 * MM
        // intestazione
        this.serve(9 * MM)
        pg().drawRectangle({ x: MARG.sinistra, y: this.y - 0.6, width: LARGH, height: 0.6, color: BLU })
        this.y -= 2.5 * MM
        b.colonne.forEach((c, i) => {
          const w = this.sb.widthOfTextAtSize(c.testo.toUpperCase(), 7.4) + 1.1 * c.testo.length
          const x = c.destra ? xs[i] + wDi(i) - pad - w : xs[i] + (i === 0 ? 0 : pad)
          spaziato(pg(), c.testo, x, this.y - 7.4, this.sb, 7.4, BLU, 1.1)
        })
        this.y -= 7.4 + 2.5 * MM
        pg().drawRectangle({ x: MARG.sinistra, y: this.y, width: LARGH, height: 0.4, color: SOFFICE })
        // righe
        for (const riga of b.righe) {
          const alt = Math.max(...riga.map((cella, i) => {
            const w = wDi(i) - pad * (i === 0 ? 1 : 2)
            return this.altezza(cella.testo, cella.forte ? 10.5 : 9.2, cella.forte ? this.sb : this.reg, w) + (cella.sotto ? this.altezza(cella.sotto, 8, this.reg, w) : 0)
          })) + 2 * pad
          this.serve(alt)
          const top = this.y
          riga.forEach((cella, i) => {
            const w = wDi(i) - pad * (i === 0 ? 1 : 2)
            const size = cella.forte ? 10.5 : 9.2
            const font = cella.forte ? this.sb : this.reg
            let y = top - pad
            const righeT = aCapo(cella.testo, font, size, w)
            for (const r of righeT) {
              const tw = font.widthOfTextAtSize(r, size)
              const x = b.colonne[i].destra ? xs[i] + wDi(i) - pad - tw : xs[i] + (i === 0 ? 0 : pad)
              pg().drawText(r, { x, y: y - size, size, font, color: NERO }); y -= size * INTERLINEA
            }
            if (cella.sotto) for (const r of aCapo(cella.sotto, this.reg, 8, w)) {
              const tw = this.reg.widthOfTextAtSize(r, 8)
              const x = b.colonne[i].destra ? xs[i] + wDi(i) - pad - tw : xs[i] + (i === 0 ? 0 : pad)
              pg().drawText(r, { x, y: y - 8, size: 8, font: this.reg, color: GRIGIO }); y -= 8 * INTERLINEA
            }
          })
          this.y = top - alt
          pg().drawRectangle({ x: MARG.sinistra, y: this.y, width: LARGH, height: 0.4, color: SOFFICE })
        }
        this.y -= 3 * MM
        break
      }
    }
  }

  copertina(c: Copertina, sfondo?: PDFImage, logoBianco?: PDFImage) {
    const page = this.pdf.addPage([A4.w, A4.h])
    if (sfondo) page.drawImage(sfondo, { x: 0, y: 0, width: A4.w, height: A4.h })
    else page.drawRectangle({ x: 0, y: 0, width: A4.w, height: A4.h, color: BLU })
    // il logo bianco non ce l'abbiamo come PNG qui: sulla copertina va il nome, in bianco
    let y = A4.h - MARG.alto
    if (logoBianco) {
      const h = 15 * MM
      page.drawImage(logoBianco, { x: MARG.sinistra, y: y - h, width: h * (logoBianco.width / logoBianco.height), height: h })
    } else {
      page.drawText('StudioGalilei', { x: MARG.sinistra, y: y - 14, size: 14, font: this.sb, color: BIANCO })
    }
    if (c.riferimento) {
      const t = c.riferimento
      page.drawText(t, { x: A4.w - MARG.destra - this.sb.widthOfTextAtSize(t, 8), y: y - 10, size: 8, font: this.sb, color: BIANCO })
      if (c.data) page.drawText(c.data, { x: A4.w - MARG.destra - this.reg.widthOfTextAtSize(c.data, 8), y: y - 10 - 12, size: 8, font: this.reg, color: BIANCO, opacity: 0.85 })
    }
    if (c.cliente) page.drawText(c.cliente, { x: MARG.sinistra, y: y - 15 * MM - 7 * MM, size: 10.5, font: this.reg, color: BIANCO })
    // il titolo nel primo terzo: e' l'unica cosa che si legge in anteprima
    y = A4.h - 78 * MM
    spaziato(page, c.occhiello, MARG.sinistra, y, this.sb, 8, BIANCO, 1.8)
    y -= 8 + 5 * MM
    for (const r of aCapo(c.titolo, this.sb, 30, 150 * MM)) { page.drawText(r, { x: MARG.sinistra, y: y - 30, size: 30, font: this.sb, color: BIANCO }); y -= 30 * 1.12 }
    if (c.sottotitolo) {
      y -= 3 * MM
      for (const r of aCapo(c.sottotitolo, this.reg, 11, 140 * MM)) { page.drawText(r, { x: MARG.sinistra, y: y - 11, size: 11, font: this.reg, color: BIANCO, opacity: 0.92 }); y -= 11 * 1.5 }
    }
  }
}

export async function generaPdf(doc: Documento, r: Risorse): Promise<Uint8Array> {
  const problemi = controllaTono(testoDi(doc))
  if (problemi.length) throw new Error(`Il testo non passa il controllo del tono: ${problemi.join(', ')}`)
  const imp = new Impaginatore(doc)
  imp.pdf = await PDFDocument.create()
  imp.pdf.registerFontkit(fontkit)
  imp.reg = await imp.pdf.embedFont(r.regular, { subset: true })
  imp.sb = await imp.pdf.embedFont(r.semibold, { subset: true })
  imp.logo = await imp.pdf.embedPng(r.logo)
  // i documenti formali (condizioni economiche, contratti) restano sobri
  if (!doc.formale && r.segni) {
    if (r.segni.sottolineatura) imp.segnoSotto = await imp.pdf.embedPng(r.segni.sottolineatura)
    if (r.segni.tratto) imp.segnoTratto = await imp.pdf.embedPng(r.segni.tratto)
  }
  imp.pdf.setTitle(doc.copertina?.titolo ?? doc.tipo)
  imp.pdf.setAuthor('Studio Galilei')
  imp.pdf.setProducer('SG Workspace')
  if (doc.copertina) {
    const s = r.sfondi?.[doc.copertina.linea]
    imp.copertina(doc.copertina, s ? await imp.pdf.embedPng(s) : undefined, r.logoBianco ? await imp.pdf.embedPng(r.logoBianco) : undefined)
  }
  imp.nuovaPagina(true)
  for (const b of doc.blocchi) imp.blocco(b)
  if (imp.segnoTratto) {
    // il tratto che chiude: in fondo all'ultima pagina, sopra la firma
    const largo = 26 * MM
    const alto = largo * (imp.segnoTratto.height / imp.segnoTratto.width)
    const y = Math.max(MARG.basso + 4 * MM, imp.y - 6 * MM)
    imp.page.drawImage(imp.segnoTratto, { x: MARG.sinistra, y, width: largo, height: alto })
  }
  if (doc.piede) {
    const t = doc.piede
    const y = MARG.basso - 6 * MM
    let x = MARG.sinistra
    for (const [testo, font] of [['Studio Galilei', imp.sb], ['studiogalilei.com', imp.reg], [t, imp.reg]] as Array<[string, PDFFont]>) {
      imp.page.drawText(testo, { x, y, size: 8, font, color: BLU })
      x += font.widthOfTextAtSize(testo, 8) + 6 * MM
    }
  }
  return imp.pdf.save()
}

