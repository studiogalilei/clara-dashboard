#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA PRIMA RISPOSTA AUTOMATICA (Dre, 29/9/2026, chiesta due volte).

PERCHE'
Chi risponde «si', mandatemi l'analisi» aspettava ore, a volte un giorno,
che Dre copiasse e incollasse. Dre, 29/9: la prima risposta parte da sola,
con l'analisi e la presentazione dello Studio in allegato. «Risponde solo ai
primi che arrivano»: i no, i rinvii, i follow-up e i casi strani restano suoi
(caso Orange Seed).

COSA FA, e cosa NON fa
Non manda niente. Approva, al posto del clic di Dre, SOLO le bozze che passano
tutto il cancello qui sotto; l'invio resta a manda.py, che ha gia' tutto
(ricontrollo di contattabile e del cancello qualita', thread giusto, analisi e
presentazione allegate e verificate, lucchetto). Il resto resta in Posta.

IL CANCELLO, condizione per condizione (tutte, nessuna esclusa):
  - bozza pronta (tipo «risposta»), non «Da guardare tu»;
  - prima risposta vera: nessun gruppo (ne' follow-up, ne' ripresa, ne' gigante
    buono), analisi mai mandata, niente di nostro dopo la loro ultima mail;
  - la persona e' positiva o tiepida, e l'intento e' uno di quelli «vuole
    sapere di piu'» (INTENTI_OK);
  - niente no, niente autorisposta, niente casella di servizio, niente
    inoltro a un collega o indirizzo diverso: quelli sono casi strani;
  - l'analisi c'e' in PDF;
  - seconda testa COERENTE, e la mail loro e' ancora quella su cui e' nata
    la bozza (si rilegge il filo adesso, non ci si fida di quello di ieri);
  - contattabile (regola Zafferano), mai due volte alla stessa persona;
  - lun-ven, 9-17 ora di Roma; al massimo 5 per giro e 15 al giorno.
Poi IL REVISORE rilegge ogni singola mail sapendo che partira' davvero:
«OK» e la bozza passa ad «approvata», qualunque altra cosa e resta a Dre con
una nota in chat. Ferma, non esegue.

GLI INTERRUTTORI
Due, nella sala di controllo: «prima_risposta» (questo) e «manda». Nascono
spenti. Questo script non approva niente se uno dei due e' spento, nemmeno
lanciato a mano: con «manda» spento le approvate resterebbero ferme e
invisibili, fuori dalla Posta di Dre.

L'OMBRA (29/9, dalla ricerca: Ramp, Instantly, e il video stesso: «gli agenti
girano in sottofondo prima di toccare qualcosa di vero»). Con --ombra fa tutto
il lavoro, Revisore compreso, ma NON approva: scrive sulla bozza cosa avrebbe
fatto (azione.ombra) e la bozza resta a Dre. Serve solo l'interruttore
prima_risposta. Dopo circa 50 casi si confronta la sua scelta con quello che
Dre ha davvero mandato (e corretto): se non ha mai detto «parte» a una mail che
Dre avrebbe fermato o cambiato nella sostanza, si toglie --ombra.

USO
  python3 scripts/prima_risposta.py --prova   chi passerebbe, col Revisore vero, senza scrivere
  python3 scripts/prima_risposta.py --ombra   decide e lo scrive, ma non approva (solo prima_risposta acceso)
  python3 scripts/prima_risposta.py           approva (solo a interruttori accesi)
"""

import datetime
import os
import re
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara, contattabile, quando          # noqa: E402

PROVA = "--prova" in sys.argv
OMBRA = "--ombra" in sys.argv
# I SEGUITI (Dre 29/9, strada A): con --seguiti la stessa porta vale per i follow-up
# scritti dal codice col template di Dre. Interruttore suo («seguiti»), firma sua,
# tetto suo; al posto del Revisore il codice riscrive il testo e lo confronta.
SEGUITI = "--seguiti" in sys.argv
CHIAVE = "seguiti" if SEGUITI else "prima_risposta"
FIRMA_SEGUITI = "seguito-automatico (decisione Dre 29/9, strada A)"
MAX_SEGUITI_AL_GIORNO = 15
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
FIRMA = "prima-risposta-automatica (decisione Dre 29/9)"
MAX_PER_GIRO = 5                 # per giro: la fila resta umana
MAX_AL_GIORNO = 15               # era 5 la prima settimana; alzato il 2/10 su ordine di Dre («tanti senza risposta»), dopo un 1/10 pulito          # Dre 29/9: 5 al giorno la prima settimana, poi si sale a 15 se va
ORE = (9, 17)                              # dalle 9 alle 16:59, ora di Roma
CLASSI_OK = ("positivo", "tiepido")
# dal playbook: vuole l'analisi, vuole parlare, chi siete, vuole il materiale
# ma non la call. Il resto (rinvii, inoltri, obiezioni, prezzo, «come ci avete
# trovato») e' una conversazione, non una prima risposta: resta a Dre.
# INT-GB dal 2/10 (Dre: «anche i negativi, ricordati, comunque gli inviamo l'analisi
# e lasciamo il calendario, senza proporre una data, porta aperta e basta»): anche il
# gigante buono e' la consegna della prima risposta. I suoi freni restano tutti:
# mai una data (cancello detto_no), mai a chi chiede di non essere contattato.
INTENTI_OK = ("INT-01", "INT-02", "INT-03", "INT-23", "INT-GB")
# 2/10: il gigante buono dice «gliela lasciamo in allegato», e «le lascio» non bastava
ALLEGA_ANALISI = re.compile(r"(?:inoltr|alleg|lasci|ecco|trova qui|mand|invi)\w*[^.\n]{0,60}\banalisi\b|"
                            r"\banalisi\b[^\n]{0,160}?gliel[ao] lasci\w* in allegato|"
                            r"\banalisi\b[^.\n]{0,60}(?:in allegato|allegat|qui sotto)")
CAMPI = ("id,email,email_alt,company,name,classificazione,stage,pipeline_stage,fuori,no_followup,notes,owner,"
         "analysis_sent,analysis_pdf,campaign,campaign_id,lead_id,last_reply_at")


def finestra(ora):
    """Lun-ven, dalle 9 alle 17 a Roma. Una mail automatica alle 23 non sembra una persona."""
    ora = ora.astimezone(ROMA)
    return ora.weekday() < 5 and ORE[0] <= ora.hour < ORE[1]


def interruttori(ops, ombra=False, chiave="prima_risposta"):
    """Tutti e due accesi, o niente. Torna il motivo se non si parte. In ombra
    non si approva niente, quindi basta il suo: manda puo' restare spento."""
    stato = {o["chiave"]: bool(o.get("attiva")) for o in ops}
    if chiave not in stato:
        return f"l'operazione {chiave} non esiste in tabella"
    spenti = [k for k in ((chiave,) if ombra else (chiave, "manda")) if not stato.get(k)]
    return f"interruttore spento: {', '.join(spenti)}" if spenti else None


GIORNI_CONTATTO = 60
# LE RIGHE DI SERVIZIO (29/9). Nelle note ci sono anche righe scritte dal sistema che
# dicono solo «era in ferie»: sono il motivo del ricontatto, non un contatto con una
# persona. Si riconoscono dal formato esatto; tutto il resto resta un motivo per fermarsi.
_SERVIZIO = re.compile(r"^(?:OOO: rientra il \d{4}-\d{2}-\d{2}.*"
                       r"|Pulizia del \d{1,2}/\d{1,2} \(Achille\): (?:risposta automatica o ferie ormai passate, nessuna risposta vera|ferie fino al .*))$")


def note_vere(testo):
    """La nota senza le righe di servizio: quello che ha scritto una persona."""
    return "\n".join(r for r in (testo or "").splitlines() if r.strip() and not _SERVIZIO.match(r.strip())).strip()


def contatti_fuori(p, giorni=GIORNI_CONTATTO):
    """SIAMO GIA' IN CONTATTO FUORI DA SMARTLEAD? (Dre, 29/9: «molto importante
    non mandare follow-up a chi stiamo gia' sentendo: per questo tracciare le
    attivita' e' importante, gmail, transcript, discorsi, calendario»).
    Si guarda tutto quello che il sistema raccoglie, negli ultimi 60 giorni. Basta
    una traccia e la mail non parte da sola: la decide una persona. Torna i motivi."""
    pid = p["id"]
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%SZ")
    no = []
    nota = note_vere(p.get("notes"))
    if nota:
        no.append(f"c'e' una nota fuori binario: «{' '.join(nota.split())[:60]}»")
    if p.get("owner"):
        no.append("qualcuno l'ha presa in carico")
    righe = sb("GET", f"/rest/v1/interactions?select=kind,at,ref&prospect_id=eq.{pid}&at=gte.{da}"
                      f"&or=(kind.in.(call,transcript,nota,postit),ref.like.gmail:*)&order=at.desc&limit=5") or []
    for r in righe[:1]:
        cosa = "una mail da Gmail" if (r.get("ref") or "").startswith("gmail:") else {"call": "una call", "transcript": "una call registrata",
                                                                                       "nota": "una nota", "postit": "un post-it"}.get(r["kind"], r["kind"])
        no.append(f"{cosa} del {r['at'][:10]}, fuori da Smartlead")
    ag = sb("GET", f"/rest/v1/agenda?select=at,titolo&prospect_id=eq.{pid}&at=gte.{da}&order=at.desc&limit=1") or []
    if ag:
        no.append(f"in calendario: «{ag[0]['titolo'][:40]}» il {ag[0]['at'][:10]}")
    if sb("GET", f"/rest/v1/task?select=id&prospect_id=eq.{pid}&fatta=eq.false&limit=1"):
        no.append("c'e' una task aperta su questa azienda")
    return no


def perche_no_seguito(pr, p):
    """Il cancello dei follow-up scritti dal codice. Vuota = passa."""
    import seguiti
    az = pr.get("azione") or {}
    let = az.get("lettura") or {}
    gruppo = let.get("gruppo")
    no = []
    if pr.get("tipo") != "risposta" or str(pr.get("titolo") or "").startswith("Da guardare tu"):
        no.append("e' da guardare")
    if az.get("approvata_da") or az.get("prima_risposta"):
        no.append("gia' passata di qui")
    if gruppo not in seguiti.GRUPPI_DAL_CODICE:
        no.append(f"non e' un follow-up col template ({gruppo or 'prima risposta'})")
    if not az.get("testo_dal_codice"):
        no.append("il testo l'ha scritto il modello, non il codice")
    if let.get("coerenza") != "COERENTE":
        no.append("la seconda testa non dice COERENTE")
    if let.get("detto_no"):
        no.append("ha detto no")
    # 2/10: un alias dello STESSO dominio (info@ che risponde per commerciale@) non e'
    # un rimbalzo a terzi: si risponde nel thread come sempre. Il freno resta per i
    # domini diversi (vero passaggio di persona) e per i cambi di indirizzo dichiarati.
    _dom = ((p or {}).get("email") or "").split("@")[-1].lower()
    _fuori = [g for g in (let.get("girato_a") or []) if g.split("@")[-1].lower() != _dom]
    if _fuori or let.get("destinatario") or (p or {}).get("email_alt"):
        no.append("c'e' di mezzo un altro indirizzo")
    if not p:
        return no + ["manca la scheda"]
    if not contattabile(p) or p.get("classificazione") in ("negativo",):
        no.append("non e' piu' un lead")
    if gruppo in ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO") and not p.get("analysis_pdf"):
        no.append("l'analisi in PDF non c'e'")
    if "usa" in (p.get("campaign") or "").lower():
        no.append("campagna USA")
    return no


def perche_no(pr, p):
    """Il cancello sui fatti gia' scritti. Torna i motivi: vuota vuol dire che passa."""
    az = pr.get("azione") or {}
    let = az.get("lettura") or {}
    gb = az.get("intento") == "INT-GB"      # il gigante buono: il no E' il suo caso (Dre, 2/10)
    no = []
    if pr.get("tipo") != "risposta" or str(pr.get("titolo") or "").startswith("Da guardare tu"):
        no.append("e' da guardare")
    if not (az.get("bozza") or "").strip():
        no.append("manca la bozza")
    # DAL BANCO DI PROVA (29/9, 70 risposte vere di Dre): alla prima risposta Dre
    # manda SEMPRE l'analisi, anche a chi chiede solo «una chiacchierata»
    # (Yachtspassion), e propone SEMPRE la call col calendario, anche a chi dice
    # «niente budget quest'anno» (Optima, Mason). Le bozze che non lo fanno non
    # partono da sole: il PDF partirebbe allegato a una mail che non lo nomina.
    # Non basta nominarla: «vediamo insieme l'analisi in call» (Yachtspassion,
    # Abiovet) con il PDF attaccato e' una mail che non sa cosa porta.
    testo = (az.get("bozza") or "").lower()
    if not ALLEGA_ANALISI.search(testo):
        no.append("la bozza non dice che l'analisi e' allegata")
    if "calendar.app.google" not in testo:
        no.append("la bozza non lascia il calendario")
    if az.get("approvata_da") or az.get("prima_risposta"):
        no.append("gia' passata di qui")
    if let.get("gruppo") and not (gb and let.get("gruppo") == "GIGANTE BUONO"):
        no.append(f"non e' una prima risposta ({let['gruppo']})")
    if az.get("intento") not in INTENTI_OK:
        no.append(f"intento {az.get('intento')} fuori dalla prima risposta")
    if let.get("coerenza") != "COERENTE":
        no.append("la seconda testa non dice COERENTE")
    if let.get("scritto_dopo_di_lei"):
        no.append("abbiamo gia' scritto dopo la sua ultima mail")
    if let.get("non_scrivere"):
        no.append("ha chiesto di non essere contattato")
    if let.get("detto_no") and not gb:
        no.append("ha detto no")
    if let.get("autorisposta"):
        no.append("autorisposta")
    if let.get("casella_di_servizio"):
        no.append("casella di servizio")
    # 2/10: un alias dello STESSO dominio (info@ che risponde per commerciale@) non e'
    # un rimbalzo a terzi: si risponde nel thread come sempre. Il freno resta per i
    # domini diversi (vero passaggio di persona) e per i cambi di indirizzo dichiarati.
    _dom = ((p or {}).get("email") or "").split("@")[-1].lower()
    _fuori = [g for g in (let.get("girato_a") or []) if g.split("@")[-1].lower() != _dom]
    if _fuori or let.get("destinatario") or (p or {}).get("email_alt"):
        no.append("c'e' di mezzo un altro indirizzo")
    if let.get("analisi_ricevuta") or let.get("analisi_gia_letta"):
        no.append("l'analisi l'ha gia' avuta")
    if not p:
        no.append("manca la scheda")
        return no
    if p.get("classificazione") not in CLASSI_OK and not (az.get("intento") == "INT-GB" and p.get("classificazione") == "negativo"):
        no.append(f"e' {p.get('classificazione')}, non positivo o tiepido")
    if not contattabile(p):
        no.append("non e' piu' un lead")
    if p.get("analysis_sent"):
        no.append("l'analisi risulta gia' mandata")
    if not p.get("analysis_pdf"):
        no.append("l'analisi in PDF non c'e'")
    if "usa" in (p.get("campaign") or "").lower():
        no.append("campagna USA")
    return no


def verdetto_revisore(testo):
    """Solo un «OK» netto fa passare. Tutto il resto, anche il silenzio, resta a Dre."""
    t = " ".join((testo or "").split()).strip()
    parola = t.split()[0].strip(".:,!").upper() if t else ""
    return ("OK", "") if parola == "OK" else ("STOP", (t.split(":", 1)[1].strip() if ":" in t else t)[:200] or "nessuna risposta")


def _template_approvati():
    """Le prime risposte del file dei template di Dre (29/9, dal banco di prova: il
    Revisore fermava La Baita Case per «una proposta con garanzia non verificata»,
    che e' una frase del template di Dre. Chi giudica deve sapere cosa e' gia' approvato)."""
    try:
        import bozze
        t = bozze.template_verbatim()
        fine = t.find("RIPRESA (25/9")                     # dopo iniziano riprese e follow-up: non servono qui
        return (t[:fine] if fine > 0 else t)[:9000]
    except Exception:                                    # noqa: BLE001
        return "(template non caricati)"


def rilettura_seguito(pr, p, letti):
    """Per i seguiti il controllo non lo fa un modello: il codice riscrive il testo
    adesso, col filo di adesso, e deve venire identico a quello in Posta. Se Dre
    l'ha corretto, o il saluto o il template sono cambiati, resta a lui."""
    import seguiti
    import bozze
    az = pr.get("azione") or {}
    gruppo = (az.get("lettura") or {}).get("gruppo")
    giorno = az.get("giorno_proposto")
    if giorno and seguiti.giorno_passato(giorno):
        return "STOP", f"propone {giorno}, che e' gia' passato: va rifatta"
    ora = seguiti.testo(gruppo, p, letti, bozze.CALENDARIO, giorno=giorno)
    if not ora:
        return "STOP", "il codice non sa piu' scriverlo da solo (template o regola cambiati)"
    if ora.strip() != (az.get("bozza") or "").strip():
        return "STOP", "il testo in Posta non e' piu' il template parola per parola"
    return "OK", ""


def revisore(pr, p, letti):
    """Il Revisore rilegge la mail sapendo che partira' davvero, senza nessuno dopo di lui."""
    try:
        import cervello
        az = pr.get("azione") or {}
        azienda = p.get("company") or p.get("name") or p["email"]
        prompt = f"""{cervello.ruolo("revisore")}Sei il REVISORE di Studio Galilei. Questa mail PARTIRA' DAVVERO, in automatico,
senza che Dre la legga prima. Dopo di te non c'e' nessuno. Il tuo compito: dire se puo' partire cosi'.

I TESTI APPROVATI DA DRE, parola per parola. Quello che la mail dice con queste frasi (la proposta con
garanzia, il calendario, il doc di presentazione, «centrata principalmente sulla comunicazione su Google»)
e' approvato da lui: non e' un impegno inventato e non e' un motivo per fermarla.
NEL GIGANTE BUONO (la risposta a un no cortese) Dre ha deciso il 30/9 e l'1-2/10: si lascia l'analisi
gia' pronta, un saluto cordiale, la porta aperta ANCHE su «AI e software su misura, con la finanza
agevolata come leva» (parole sue: il «senza software» del 29/9 vale per le altre mail, NON per questo
saluto ai no), e il link del calendario in fondo SENZA proporre una data. Tutto questo e' voluto.
I numeri di zona (ricerche al mese, recensioni) vengono dal fit misurato dal codice: sono ammessi.
{_template_approvati()}

A CHI: {azienda} ({p['email']}), classificato {p.get('classificazione')}, intento {az.get('intento')}.
IN ALLEGATO partiranno: l'analisi Google Ads in PDF fatta per loro e la presentazione dello Studio.

L'ULTIMA MAIL LORO ({letti.get('ultima_loro_il') or 'data ignota'}):
{letti.get('ultima_loro') or '(nessuna)'}

L'ULTIMA MAIL NOSTRA ({letti.get('ultima_nostra_il') or 'mai'}), mandata PRIMA della loro:
{letti.get('ultima_nostra') or '(nessuna)'}

LA MAIL CHE PARTE:
{az.get('bozza')}

Fermala se: non risponde a quello che hanno chiesto; promette cose che l'allegato non contiene o che lo Studio
non fa; sbaglia nome o azienda; ha un tono che una persona attenta non userebbe; contiene numeri, prezzi o
impegni che nessuno ha verificato; la loro mail chiede qualcosa che solo Dre puo' decidere (prezzo, contratto,
accordi, un collega da coinvolgere); qualunque cosa ti farebbe dire «questa la fa vedere a Dre prima».
Falla passare se e' una risposta naturale e corretta a chi ha chiesto di saperne di piu'.

Rispondi SOLO con una riga: «OK» oppure «STOP: motivo in venti parole»."""
        modello = "gpt-5" if cervello.FORNITORE == "openai" else None
        return verdetto_revisore(cervello._chiedi(prompt, modello))
    except Exception as e:                                   # noqa: BLE001
        return "STOP", f"il Revisore non ha potuto leggere ({str(e)[:60]})"


def segna(pr, az, patch_extra=None, solo_se_aperta=True):
    """Scrive sulla proposta solo se e' ancora aperta: se Dre l'ha toccata nel frattempo, vince lui."""
    filtro = f"id=eq.{pr['id']}" + ("&stato=eq.aperta" if solo_se_aperta else "")
    r = sb("PATCH", f"/rest/v1/proposte?{filtro}", {"azione": az, **(patch_extra or {})},
           {"Prefer": "return=representation"}) or []
    return bool(r)


def main():
    adesso = datetime.datetime.now(datetime.timezone.utc)
    print(("I SEGUITI AUTOMATICI" if SEGUITI else "LA PRIMA RISPOSTA AUTOMATICA") + (" (prova: non scrive niente)" if PROVA else "") + (" IN OMBRA: decide, non approva" if OMBRA else ""))
    ops = sb("GET", f"/rest/v1/operazioni?select=chiave,attiva&chiave=in.({CHIAVE},manda)") or []
    fermo = interruttori(ops, OMBRA, CHIAVE)
    if fermo:
        print(f"  {fermo}" + (": in prova guardo lo stesso" if PROVA else ": non approvo niente"))
        if not PROVA:
            print("prima_risposta: 0 approvate")
            return
    if not finestra(adesso):
        print(f"  fuori finestra (lun-ven {ORE[0]}-{ORE[1]} a Roma, adesso {adesso.astimezone(ROMA):%a %H:%M})"
              + (": in prova guardo lo stesso" if PROVA else ""))
        if not PROVA:
            print("prima_risposta: 0 approvate")
            return

    # il tetto del giorno: si contano le approvate in automatico oggi, a Roma
    auto = sb("GET", "/rest/v1/proposte?select=prospect_id,azione->>approvata_il,azione->>approvata_da&azione->>automatica=eq.true&order=id.desc&limit=500") or []
    firma_mia = FIRMA_SEGUITI if SEGUITI else FIRMA
    tetto = MAX_SEGUITI_AL_GIORNO if SEGUITI else MAX_AL_GIORNO
    oggi = adesso.astimezone(ROMA).date()
    fatte_oggi = sum(1 for x in auto if x.get("approvata_il") and x.get("approvata_da") == firma_mia
                     and quando(x["approvata_il"]).astimezone(ROMA).date() == oggi)
    # mai due prime risposte alla stessa persona; i seguiti hanno gia' la loro regola (followup.py non mette in coda due volte)
    gia_auto = set() if SEGUITI else {x["prospect_id"] for x in auto if x.get("approvata_da") == FIRMA}
    posti = min(MAX_PER_GIRO, tetto - fatte_oggi)
    if posti <= 0 and not PROVA:
        print(f"  gia' {fatte_oggi} oggi: il tetto e' {tetto}, riprendo domani")
        print("prima_risposta: 0 approvate")
        return

    aperte = sb("GET", "/rest/v1/proposte?select=id,tipo,titolo,prospect_id,azione,at&stato=eq.aperta"
                       "&tipo=eq.risposta&prospect_id=not.is.null&order=at") or []
    ids = list({x["prospect_id"] for x in aperte})
    schede = {}
    for i in range(0, len(ids), 100):
        for p in sb("GET", f"/rest/v1/prospects?select={CAMPI}&id=in.({','.join(ids[i:i+100])})") or []:
            schede[p["id"]] = p

    import lettura
    # IL PRIMO INVIO SI GUARDA INSIEME (regola del 28/9, Dre 29/9). Il 29/9 manda.py
    # non aveva ancora mai spedito una mail vera: la prima risposta automatica sarebbe
    # stata anche la prima volta del postino. Finche' Clara non ha mai mandato niente,
    # la prima che passa tutto resta aperta in Posta con il via a Dre: la preme lui,
    # la guarda uscire su Smartlead, e da li' in poi si va da soli.
    mai_mandato = not sb("GET", "/rest/v1/proposte?select=id&risposta=like.Mandata%20da%20Clara*&limit=1")
    in_attesa_del_via = bool(sb("GET", "/rest/v1/proposte?select=id&stato=in.(aperta,approvata,in_invio)"
                                       "&azione->prima_risposta->>esito=eq.primo%20invio%20da%20guardare&limit=1"))
    approvate, restano = 0, 0
    for pr in aperte:
        p = schede.get(pr["prospect_id"])
        nome = ((p or {}).get("company") or (p or {}).get("name") or (p or {}).get("email") or pr["titolo"])[:34]
        no = perche_no_seguito(pr, p) if SEGUITI else perche_no(pr, p)
        if p and p["id"] in gia_auto:
            no.append("ha gia' avuto una risposta automatica")
        if OMBRA and (pr.get("azione") or {}).get("ombra"):
            continue                                          # gia' giudicata in ombra: non si rilegge ogni 5 minuti
        if no:
            if "gia' passata di qui" not in no:
                print(f"  -  {nome:34} {no[0]}")
            continue
        if approvate >= max(posti, 0) and not PROVA:
            print(f"  {nome}: passerebbe, ma il giro e' pieno: al prossimo"); continue
        az = dict(pr.get("azione") or {})
        # IL FILO ADESSO: la bozza e' nata su una lettura di ore fa. Se nel frattempo
        # hanno riscritto, o qualcuno di noi ha risposto a mano, non si parte.
        try:
            _, letti = lettura.leggi(p)
        except Exception as e:                                # noqa: BLE001
            print(f"  ?  {nome:34} filo non riletto ({str(e)[:60]}): resta a Dre"); continue
        vecchia = az.get("lettura") or {}
        cambiato = None
        if SEGUITI:
            # per un follow-up noi abbiamo gia' scritto dopo di lei (l'analisi): conta
            # solo se e' partito qualcosa DOPO che la bozza e' nata
            if (letti.get("scritto_dopo_di_lei") or 0) > (vecchia.get("scritto_dopo_di_lei") or 0):
                cambiato = "qualcuno di noi le ha gia' scritto dopo che la bozza era nata"
        elif letti.get("scritto_dopo_di_lei"):
            cambiato = "qualcuno di noi le ha gia' scritto dopo la sua ultima mail"
        elif (letti.get("ultima_loro_il"), (letti.get("ultima_loro") or "")[:150]) != (vecchia.get("ultima_loro_il"), (vecchia.get("ultima_loro") or "")[:150]):
            cambiato = "ha riscritto dopo che la bozza era nata"
        elif (letti.get("detto_no") and (pr.get("azione") or {}).get("intento") != "INT-GB") \
                or letti.get("non_scrivere") \
                or [g for g in (letti.get("girato_a") or []) if g.split("@")[-1].lower() != (p.get("email") or "").split("@")[-1].lower()] \
                or (letti.get("autorisposta") and not SEGUITI):
            # per il gigante buono il no E' il caso (Dre, 2/10); «non scrivetemi» ferma sempre
            cambiato = "rileggendo il filo adesso, non e' piu' un caso semplice"
        # «Via libera» dal calendario dei follow-up (29/9): Dre ha visto la traccia e sa che e' innocua
        if not cambiato and not az.get("via_libera"):
            fuori = contatti_fuori(p)
            if fuori:
                cambiato = "siamo gia' in contatto fuori da Smartlead: " + "; ".join(fuori)[:220]
        if cambiato:
            esito, motivo = "STOP", cambiato
        else:
            esito, motivo = rilettura_seguito(pr, p, letti) if SEGUITI else revisore(pr, p, letti)
        il = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if OMBRA:
            # la decisione si scrive, con la mail esatta che sarebbe partita: il
            # confronto con quello che Dre manda davvero si fa su questo testo
            print(f"  {'◐ partirebbe' if esito == 'OK' else '◐ resta a Dre'}  {nome:34} {motivo}")
            if esito == "OK":
                approvate += 1
            else:
                restano += 1
            if not PROVA:
                az["ombra"] = {"esito": "partirebbe" if esito == "OK" else "resta a Dre", "motivo": motivo,
                               "il": il, "bozza": az.get("bozza")}
                segna(pr, az)
            continue
        if esito != "OK":
            restano += 1
            print(f"  ✋ {nome:34} resta a Dre: {motivo}")
            if PROVA:
                continue
            az["prima_risposta"] = {"esito": "resta a Dre", "motivo": motivo, "il": il}
            if segna(pr, az):
                di_clara("controllo", f"Prima risposta a {nome}: non parte da sola, resta a te in Posta. Il Revisore: {motivo}",
                         prospect_id=p["id"])
            continue
        if mai_mandato:
            if in_attesa_del_via:
                print(f"  ✓  {nome:34} passa, ma aspetta il primo invio guardato insieme"); continue
            print(f"  ✓  {nome:34} passa: e' il PRIMO invio, il via lo da' Dre in Posta")
            if PROVA:
                approvate += 1; continue
            az.update({"allega": True, "allega_presentazione": True,
                       "prima_risposta": {"esito": "primo invio da guardare", "il": il}})
            if segna(pr, az, {"titolo": f"Primo invio automatico, dai tu il via: {nome}"[:200]}):
                in_attesa_del_via = True
                di_clara("domanda", f"È pronta la prima risposta che partirebbe da sola: {nome}. Aprila in Posta e premi «Approva e manda»: "
                                    f"la guardiamo uscire su Smartlead, con analisi e presentazione allegate. Dopo questa, le prossime partono da sole (massimo {MAX_AL_GIORNO} al giorno).",
                         prospect_id=p["id"])
            continue
        print(f"  ✓  {nome:34} passa: parte al prossimo giro di manda, con analisi e presentazione")
        if PROVA:
            approvate += 1; continue
        gruppo = (az.get("lettura") or {}).get("gruppo")
        az.update({"approvata_da": firma_mia, "approvata_il": il, "automatica": True,
                   "allega": (not SEGUITI) or gruppo in ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO"),
                   "allega_presentazione": (not SEGUITI) or gruppo in ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO", "FOLLOW UP 1"),
                   "prima_risposta": {"esito": "OK", "il": il}})
        if segna(pr, az, {"stato": "approvata"}):
            approvate += 1
            di_clara("controllo", f"Prima risposta a {nome} approvata in automatico (Revisore: OK). Parte con analisi e presentazione al prossimo giro.",
                     prospect_id=p["id"], letto=True)
        else:
            print(f"     {nome}: nel frattempo l'ha presa Dre, non tocco")
    print(f"prima_risposta: {approvate} {'partirebbero (ombra)' if OMBRA else 'passerebbero' if PROVA else 'approvate'}, {restano} restano a Dre, "
          f"{len(aperte)} bozze guardate, {fatte_oggi}/{tetto} oggi")


if __name__ == "__main__":
    main()
