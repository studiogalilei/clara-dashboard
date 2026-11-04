"""CLARA IN PROVA: la sandbox sul vivo (3/11/2026, sera).

Dre: «prima trainare, testare il sistema in sandbox, proprio il reale sistema che poi andra' a
lavorare, finche' non arriva al livello che fa le cose bene, e rilasciarlo». Qui il cervello nuovo
(clara_sdr) decide su ogni risposta vera che entra, con gli strumenti veri (calendario, scheda,
filo di Smartlead). Scrive la decisione in clara_decisioni; il giudice (Opus, un altro modello) la
vota subito. Dal 4/11 mattina (Dre: «lo volevo automatizzato, io non ho tempo per leggere») una
mail votata non pericolosa parte da sola col postino (clara_manda); una pericolosa resta ferma col
motivo, e la sera il turno (clara_turno, dentro «La giornata») riferisce a Dre cosa e' partito e
come. Le call e i «decidi tu» restano suoi. Da li' si addestra l'identita'.

Uso:
  python3 scripts/clara_prova.py --email X     dalla strada veloce: decide sull'ultima risposta
  python3 scripts/clara_prova.py --giro        ogni 10 minuti: risposte senza decisione, giudice,
                                               foglio, correzioni di Dre
  --prova                                      decide e stampa, non scrive niente
"""
import datetime
import json
import os
import sys
import urllib.parse

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import clara_sdr  # noqa: E402
import lettore  # noqa: E402
from stanza import sb, sb_tutte  # noqa: E402

PROVA = os.environ.get("PROVA") == "1" or "--prova" in sys.argv
OPERAZIONE = "clara_prova"
SCHEDA = "Clara in prova"
RIGHE = 400
FINESTRA_ORE = 48          # risposte piu' vecchie non si decidono nel giro (il banco storico e' l'esame)
PER_GIRO = 15              # decisioni al massimo per giro: un tetto alla spesa, non una coda persa
TETTO_GIORNO = 40.0        # dollari al giorno per il cervello (4/11: Fable 5.1, circa 0,3-0,5 $ a decisione)
TETTO_GIUDICE = 25.0       # il giudice vota ogni mail prima che parta: non deve finire i soldi
SCRIVE = {"send_analysis", "reply", "offer_slots", "book_meeting"}   # le mosse che mandano una mail
RIFAI_MOSSE = SCRIVE | {"escalate"}   # --rifai rigioca col cervello nuovo solo cio' che manda o che era rimasto a Dre
AUTONOMA = True            # 4/11 mattina, Dre: «lo volevo automatizzato»: una mail votata non pericolosa parte da sola
COLONNE = [("Quando", 95), ("Azienda", 150), ("Il lead ha scritto", 340), ("Mossa", 100), ("Perché", 250),
           ("Testo che manderebbe", 400), ("Segnali", 150), ("Giudice", 130),
           ("Va bene? (ok / no)", 110), ("Cosa avresti fatto tu", 260), ("Note", 220), ("id", 40)]
DI_DRE = (8, 9, 10)        # le colonne gialle: I, J, K
ROMA = datetime.timezone(datetime.timedelta(hours=1))


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def acceso():
    r = sb("GET", f"/rest/v1/operazioni?select=attiva&chiave=eq.{OPERAZIONE}") or []
    return bool(r and r[0].get("attiva"))


def _roma(iso):
    try:
        import zoneinfo
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(zoneinfo.ZoneInfo("Europe/Rome"))
    except (ValueError, TypeError, AttributeError):
        return None


# ── 1. decidere ────────────────────────────────────────────────────────────────

def _storia(p):
    h = lettore._smartlead(f"/campaigns/{p['campaign_id']}/leads/{p['lead_id']}/message-history") or {}
    return h.get("history") or []


RIFAI = "--rifai" in sys.argv       # rigioca con l'identita' nuova le decisioni ancora da fare di versioni vecchie


def gia_decisa(pid, risposta_il):
    r = sb("GET", f"/rest/v1/clara_decisioni?select=risposta_il,versione,stato,mossa&prospect_id=eq.{pid}&origine=eq.risposta&order=risposta_il.desc,creato_il.desc&limit=1") or []
    if not r:
        return False
    a, b = _roma(r[0]["risposta_il"]), _roma(risposta_il)
    stessa = bool(a and b and abs((a - b).total_seconds()) < 120)
    if stessa and RIFAI and r[0]["stato"] == "proposta" and r[0]["versione"] != clara_sdr.VERSIONE and r[0]["mossa"] in RIFAI_MOSSE:
        return False                                         # da rifare col cervello nuovo (solo se manda una mail)
    return stessa


def da_rifare(r, ora):
    """Pura. L'ultima decisione su una risposta e' da rifare se Dre l'ha scartata con una nota negli ultimi due giorni
    («Non sono d'accordo: dico a Clara cosa fare», 4/11): la nota e' l'ordine. «Me ne occupo io» non e' un ordine a Clara."""
    if not r or r.get("stato") != "scartata" or r.get("dre_giudizio") != "no":
        return None
    nota = (r.get("dre_nota") or "").strip()
    if not nota or nota.startswith("Me ne occupo io"):
        return None
    quando = _roma(r.get("dre_il"))
    if not quando or (ora - quando) > datetime.timedelta(hours=48):
        return None
    return nota


def correzione_di_dre(pid, risposta_il):
    r = sb("GET", f"/rest/v1/clara_decisioni?select=stato,dre_giudizio,dre_nota,dre_il&prospect_id=eq.{pid}&risposta_il=eq.{urllib.parse.quote(risposta_il)}"
                  "&origine=eq.risposta&order=creato_il.desc&limit=1") or []
    return da_rifare(r[0] if r else None, adesso())


def decidi_lead(p, perche=""):
    """Decide sull'ultima risposta del lead e salva. Torna la riga salvata (o la decisione, in prova).
    4/11: se Dre ha scartato la decisione con una nota, Clara la rifa' seguendo la nota."""
    if not (p.get("campaign_id") and p.get("lead_id")):
        print("  lead senza filo Smartlead: niente")
        return None
    storia = _storia(p)
    messaggi = clara_sdr.messaggi_della_relazione(p, storia)   # Smartlead piu' le mail fuori thread del CRM
    risposte = [m for m in messaggi if m["tipo"] == "REPLY"]
    if not risposte:
        print("  nessuna risposta nel filo")
        return None
    risposta_il = risposte[-1]["il"]
    ordine = None
    if gia_decisa(p["id"], risposta_il):
        ordine = correzione_di_dre(p["id"], risposta_il)
        if not ordine:
            print("  gia' decisa")
            return None
        print(f"  Dre ha detto no e ha scritto cosa fare: Clara rifà («{ordine[:60]}»)")
    sit = (f"Dramane ha scartato la tua decisione precedente su questa risposta e ha scritto: «{ordine}». "
           "Fai esattamente quello che dice, con una mossa o un testo diversi da prima.") if ordine else None
    r = clara_sdr.giudica_uno(p, storia, situazione=sit)
    d = r["decisione"]
    riga = {"prospect_id": p["id"], "risposta_il": risposta_il, "versione": clara_sdr.VERSIONE, "stato": "proposta",
            **({"dre_giudizio": None, "errore": None} if ordine else {}),
            "modello": r["uso"].get("modello") or clara_sdr.MODELLO,
            "lead_testo": (r.get("lead_testo") or "")[:1500],
            "mossa": d["proposed_action"], "owner": d.get("owner"), "entro_il": d.get("due_at") or None,
            "testo": d.get("draft") or None, "perche": d.get("reason_summary"), "prove": d.get("evidence_refs") or [],
            "richiamo": d.get("callback") if d["proposed_action"] == "callback" else None,
            "appuntamento": (d.get("meeting_at") or None) if d["proposed_action"] == "book_meeting" else None,
            # 4/11 (Dre): prima il valore, poi l'incontro. Niente consiglio di chiamata finche' l'analisi non e' partita
            "consiglio": (d.get("call_suggestion") if (d.get("call_suggestion") or {}).get("numero", "").strip()
                          and d["proposed_action"] != "send_analysis" and p.get("analysis_sent") else None),
            "segnali": r["segnali"], "uso": r["uso"], "contesto": r["contesto"]}
    print(f"  {p.get('company') or '?'}: {d['proposed_action']} (owner {d.get('owner')}, {r['uso'].get('dollari')} $)"
          + (f"; segnali: {'; '.join(r['segnali'])}" if r["segnali"] else ""))
    if PROVA:
        print("  (prova: non si salva)")
        return riga
    salvata = sb("POST", "/rest/v1/clara_decisioni?on_conflict=prospect_id,risposta_il,versione", [riga],
       {"Prefer": "resolution=merge-duplicates,return=representation"}) or []
    # le decisioni vecchie ancora da fare per questo lead sono superate: il lead ha scritto di nuovo,
    # oppure (--rifai) l'identita' e' cambiata e questa e' la decisione nuova sulla stessa risposta
    sb("PATCH", f"/rest/v1/clara_decisioni?prospect_id=eq.{p['id']}&risposta_il=lt.{urllib.parse.quote(risposta_il)}&stato=in.(proposta,approvata)",
       {"stato": "superata"}, {"Prefer": "return=minimal"})
    sb("PATCH", f"/rest/v1/clara_decisioni?prospect_id=eq.{p['id']}&risposta_il=eq.{urllib.parse.quote(risposta_il)}&versione=neq.{clara_sdr.VERSIONE}&stato=eq.proposta",
       {"stato": "superata"}, {"Prefer": "return=minimal"})
    # una mail: il giudice la vota subito e, se non e' pericolosa, parte da sola (il postino, entro 5 minuti)
    if AUTONOMA and salvata and d["proposed_action"] in SCRIVE:
        g = giudica_riga(salvata[0])
        riga["stato"] = rilascia_una(salvata[0], g)
    return riga


def spesa(scopo):
    try:
        return float(lettore.spesa_di_oggi(scopo) or 0)
    except Exception:                                            # noqa: BLE001
        return 0.0


def risposte_nuove(ore=None):
    """I lead con una risposta nelle ultime FINESTRA_ORE senza una decisione: i piu' recenti prima."""
    da = (adesso() - datetime.timedelta(hours=ore or FINESTRA_ORE)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # solo chi aspetta noi e si puo' ancora contattare: a chi ha gia' avuto la nostra risposta, o e'
    # cliente/perso/non contattare, non serve una mossa (4/11: senza questo filtro erano 581 lead in 30 giorni)
    righe = sb_tutte(f"/rest/v1/prospects?select=*&last_reply_at=gte.{da}&lead_id=not.is.null&campaign_id=not.is.null&awaiting_us=eq.true")
    righe.sort(key=lambda r: r.get("last_reply_at") or "", reverse=True)
    from stanza import contattabile
    fuori = []
    for p in righe:
        if contattabile(p) and not gia_decisa(p["id"], p["last_reply_at"]):
            fuori.append(p)
    return fuori


def giorni_feriali(da, a):
    """Quanti giorni feriali interi sono passati fra due momenti (pura): da venerdi' alle 15 a sabato alle 15 e' 0,
    a lunedi' alle 15 e' 1."""
    n, g = 0, da
    while g + datetime.timedelta(days=1) <= a:
        g += datetime.timedelta(days=1)
        if g.weekday() < 5:
            n += 1
    return n


ATTESA_FERIALI = {"send_analysis": 1, "offer_slots": 2}   # 4/11 (Dre): dopo l'analisi un giorno; dopo gli orari «2/3 giorni, 5 e' tanto»


def da_seguire(r, ora):
    """Pura. Una nostra mail partita (analisi o orari) va seguita se sono passati i giorni feriali di ATTESA_FERIALI,
    il lead non ha scritto dopo, non c'e' una call in agenda, non e' in mano a Dre e non l'abbiamo gia' seguita."""
    p = r.get("prospects") or {}
    inviata = _roma(r.get("inviata_il"))
    attesa = ATTESA_FERIALI.get(r.get("mossa") or "send_analysis", 1)
    if not inviata or giorni_feriali(inviata, ora) < attesa or (ora - inviata).days > 10:
        return False
    risposta = _roma(p.get("last_reply_at"))
    if risposta and risposta > inviata + datetime.timedelta(minutes=3):
        return False
    if p.get("in_mano_a") or r.get("consiglio") or r.get("seguita"):
        return False
    return True


NOTA_ISTRUZIONI = """Sei Clara. Dramane (il capo) ha scritto una nota su un lead. Devi dire una cosa sola: la nota significa che
adesso la relazione la gestisce lui di persona (gli ha scritto su WhatsApp, l'ha chiamato, lo sente lui, «ci penso io»,
«lo gestisco io», ci ha parlato)? In quel caso in_mano=true e in motivo riscrivi in 3-8 parole cosa ha fatto («gli ha
scritto su WhatsApp»). Se la nota è un'istruzione, un promemoria, un'informazione o un esito di chiamata senza che lui
prenda in mano la relazione (es. «vuole solo Meta», «richiamare a dicembre», «non risponde»), in_mano=false."""
NOTA_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["in_mano", "motivo"],
               "properties": {"in_mano": {"type": "boolean"}, "motivo": {"type": "string"}}}


def leggi_note_di_dre(massimo=20):
    """UN CERVELLO SOLO (Dre, 4/11): «dai la capacità a Clara di comprendere le mie note: non mi invia notifiche su
    lead che ho già sentito e scritto su WhatsApp io, e che quindi ho in mano e gestisco io». Ogni nota nuova di Dre
    la legge il cervello: se dice che se ne occupa lui, il lead passa in mano a lui (come «Me ne occupo io» nel Desk):
    niente mail, niente consigli, niente solleciti, niente notifiche. Torna (lette, prese in mano)."""
    # le note di Achille e di Clara non sono ordini; le note piu' vecchie di due giorni sono storia: si archiviano senza leggerle
    vecchie = (adesso() - datetime.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not PROVA:
        sb("PATCH", f"/rest/v1/snella_note?clara_letta_il=is.null&or=(at.lt.{vecchie},autore_nome.neq.Dramane,autore_nome.is.null)",
           {"clara_letta_il": adesso().isoformat()}, {"Prefer": "return=minimal"})
    righe = sb("GET", "/rest/v1/snella_note?select=id,prospect_id,testo,tipo,at,autore_nome,prospects(id,company,in_mano_a)"
                      f"&clara_letta_il=is.null&prospect_id=not.is.null&autore_nome=eq.Dramane&at=gte.{vecchie}&order=at.asc&limit={massimo}") or []
    lette = prese = 0
    for n in righe:
        p = n.get("prospects") or {}
        testo = (n.get("testo") or "").strip()
        ora = adesso().isoformat()
        if not testo or testo.startswith("Dre ridà") or p.get("in_mano_a") or (n.get("autore_nome") or "").lower().startswith("clara"):
            if not PROVA:
                sb("PATCH", f"/rest/v1/snella_note?id=eq.{n['id']}", {"clara_letta_il": ora}, {"Prefer": "return=minimal"})
            lette += 1
            continue
        try:
            v, _ = lettore.chiedi_anthropic("nota", NOTA_ISTRUZIONI, f"Lead: {p.get('company') or '?'}\nNota di Dramane ({n.get('tipo')}): «{testo[:600]}»",
                                            NOTA_SCHEMA, modello=clara_sdr.MODELLO, registra="clara_sdr")
        except Exception as e:                                   # noqa: BLE001
            print(f"  nota su {p.get('company') or '?'} non letta ({str(e)[:120]})")
            continue
        lette += 1
        print(f"  nota su {p.get('company') or '?'}: {'in mano a Dre' if v.get('in_mano') else 'solo informazione'} ({(v.get('motivo') or '')[:60]})")
        if PROVA:
            continue
        sb("PATCH", f"/rest/v1/snella_note?id=eq.{n['id']}", {"clara_letta_il": ora}, {"Prefer": "return=minimal"})
        if v.get("in_mano"):
            motivo = (v.get("motivo") or testo)[:120]
            sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"in_mano_a": "Dre", "in_mano_motivo": motivo, "in_mano_il": ora}, {"Prefer": "return=minimal"})
            sb("PATCH", f"/rest/v1/clara_decisioni?prospect_id=eq.{p['id']}&stato=in.(proposta,approvata)",
               {"stato": "scartata", "dre_nota": f"Me ne occupo io: {motivo}", "errore": None}, {"Prefer": "return=minimal"})
            sb("PATCH", f"/rest/v1/clara_decisioni?prospect_id=eq.{p['id']}&consiglio=not.is.null&stato=not.in.(superata,scartata)",
               {"consiglio": None}, {"Prefer": "return=minimal"})
            prese += 1
    return lette, prese


def ritira_consigli_prematuri():
    """LA LEGGE E' RETROATTIVA (4/11): un consiglio di chiamata dato prima che l'analisi partisse si ritira."""
    righe = sb_tutte("/rest/v1/clara_decisioni?select=id,mossa,consiglio,prospects(analysis_sent)&consiglio=not.is.null&stato=not.in.(superata,scartata)", chiave="id")
    prematuri = [r["id"] for r in righe if (r.get("consiglio") or {}).get("esito") is None
                 and (not (r.get("prospects") or {}).get("analysis_sent")
                      or (r.get("mossa") == "send_analysis" and not ((r.get("consiglio") or {}).get("perche") or "").startswith(("Analisi mandata il", "Orari proposti il"))))]
    for i in range(0, len(prematuri), 50):
        if not PROVA:
            sb("PATCH", f"/rest/v1/clara_decisioni?id=in.({','.join(prematuri[i:i + 50])})", {"consiglio": None}, {"Prefer": "return=minimal"})
    return len(prematuri)


def numero_da_chiamare(p):
    """Il numero per il consiglio di chiamata (Dre, 5/11 notte: «soprattutto i cellulari, però va bene anche quelli»
    aziendali). Il cellulare prima; se no il numero migliore che abbiamo (firma, scheda, sito). (numero, come) o (None, None)."""
    import segnale_provvisorio as S
    if not p or not p.get("id"):
        return None, None
    if "phone" not in p or "enriched" not in p:
        p = {**((sb("GET", f"/rest/v1/prospects?select=phone,enriched&id=eq.{p['id']}") or [{}])[0]), **p}
    letti = sb("GET", f"/rest/v1/interactions?select=at,kind,body&prospect_id=eq.{p['id']}&kind=in.(email_in,email_out)&order=at.asc&limit=80") or []
    numeri = S.numeri_di(p, letti)
    cellulare = S.cellulare_fra(numeri)
    if cellulare:
        return cellulare, "il suo cellulare"
    for t in sorted(numeri, key=lambda t: S.RANGO_TEL.get((t.get("tipo"), t.get("fonte")), 9)):
        if t.get("numero"):
            return t["numero"], ("un numero aziendale " + S.DA_DOVE.get(t.get("fonte"), "")).strip()
    return None, None


def perche_consiglio(cosa, giorno, come):
    return (f"{cosa} il {giorno} con due orari e il link: da allora nessuna risposta e niente call prenotata. "
            f"C'è {come}: una tua telefonata adesso è il touchpoint giusto («vi abbiamo mandato l'analisi»).")


def segui_silenzio(massimo=10):
    """DOPO L'ANALISI (Dre, 4/11): «sempre inviare l'analisi e quello che porta valore, e dopo si puo' chiedere
    l'incontro. Mi deve consigliare di chiamarlo se l'abbiamo inviata, e' passato un giorno, non ha risposto ne'
    prenotato e abbiamo il numero; se non abbiamo il numero continua lei a sentire a modo suo».
    Per ogni analisi partita da almeno un giorno feriale senza risposta ne' call: col cellulare un consiglio di
    chiamata a Dre sulla decisione dell'analisi; senza, Clara decide il sollecito (origine «silenzio»), il giudice
    vota e la mail parte da sola. Torna (consigli, solleciti)."""
    from stanza import contattabile, call_in_agenda
    import segnale_provvisorio
    ora = adesso()
    da = (ora - datetime.timedelta(days=11)).strftime("%Y-%m-%dT%H:%M:%SZ")
    righe = sb_tutte("/rest/v1/clara_decisioni?select=id,prospect_id,inviata_il,consiglio,risposta_il,mossa,"
                     "prospects(id,company,name,email,phone,enriched,last_reply_at,awaiting_us,fuori,stage,pipeline_stage,no_followup,"
                     "classificazione,in_mano_a,campaign_id,lead_id,analysis_sent,analysis_sent_at,analysis_pdf,city,sector,role)"
                     f"&mossa=in.(send_analysis,offer_slots)&stato=eq.inviata&origine=eq.risposta&inviata_il=gte.{da}", chiave="id")
    seguite = {x["risposta_il"] for x in (sb("GET", f"/rest/v1/clara_decisioni?select=risposta_il&origine=eq.silenzio&risposta_il=gte.{da}") or [])}
    consigli = solleciti = 0
    for r in righe:
        r["seguita"] = r.get("inviata_il") in seguite
        p = r.get("prospects") or {}
        if not da_seguire(r, ora) or not contattabile(p) or call_in_agenda(p):
            continue
        if consigli + solleciti >= massimo or spesa("clara_sdr") > TETTO_GIORNO:
            break
        giorno = _roma(r["inviata_il"]).strftime("%d/%m")
        cosa = "Analisi mandata" if r.get("mossa") == "send_analysis" else "Orari proposti"
        # 5/11 (Dre): il consiglio vale con qualunque numero, il cellulare prima
        numero, come = numero_da_chiamare(p)
        if numero:
            perche = perche_consiglio(cosa, giorno, come)
            print(f"  {p.get('company') or '?'}: consiglio di chiamata ({come}, …{numero[-4:]})")
            if not PROVA:
                sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{r['id']}", {"consiglio": {"numero": numero, "perche": perche}}, {"Prefer": "return=minimal"})
            consigli += 1
            continue
        try:
            storia = _storia(p)
            sit = ((f"silenzio dopo l'analisi. L'analisi è partita il {giorno} con due orari e il link del calendario; " if r.get("mossa") == "send_analysis"
                    else f"silenzio dopo la proposta di orari. Gli orari sono partiti il {giorno} con il link del calendario; ")
                   + "da allora nessuna risposta e nessuna call prenotata; non abbiamo un cellulare da far chiamare. Decidi tu il seguito.")
            g = clara_sdr.giudica_uno(p, storia, situazione=sit)
            d = g["decisione"]
            riga = {"prospect_id": p["id"], "risposta_il": r["inviata_il"], "versione": clara_sdr.VERSIONE, "origine": "silenzio",
                    "modello": g["uso"].get("modello") or clara_sdr.MODELLO,
                    "lead_testo": f"(silenzio: {cosa.lower()} il {giorno}, nessuna risposta e niente call prenotata)",
                    "mossa": d["proposed_action"], "owner": d.get("owner"), "entro_il": d.get("due_at") or None,
                    "testo": d.get("draft") or None, "perche": d.get("reason_summary"), "prove": d.get("evidence_refs") or [],
                    "richiamo": None, "consiglio": None, "appuntamento": None,
                    "segnali": g["segnali"], "uso": g["uso"], "contesto": g["contesto"]}
            print(f"  {p.get('company') or '?'}: sollecito → {d['proposed_action']} ({g['uso'].get('dollari')} $)")
            solleciti += 1
            if PROVA:
                continue
            salvata = sb("POST", "/rest/v1/clara_decisioni?on_conflict=prospect_id,risposta_il,versione", [riga],
                         {"Prefer": "resolution=merge-duplicates,return=representation"}) or []
            if AUTONOMA and salvata and d["proposed_action"] in SCRIVE:
                rilascia_una(salvata[0], giudica_riga(salvata[0]))
        except Exception as e:                                   # noqa: BLE001
            print(f"  {p.get('company') or '?'}: sollecito non deciso ({str(e)[:150]})")
    return consigli, solleciti


def consigli_retroattivi(giorni=45):
    """LA LEGGE E' RETROATTIVA (Dre, 5/11 alle 0:36): «se abbiamo inviato l'analisi, non hanno risposto e c'e' il
    numero, me lo deve lasciare: oggi li chiamo tutti». Le analisi mandate dal sistema vecchio non hanno una decisione
    di Clara: per ognuna (ultimi `giorni` giorni, nessuna risposta dopo, niente call, contattabile, un numero) nasce
    una decisione «aspetta» con il consiglio di chiamata, che il Desk mostra in Relazioni e in Call."""
    from stanza import contattabile, call_in_agenda
    ora = adesso()
    da = (ora - datetime.timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%SZ")
    righe = sb_tutte("/rest/v1/prospects?select=id,company,name,email,phone,enriched,last_reply_at,fuori,stage,pipeline_stage,no_followup,"
                     "classificazione,in_mano_a,analysis_sent,analysis_sent_at,city,sector,role"
                     f"&analysis_sent=eq.true&analysis_sent_at=gte.{da}&fuori=eq.false&no_followup=eq.false&in_mano_a=is.null"
                     "&or=(classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso))", chiave="id")
    aperti = {x["prospect_id"] for x in (sb_tutte("/rest/v1/clara_decisioni?select=prospect_id,consiglio&consiglio=not.is.null&stato=not.in.(superata,scartata)", chiave="prospect_id") or [])
              if (x.get("consiglio") or {}).get("numero") and not (x.get("consiglio") or {}).get("esito")}
    fatti, senza_numero, saltati = 0, 0, 0
    for p in sorted(righe, key=lambda x: x.get("analysis_sent_at") or "", reverse=True):
        mandata = _roma(p.get("analysis_sent_at"))
        risposta = _roma(p.get("last_reply_at"))
        if not mandata or (risposta and risposta > mandata + datetime.timedelta(minutes=3)):
            saltati += 1; continue
        if p["id"] in aperti or not contattabile(p) or call_in_agenda(p) or (p.get("stage") or "") in ("call_fissata", "call_fatta", "proposta", "cliente", "perso"):
            saltati += 1; continue
        numero, come = numero_da_chiamare(p)
        if not numero:
            senza_numero += 1; continue
        giorno = mandata.strftime("%d/%m")
        perche = perche_consiglio("Analisi mandata", giorno, come)
        print(f"  {(p.get('company') or '?')[:34]:34} analisi il {giorno}, {come} …{numero[-4:]}")
        fatti += 1
        if PROVA:
            continue
        riga = {"prospect_id": p["id"], "risposta_il": p["analysis_sent_at"], "versione": "consiglio-retro-5-11", "origine": "silenzio",
                "modello": "regola", "lead_testo": f"(analisi mandata il {giorno}, nessuna risposta e niente call prenotata)",
                "mossa": "wait", "owner": "Dramane", "stato": "proposta", "in_prova": False,
                "perche": f"Analisi mandata il {giorno}, nessuna risposta: aspetto, e ti consiglio di chiamare.",
                "consiglio": {"numero": numero, "perche": perche}, "prove": [], "segnali": [], "uso": {"dollari": 0}}
        sb("POST", "/rest/v1/clara_decisioni?on_conflict=prospect_id,risposta_il,versione", [riga], {"Prefer": "resolution=merge-duplicates,return=minimal"})
    print(f"consigli retroattivi: {fatti} consigli ({len(righe)} analisi mandate negli ultimi {giorni} giorni, {saltati} saltati per risposta/call/stato, {senza_numero} senza numero)" + (" (prova)" if PROVA else ""))
    return fatti


def supera_vecchie():
    """Una decisione ancora «proposta» per un lead che non aspetta piu' noi (gli abbiamo risposto, o e'
    cliente/perso/non contattare) e' superata: nel Desk non deve restare un «Invia» su una cosa gia' fatta
    (4/11: 94 decisioni della prima notte erano su lead gia' serviti dal sistema vecchio)."""
    righe = sb_tutte("/rest/v1/clara_decisioni?select=id,prospect_id,mossa,consiglio,prospects(awaiting_us,fuori,stage,pipeline_stage,no_followup,classificazione)&stato=eq.proposta", chiave="id")
    from stanza import contattabile
    # 5/11: un «aspetta» con un consiglio di chiamata aperto (le analisi senza risposta) non e' una cosa gia' fatta:
    # il lead non aspetta noi, aspettiamo noi lui, e il consiglio deve restare finche' Dre non lo chiude. (La prima
    # notte il giro ne ha superati 62 su 72 dieci minuti dopo la nascita.) Si supera solo se non e' piu' contattabile.
    def _aperto(r):
        return r.get("mossa") == "wait" and (r.get("consiglio") or {}).get("numero") and not (r.get("consiglio") or {}).get("esito")
    vecchie = [r["id"] for r in righe if r.get("prospects")
               and ((not r["prospects"].get("awaiting_us") and not _aperto(r)) or not contattabile({**r["prospects"], "id": None}))]
    for i in range(0, len(vecchie), 50):
        if not PROVA:
            sb("PATCH", f"/rest/v1/clara_decisioni?id=in.({','.join(vecchie[i:i + 50])})", {"stato": "superata"}, {"Prefer": "return=minimal"})
    return len(vecchie)


# ── 2. il giudice ──────────────────────────────────────────────────────────────

def giudica_riga(d):
    """Il giudice (Opus, un altro modello) vota una decisione salvata: pericolosa? mossa giusta? testo? Salva il voto."""
    import esame_clara
    if spesa("esame_clara") > TETTO_GIUDICE:
        return {"errore": f"tetto del giorno del giudice ({TETTO_GIUDICE} $)"}
    r = {"contesto": d["contesto"], "segnali": d["segnali"] or [],
         "decisione": {"proposed_action": d["mossa"], "reason_summary": d["perche"], "evidence_refs": d["prove"],
                       "owner": d["owner"], "due_at": d["entro_il"], "draft": d["testo"], "callback": d["richiamo"]},
         "dopo": "(ancora niente: la decisione è di oggi; giudica la mossa e il testo per quello che si sa)"}
    try:
        g = esame_clara.giudica(r)
    except Exception as e:                                   # noqa: BLE001
        g = {"errore": str(e)[:200]}
    if not PROVA and "errore" not in g:
        sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"giudice": g}, {"Prefer": "return=minimal"})
    return g


def giudica_nuove(massimo=30):
    righe = sb("GET", f"/rest/v1/clara_decisioni?select=*&giudice=is.null&order=creato_il.desc&limit={massimo}") or []
    fatte = 0
    for d in righe:
        g = giudica_riga(d)
        if "errore" in g:
            print(f"  giudice: {g['errore']}")
            if "tetto" in g["errore"]:
                break
            continue
        fatte += 1
    return fatte


def rilascia_una(d, g):
    """Una mail votata parte da sola: «approvata» (il postino la manda). Se il giudice la dice pericolosa resta
    ferma con il motivo scritto (la sera Dre lo legge). Se il giudice non ha risposto, resta da votare. Torna lo stato."""
    if not g or "errore" in g:
        print(f"  resta da votare: {(g or {}).get('errore') or 'niente voto'}")
        return "proposta"
    if g.get("pericoloso"):
        motivo = f"il giudice la ferma: {(g.get('errore_pericoloso') or 'errore pericoloso')[:200]}"
        print(f"  FERMA: {motivo}")
        if not PROVA:
            sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}&stato=eq.proposta", {"errore": motivo}, {"Prefer": "return=minimal"})
        return "proposta"
    print(f"  parte da sola (giudice: mossa {g.get('mossa')}, testo {g.get('testo')})")
    if not PROVA:
        sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}&stato=eq.proposta",
           {"stato": "approvata", "approvata_il": adesso().isoformat(), "approvata_da": "Clara", "errore": None}, {"Prefer": "return=minimal"})
    return "approvata"


def rilascia():
    """Le mail ancora ferme con un voto del giudice e senza un motivo di fermo: partono (anche quelle decise prima
    di stamattina, quando serviva l'Invia di Dre). Torna quante."""
    if not AUTONOMA:
        return 0
    righe = sb("GET", "/rest/v1/clara_decisioni?select=id,giudice&stato=eq.proposta&giudice=not.is.null&errore=is.null"
                      f"&mossa=in.({','.join(sorted(SCRIVE))})&order=creato_il.asc&limit=100") or []
    n = 0
    for d in righe:
        if rilascia_una(d, d["giudice"]) == "approvata":
            n += 1
    return n


# ── 3. il foglio: la scheda «Clara in prova» ───────────────────────────────────

def _id_scheda(sid):
    from foglio import _g, SHEETS, rgb, NAVY, GIALLO, _campo, _formato
    info = _g("GET", f"{SHEETS}/{sid}?fields=sheets.properties")
    for s in info.get("sheets", []):
        if s["properties"]["title"] == SCHEDA:
            return s["properties"]["sheetId"]
    nuovo = max([s["properties"]["sheetId"] for s in info.get("sheets", [])] + [0]) + 1
    nc = len(COLONNE)
    R = [{"addSheet": {"properties": {"sheetId": nuovo, "title": SCHEDA, "index": 2, "tabColor": rgb(NAVY),
                                      "gridProperties": {"rowCount": RIGHE, "columnCount": nc, "frozenRowCount": 2,
                                                         "hideGridlines": False}}}}]
    for i, (_, w) in enumerate(COLONNE):
        R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                                                "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "COLUMNS", "startIndex": nc - 1, "endIndex": nc},
                                            "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
    R.append({"mergeCells": {"range": _campo(nuovo, 0, 1, 0, nc), "mergeType": "MERGE_ALL"}})
    R.append(_formato(_campo(nuovo, 0, 1, 0, nc), colore=NAVY, grassetto=True, dim=12, vert="MIDDLE", a_capo="WRAP"))
    R.append(_formato(_campo(nuovo, 1, 2, 0, nc), fondo=NAVY, colore="#ffffff", grassetto=True, dim=10, vert="MIDDLE", a_capo="WRAP"))
    R.append(_formato(_campo(nuovo, 2, RIGHE, 0, nc), dim=10, vert="TOP", a_capo="WRAP"))
    R.append(_formato(_campo(nuovo, 2, RIGHE, DI_DRE[0], DI_DRE[-1] + 1), fondo=GIALLO))
    R.append({"setDataValidation": {"range": _campo(nuovo, 2, RIGHE, DI_DRE[0], DI_DRE[0] + 1),
                                    "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": "ok"}, {"userEnteredValue": "no"}]},
                                             "showCustomUi": True, "strict": False}}})
    R.append({"addProtectedRange": {"protectedRange": {"range": _campo(nuovo, 0, RIGHE, 0, DI_DRE[0]), "warningOnly": True,
                                                       "description": "Lo scrive il sistema: le tue colonne sono quelle gialle"}}})
    R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
                                            "properties": {"pixelSize": 44}, "fields": "pixelSize"}})
    _g("POST", f"{SHEETS}/{sid}:batchUpdate", {"requests": R})
    print(f"  scheda «{SCHEDA}» creata")
    return nuovo


def _giudice_breve(g):
    if not g:
        return ""
    if g.get("errore"):
        return "non votato"
    return ("PERICOLOSO: " + (g.get("errore_pericoloso") or "")[:80] if g.get("pericoloso") else "mossa " + str(g.get("mossa")))


def righe_foglio(giorni=14):
    da = (adesso() - datetime.timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%SZ")
    righe = sb_tutte(f"/rest/v1/clara_decisioni?select=*,prospects(company)&creato_il=gte.{da}&order=creato_il.desc")
    righe.sort(key=lambda d: (d["risposta_il"], d["creato_il"]), reverse=True)   # la risposta piu' recente in alto
    viste, fuori = set(), []
    for d in righe:                                              # l'ultima versione per ogni risposta
        k = (d["prospect_id"], d["risposta_il"][:16])
        if k in viste:
            continue
        viste.add(k)
        q = _roma(d["risposta_il"])
        fuori.append([q.strftime("%d/%m %H:%M") if q else "", ((d.get("prospects") or {}).get("company") or "")[:60],
                      (d.get("lead_testo") or "")[:700], d["mossa"] + (f"\n→ {d['owner']}" if d.get("owner") and d["owner"] != "Clara" else ""),
                      d.get("perche") or "", d.get("testo") or "", "\n".join(d.get("segnali") or []),
                      _giudice_breve(d.get("giudice")), d.get("dre_giudizio") or "", d.get("dre_mossa") or "",
                      d.get("dre_nota") or "", d["id"]])
    return fuori[:RIGHE - 2]


def scrivi_foglio(sid):
    from foglio import _g, SHEETS
    S = _id_scheda(sid)
    valori = righe_foglio()
    testa = [[f"Clara in prova: decide su ogni risposta, non manda. Versione {clara_sdr.VERSIONE}, {len(valori)} decisioni negli ultimi 14 giorni. "
              "Nelle colonne gialle: va bene? (ok / no), cosa avresti fatto tu, note. Achille le legge ogni 10 minuti."] + [""] * (len(COLONNE) - 1),
             [c for c, _ in COLONNE]]
    _g("POST", f"{SHEETS}/{sid}/values:batchClear", {"ranges": [f"{SCHEDA}!A1:L{RIGHE}"]})
    _g("POST", f"{SHEETS}/{sid}/values:batchUpdate", {"valueInputOption": "RAW", "data": [
        {"range": f"{SCHEDA}!A1:L{2 + len(valori)}", "values": testa + valori}]})
    return S, len(valori)


def leggi_correzioni(sid):
    """Le colonne gialle: quello che Dre ha scritto e nel database ancora non c'e'."""
    from foglio import _g, SHEETS
    try:
        d = _g("GET", f"{SHEETS}/{sid}/values/{urllib.parse.quote(SCHEDA + '!I3:L' + str(RIGHE))}?valueRenderOption=UNFORMATTED_VALUE")
    except RuntimeError:
        return 0
    nuove = 0
    for riga in d.get("values", []):
        riga = [str(x).strip() if x is not None else "" for x in riga] + [""] * (4 - len(riga))
        ok, mossa, nota, did = riga[:4]
        if not did or not (ok or mossa or nota):
            continue
        ok = ok.lower() if ok.lower() in ("ok", "no") else None
        r = (sb("GET", f"/rest/v1/clara_decisioni?select=dre_giudizio,dre_mossa,dre_nota&id=eq.{did}") or [None])[0]
        if not r or (r.get("dre_giudizio") == ok and (r.get("dre_mossa") or "") == mossa and (r.get("dre_nota") or "") == nota):
            continue
        if not PROVA:
            sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{did}",
               {"dre_giudizio": ok, "dre_mossa": mossa or None, "dre_nota": nota or None, "dre_il": adesso().isoformat()},
               {"Prefer": "return=minimal"})
        nuove += 1
    return nuove


def foglio():
    from foglio import carica_stato, trova_foglio
    sid = trova_foglio(carica_stato())
    if not sid:
        print("  foglio della pipeline non trovato")
        return
    corrette = leggi_correzioni(sid)
    if PROVA:
        print(f"  (prova: {len(righe_foglio())} righe pronte, {corrette} correzioni lette, niente scritto)")
        return
    _, n = scrivi_foglio(sid)
    print(f"  foglio: {n} decisioni, {corrette} correzioni nuove di Dre")


# ── il giro ────────────────────────────────────────────────────────────────────

def registra(esito, dettaglio, partita):
    if PROVA:
        return
    try:
        sb("PATCH", f"/rest/v1/operazioni?chiave=eq.{OPERAZIONE}",
           {"ultima_corsa": adesso().isoformat(), "ultimo_esito": esito, "ultimo_dettaglio": dettaglio[-500:],
            "ultima_durata_ms": int((adesso() - partita).total_seconds() * 1000)})
    except Exception:                                            # noqa: BLE001
        pass


def _arg(nome, default):
    try:
        return int(sys.argv[sys.argv.index(nome) + 1])
    except (ValueError, IndexError):
        return default


def giro():
    partita = adesso()
    if not acceso():
        print("clara_prova: spenta in operazioni")
        return
    note = []
    ore, massimo = _arg("--ore", FINESTRA_ORE), _arg("--max", PER_GIRO)
    try:
        lette, prese = leggi_note_di_dre()
        if lette:
            note.append(f"{lette} note di Dre lette" + (f", {prese} relazioni passate a lui" if prese else ""))
        cand = risposte_nuove(ore)
        print(f"risposte senza decisione nelle ultime {ore} ore: {len(cand)}")
        decise = 0
        for p in cand[:massimo]:
            if spesa("clara_sdr") > TETTO_GIORNO:
                note.append(f"tetto del giorno ({TETTO_GIORNO} $) raggiunto")
                break
            try:
                if decidi_lead(p):
                    decise += 1
            except Exception as e:                               # noqa: BLE001
                print(f"  {p.get('company') or '?'}: non decisa ({str(e)[:150]})")
        note.append(f"{decise} decisioni nuove" + (f" ({len(cand) - massimo} restano al prossimo giro)" if len(cand) > massimo else ""))
        note.append(f"{supera_vecchie()} superate (il lead non aspetta più noi)")
        ritirati = ritira_consigli_prematuri()
        if ritirati:
            note.append(f"{ritirati} consigli ritirati (analisi non ancora partita)")
        c, s = segui_silenzio()
        if c or s:
            note.append(f"dopo l'analisi: {c} consigli di chiamata, {s} solleciti di Clara")
        note.append(f"{giudica_nuove()} votate dal giudice")
        note.append(f"{rilascia()} mail partite da sole")
        foglio()
        registra("ok", "; ".join(note), partita)
    except Exception as e:                                       # noqa: BLE001
        print(f"giro caduto: {e}")
        registra("errore", "; ".join(note + [str(e)[:200]]), partita)
        raise


def uno(email):
    if not acceso():
        print("clara_prova: spenta in operazioni")
        return
    p = (sb("GET", f"/rest/v1/prospects?select=*&email=eq.{urllib.parse.quote(email)}") or [None])[0]
    if not p:
        print("lead non trovato")
        return
    r = decidi_lead(p)
    foglio()
    if r and r.get("stato") == "approvata" and not PROVA:
        import clara_manda                                   # la strada veloce: la mail parte adesso, non al giro dei 5 minuti
        try:
            clara_manda.main()
        except Exception as e:                               # noqa: BLE001
            print(f"  postino: {str(e)[:150]} (riprova il direttore)")


def main():
    if "--giro" in sys.argv:
        giro()
    elif "--email" in sys.argv:
        uno(sys.argv[sys.argv.index("--email") + 1].strip().lower())
    elif "--consigli-retroattivi" in sys.argv:
        consigli_retroattivi(int(sys.argv[sys.argv.index("--giorni") + 1]) if "--giorni" in sys.argv else 45)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
