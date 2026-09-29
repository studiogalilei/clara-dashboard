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
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara, contattabile, quando          # noqa: E402

PROVA = "--prova" in sys.argv
OMBRA = "--ombra" in sys.argv
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
FIRMA = "prima-risposta-automatica (decisione Dre 29/9)"
MAX_PER_GIRO = 5
MAX_AL_GIORNO = 15
ORE = (9, 17)                              # dalle 9 alle 16:59, ora di Roma
CLASSI_OK = ("positivo", "tiepido")
# dal playbook: vuole l'analisi, vuole parlare, chi siete, vuole il materiale
# ma non la call. Il resto (rinvii, inoltri, obiezioni, prezzo, «come ci avete
# trovato») e' una conversazione, non una prima risposta: resta a Dre.
INTENTI_OK = ("INT-01", "INT-02", "INT-03", "INT-23")
CAMPI = ("id,email,email_alt,company,name,classificazione,stage,pipeline_stage,fuori,no_followup,"
         "analysis_sent,analysis_pdf,campaign,campaign_id,lead_id,last_reply_at")


def finestra(ora):
    """Lun-ven, dalle 9 alle 17 a Roma. Una mail automatica alle 23 non sembra una persona."""
    ora = ora.astimezone(ROMA)
    return ora.weekday() < 5 and ORE[0] <= ora.hour < ORE[1]


def interruttori(ops, ombra=False):
    """Tutti e due accesi, o niente. Torna il motivo se non si parte. In ombra
    non si approva niente, quindi basta il suo: manda puo' restare spento."""
    stato = {o["chiave"]: bool(o.get("attiva")) for o in ops}
    if "prima_risposta" not in stato:
        return "l'operazione prima_risposta non esiste in tabella"
    spenti = [k for k in (("prima_risposta",) if ombra else ("prima_risposta", "manda")) if not stato.get(k)]
    return f"interruttore spento: {', '.join(spenti)}" if spenti else None


def perche_no(pr, p):
    """Il cancello sui fatti gia' scritti. Torna i motivi: vuota vuol dire che passa."""
    az = pr.get("azione") or {}
    let = az.get("lettura") or {}
    no = []
    if pr.get("tipo") != "risposta" or str(pr.get("titolo") or "").startswith("Da guardare tu"):
        no.append("e' da guardare")
    if not (az.get("bozza") or "").strip():
        no.append("manca la bozza")
    if az.get("approvata_da") or az.get("prima_risposta"):
        no.append("gia' passata di qui")
    if let.get("gruppo"):
        no.append(f"non e' una prima risposta ({let['gruppo']})")
    if az.get("intento") not in INTENTI_OK:
        no.append(f"intento {az.get('intento')} fuori dalla prima risposta")
    if let.get("coerenza") != "COERENTE":
        no.append("la seconda testa non dice COERENTE")
    if let.get("scritto_dopo_di_lei"):
        no.append("abbiamo gia' scritto dopo la sua ultima mail")
    if let.get("detto_no"):
        no.append("ha detto no")
    if let.get("autorisposta"):
        no.append("autorisposta")
    if let.get("casella_di_servizio"):
        no.append("casella di servizio")
    if let.get("girato_a") or let.get("destinatario") or (p or {}).get("email_alt"):
        no.append("c'e' di mezzo un altro indirizzo")
    if let.get("analisi_ricevuta") or let.get("analisi_gia_letta"):
        no.append("l'analisi l'ha gia' avuta")
    if not p:
        no.append("manca la scheda")
        return no
    if p.get("classificazione") not in CLASSI_OK:
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


def revisore(pr, p, letti):
    """Il Revisore rilegge la mail sapendo che partira' davvero, senza nessuno dopo di lui."""
    try:
        import cervello
        az = pr.get("azione") or {}
        azienda = p.get("company") or p.get("name") or p["email"]
        prompt = f"""{cervello.ruolo("revisore")}Sei il REVISORE di Studio Galilei. Questa mail PARTIRA' DAVVERO, in automatico,
senza che Dre la legga prima. Dopo di te non c'e' nessuno. Il tuo compito: dire se puo' partire cosi'.

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
    print("LA PRIMA RISPOSTA AUTOMATICA" + (" (prova: non scrive niente)" if PROVA else "") + (" IN OMBRA: decide, non approva" if OMBRA else ""))
    ops = sb("GET", "/rest/v1/operazioni?select=chiave,attiva&chiave=in.(prima_risposta,manda)") or []
    fermo = interruttori(ops, OMBRA)
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
    auto = sb("GET", "/rest/v1/proposte?select=prospect_id,azione->>approvata_il&azione->>automatica=eq.true&order=id.desc&limit=500") or []
    oggi = adesso.astimezone(ROMA).date()
    fatte_oggi = sum(1 for x in auto if x.get("approvata_il") and quando(x["approvata_il"]).astimezone(ROMA).date() == oggi)
    gia_auto = {x["prospect_id"] for x in auto}
    posti = min(MAX_PER_GIRO, MAX_AL_GIORNO - fatte_oggi)
    if posti <= 0 and not PROVA:
        print(f"  gia' {fatte_oggi} oggi: il tetto e' {MAX_AL_GIORNO}, riprendo domani")
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
    approvate, restano = 0, 0
    for pr in aperte:
        p = schede.get(pr["prospect_id"])
        nome = ((p or {}).get("company") or (p or {}).get("name") or (p or {}).get("email") or pr["titolo"])[:34]
        no = perche_no(pr, p)
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
        if letti.get("scritto_dopo_di_lei"):
            cambiato = "qualcuno di noi le ha gia' scritto dopo la sua ultima mail"
        elif (letti.get("ultima_loro_il"), (letti.get("ultima_loro") or "")[:150]) != (vecchia.get("ultima_loro_il"), (vecchia.get("ultima_loro") or "")[:150]):
            cambiato = "ha riscritto dopo che la bozza era nata"
        elif letti.get("detto_no") or letti.get("autorisposta") or letti.get("girato_a"):
            cambiato = "rileggendo il filo adesso, non e' piu' un caso semplice"
        if cambiato:
            esito, motivo = "STOP", cambiato
        else:
            esito, motivo = revisore(pr, p, letti)
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
        print(f"  ✓  {nome:34} passa: parte al prossimo giro di manda, con analisi e presentazione")
        if PROVA:
            approvate += 1; continue
        az.update({"approvata_da": FIRMA, "approvata_il": il, "automatica": True,
                   "allega": True, "allega_presentazione": True,
                   "prima_risposta": {"esito": "OK", "il": il}})
        if segna(pr, az, {"stato": "approvata"}):
            approvate += 1
            di_clara("controllo", f"Prima risposta a {nome} approvata in automatico (Revisore: OK). Parte con analisi e presentazione al prossimo giro.",
                     prospect_id=p["id"], letto=True)
        else:
            print(f"     {nome}: nel frattempo l'ha presa Dre, non tocco")
    print(f"prima_risposta: {approvate} {'partirebbero (ombra)' if OMBRA else 'passerebbero' if PROVA else 'approvate'}, {restano} restano a Dre, "
          f"{len(aperte)} bozze guardate, {fatte_oggi}/{MAX_AL_GIORNO} oggi")


if __name__ == "__main__":
    main()
