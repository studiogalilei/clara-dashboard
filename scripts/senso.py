#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL SENSO LO DECIDE L'AI (12/10/2026). Le regole, in un posto solo.

PERCHE' ESISTE
Il 12/10 il postino ha fermato due «sì» veri come «ha detto no». La lista di parole
trovava «cancellare il messaggio» nell'informativa in fondo alla mail, e «Buongiorno,
grazie» come «no, grazie». Il modello li aveva letti giusti. La fonte non era la lista:
era la regola «basta che UNO dei due dica no» (lettura.frena), che faceva vincere la
parola sul senso. Dre: «questo deve essere interpretato».

LA REGOLA, DA QUI IN POI
  - Il senso di quello che ha scritto una persona lo decide l'AI, sul testo SUO
    (senza firma, informativa e nostra mail citata).
  - Una lista di parole sola, GRAVI, e solo come rete per i casi gravi: chiede di non
    essere contattato, di essere cancellato, minaccia. Li' un falso allarme costa poco
    (una seconda lettura) e un errore costa tanto.
  - Se la lista e l'AI non sono d'accordo non ci si blocca in silenzio: si rilegge, e se
    il dubbio resta il caso va a Dre in tre righe.
  - Fermarsi costa poco, il permanente costa tanto: le soglie per fermare e quelle per
    gli effetti permanenti (soppressione, attesa chiusa, classe fuori dai positivi) sono
    diverse, e il permanente vuole l'AI sicura o Dre.

LE SOGLIE NON STANNO QUI
Stanno nel Manuale di Clara (documento 01, sezione F «Il lettore»), caricato nella
tabella `regole`. Qui arrivano come argomento. Se una chiave manca o non si capisce,
la decisione e' «senza_regole»: freno acceso, niente di permanente, e si dice.

Questo modulo e' puro: niente rete, niente database, niente modello. Si prova da solo.
"""
import datetime
import re
import unicodedata

# ── LA RETE PER I GRAVI ─────────────────────────────────────────────────────────
# Una regex sola, applicata solo al testo suo (lettura.solo_suo). Nasce dalla parte
# forte delle due liste di prima (lettura.DETTO_NO e analisi_auto.NON_TOCCARE), con due
# correzioni del 12/10: via «come spam» (due falsi su due: «segnalata come spam dal
# filtro» e' un avviso, non un'accusa), dentro «rimossi». Niente «non siamo interessati»,
# «no grazie», «abbiamo gia'»: sono no ordinari, li legge l'AI.
GRAVI = re.compile((
    r"cancell(?:atemi|ateci|ami|aci|armi|arci)\b|"
    r"cancell\w* (?:il|la|le|i|lo|gli) (?:mio|mia|miei|mie|nostr\w*) (?:dat|indirizz|contatt|mail|e-?mail|nominativ)|"
    r"cancell\w* (?:dalla|dalle|dai|dal|dagli|da) (?:vostr|lista|list|mailing|database|elenc|contatt|newsletter)|"
    r"rimuov(?:etemi|eteci|ermi|erci|ami|aci)\b|"
    r"rimuov\w* (?:il|la|le|i|lo|gli) (?:mio|mia|miei|mie|nostr\w*) (?:dat|indirizz|contatt|mail|e-?mail|nominativ)|"
    r"rimuov\w* (?:dalla|dalle|dai|dal|dagli|da) (?:vostr|lista|list|mailing|database|elenc|contatt|newsletter)|"
    r"(?:essere|venire|siano|vengano|venga|sia) rimoss\w*|"
    r"non (?:ci|mi) contatt\w*|non (?:ci|mi) (?:scriv|invi|mand)\w* pi[uù]|"
    r"non (?:vogliamo|voglio|desider\w+) (?:pi[uù]|essere contattat|ricevere|altre)|"
    r"diffid\w*|denunc\w*|garante (?:della |per la )?privacy|molest\w*|"
    r"smett\w* (?:di|con) (?:scriver|mandar|inviar|contattar|disturbar)|"
    r"la smetta|smettila|smettetela|"
    r"basta (?:mail|email|e-mail|messaggi|con queste|cos[iì])|"
    r"lasciateci (?:in pace|stare)|lasciatemi (?:in pace|stare)|opt.?out|unsubscribe|disiscri\w*|"
    r"come (?:avete|ha) (?:avuto|ottenuto|preso) (?:la mia|il mio|i miei|questo|questa|il nostro|la nostra)|"
    r"(?:trattamento|dati) .{0,20}(?:senza|non) .{0,20}consenso|"
    # 12/10 sera, dagli scettici: le frasi piu' comuni non le vedeva. L'imperativo italiano mette il
    # pronome in coda («contattateci», «scrivetemi»), e le richieste GDPR e quelle in inglese mancavano.
    # Sette richieste vere sulle ultime mille risposte passavano solo se l'AI non sbagliava.
    r"non (?:(?:ci|mi) )?(?:contatt|scriv|invi|mand|disturb|chiam)\w*(?:mi|ci)\b|"
    r"non (?:ci|mi) (?:contatt|scriv|invi|mand|disturb)\w* (?:pi[uù]|ulteriorment|ancora)|"
    r"togli(?:etemi|eteci|ermi|erci)\b|elimin(?:atemi|ateci|armi|arci)\b|"
    r"elimin\w* (?:il|la|le|i|lo|gli) (?:mio|mia|miei|mie|nostr\w*) (?:dat|indirizz|contatt|mail|e-?mail|nominativ)|"
    r"mi oppongo|ci opponiamo|revoc\w* (?:il |ogni )?(?:mio |nostro )?consenso|diritto (?:di|alla) (?:opposizione|cancellazione)|"
    r"remove (?:me|us)\b|take (?:me|us) off|(?:do not|don.?t) (?:contact|email|e-mail|write|send)|"
    r"stop (?:emailing|contacting|sending|writing)|no (?:more|further) e-?mails?").replace(" ", r"\s+")
    # «spam» solo come accusa (1/10): «finita nello spam» e' un si' che avvisa del filtro
    + r"|(?<!nello )(?<!in )(?<!nella cartella )(?<!come )\bspam\b(?! folder)", re.I)


def rete(testo_suo):
    """Le frasi della lista grave trovate nel testo suo, in ordine. Vuota = la rete tace."""
    return [m.group(0) for m in GRAVI.finditer(testo_suo or "")][:5]


# ── LE SOGLIE, DAL MANUALE ──────────────────────────────────────────────────────
# Le chiavi che servono (sezione F del documento 01). Le prime sette ci sono gia' dal
# 12/10; le altre sono la proposta portata a Dre con questo lavoro.
CHIAVI = ("lettore_non_contattare", "lettore_non_contattare_per_sempre", "lettore_dice_no", "lettore_dice_no_sicuro",
          "autorisposta", "rimanda", "lettore_vuole_analisi_o_call", "lettore_vuole_analisi_o_call_dubbio",
          "lettore_seconda_netta", "lettore_illeggibile", "lettore_fuori_target", "lettore_non_e_lui", "lettore_ha_gia_analisi")
FACOLTATIVE = ("lettore_tutto_vicino_a",)       # vuota nel Manuale di oggi: senza, il controllo non si fa


def _numeri(v):
    """«≥ 0,50» → [0.5]; «≥ 0,80 e dice no < 0,20» → [0.8, 0.2]; «0,50-0,80» → [0.5, 0.8]."""
    return [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", v or "")]


def soglie(regole):
    """Le soglie del lettore dalle righe di `regole` (lista di {chiave, valore} o dict).
    Torna None se ne manca una o non si capisce: chi chiama decide «senza_regole»."""
    if not regole:
        return None
    val = regole if isinstance(regole, dict) else {r.get("chiave"): r.get("valore") for r in regole}
    s = {}
    for k in CHIAVI + FACOLTATIVE:
        n = [x for x in _numeri(val.get(k)) if 0 <= x <= 1]
        if not n:
            if k in FACOLTATIVE:
                continue
            return None
        s[k] = n
    if len(s["lettore_vuole_analisi_o_call"]) < 2 or len(s["lettore_vuole_analisi_o_call_dubbio"]) < 1 \
            or len(s["lettore_seconda_netta"]) < 2:
        return None
    return s


# ── LE DECISIONI ────────────────────────────────────────────────────────────────
ETICHETTE = ("si", "no", "non_scrivere", "auto", "rinvio", "fuori_target", "persona_sbagliata", "illeggibile", "altro")
# la scelta di Dre (i bottoni del Metro) diventa un'etichetta del senso
DA_DRE = {"si": "si", "no": "no", "non_scrivere": "non_scrivere", "fuori_ufficio": "auto", "rinvio": "rinvio", "altro": "altro"}
CAMPO_DI = {"no": "detto_no", "auto": "autorisposta", "rinvio": "rinvio", "fuori_target": "fuori_target",
            "persona_sbagliata": "non_e_lui", "illeggibile": "illeggibile"}
PAROLE = {"si": "sì", "no": "no", "non_scrivere": "richiesta di non essere contattato", "auto": "risposta automatica",
          "rinvio": "più avanti", "fuori_target": "fuori target", "persona_sbagliata": "persona sbagliata",
          "illeggibile": "illeggibile", "altro": "altro"}


def _d(**k):
    base = {"etichetta": "altro", "sicuro": False, "freno": True, "grave": False, "dubbio": True,
            "permanente_ok": False, "serve_seconda": False, "contesa": None, "fonte": "nessuna",
            "stato": "letta", "motivo": "", "quando": None, "girato_a": [], "domanda": "", "frase": "",
            "rete": [], "p": None, "soppresso": False, "ordinaria": None}
    base.update(k)
    return base


def _vuole(r):
    return max(r.get("vuole_analisi", 0), r.get("vuole_call", 0))


def _ordinario(r, s):
    """Il punto 4: il resto lo decide l'AI, senza nessuna lista. Il primo caso che vale chiude.
    Torna (etichetta, sicuro, dubbio)."""
    if r.get("illeggibile", 0) >= s["lettore_illeggibile"][0]:
        return "illeggibile", True, False
    # 12/10 sera, dagli scettici: chi ci gira a un indirizzo nuovo o a un collega («questa casella non
    # e' piu' attiva, scrivetemi su ...», «scriva a ..., se ne occupa lui») usciva dai positivi senza
    # Dre: diventava fuori ufficio o persona sbagliata. Per Dre, sul Metro, sono si'. Se c'e' a chi
    # scrivere (girato_a, gia' verificato: scritto da lui, non nostro, non una pec in firma) e non ha
    # detto no, e' un si' in dubbio: la classe resta fra i positivi e la bozza la vede Dre.
    # Ma un fuori ufficio TEMPORANEO («fino al 20, per urgenze scrivete a ...») resta un fuori ufficio:
    # si riprende al rientro, non si scrive al collega. Misurato sulle 150 del Metro: cosi' i si' persi
    # passano da 9 a 6 e le autorisposte mancate restano 4; con il rimando sempre prima dell'autorisposta
    # le autorisposte mancate sarebbero salite a 10.
    temporaneo = r.get("autorisposta", 0) >= s["autorisposta"][0] and r.get("non_e_lui", 0) < s["lettore_non_e_lui"][0]
    if r.get("girato_a") and r.get("detto_no", 0) < s["lettore_dice_no"][0] and not temporaneo:
        return "si", False, True
    if r.get("autorisposta", 0) >= s["autorisposta"][0]:
        return "auto", True, False
    if r.get("fuori_target", 0) >= s["lettore_fuori_target"][0]:
        return "fuori_target", True, False
    # 12/10, dalla misura sul Metro: «quest'anno niente budget, ma saremo lieti di ricevere l'analisi»
    # e' un si' per Dre (se chiede l'analisi la riceve). Un no insieme a un si' pieno non e' mai un
    # no sicuro: e' un si' in dubbio (freno, niente di permanente)
    if _vuole(r) >= s["lettore_vuole_analisi_o_call"][0] and r.get("detto_no", 0) >= s["lettore_dice_no"][0]:
        return "si", False, True
    if r.get("detto_no", 0) >= s["lettore_dice_no_sicuro"][0]:
        return "no", True, False
    if r.get("detto_no", 0) >= s["lettore_dice_no"][0]:
        return "no", False, True
    if r.get("rinvio", 0) >= s["rimanda"][0]:
        return "rinvio", True, False
    pieno, no_max = s["lettore_vuole_analisi_o_call"][:2]
    if _vuole(r) >= pieno and r.get("detto_no", 0) < no_max:
        return "si", True, False
    if _vuole(r) >= s["lettore_vuole_analisi_o_call_dubbio"][0]:
        return "si", False, True
    if r.get("non_e_lui", 0) >= s["lettore_non_e_lui"][0]:
        return "persona_sbagliata", True, False
    banda = s.get("lettore_tutto_vicino_a")
    if banda and len(banda) >= 2:
        domande = [v for k, v in r.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if domande and all(banda[0] <= v <= banda[1] for v in domande):
            return "altro", False, True
    return "altro", False, False


def _campo_dell_etichetta(e, r):
    if e == "si":
        return "vuole_analisi" if r.get("vuole_analisi", 0) >= r.get("vuole_call", 0) else "vuole_call"
    return CAMPO_DI.get(e, "detto_no")


def giudica(r, rete_trovata, s, seconda=None, dre=None, problemi=()):
    """La decisione su una risposta, nell'ordine scritto nel piano del 12/10 (§4).

    r         le probabilita' della prima lettura (cervello.classifica_risposta), o None
    rete_trovata  le frasi della lista grave nel testo suo (rete()), o []
    s         le soglie (soglie()), o None
    seconda   {campo, p, dove, perche} dalla seconda lettura (cervello.rileggi); p None = fallita
    dre       la scelta di Dre ('si', 'no', 'non_scrivere', 'fuori_ufficio', 'rinvio', 'altro')
    problemi  le verifiche fallite (verifica()): ognuna chiede una seconda lettura
    """
    rr = list(rete_trovata or [])
    if dre in DA_DRE:
        e = DA_DRE[dre]
        return _d(etichetta=e, sicuro=True, dubbio=False, grave=e == "non_scrivere", freno=e != "si" and e != "rinvio",
                  permanente_ok=True, fonte="dre", stato="deciso_dre", motivo="deciso da Dre", rete=rr,
                  soppresso=e == "non_scrivere", p=r, quando=(r or {}).get("rinvio_quando") or None,
                  girato_a=(r or {}).get("girato_a") or [], domanda=(r or {}).get("domanda") or "", frase=(r or {}).get("frase") or "")
    if s is None:
        return _d(stato="senza_regole", grave=bool(rr), rete=rr, p=r,
                  motivo="le soglie del lettore nel Manuale non si leggono: fermo tutto e lo dico")
    if not r:
        return _d(stato="senza_ai", grave=bool(rr), rete=rr,
                  motivo="l'AI non ha letto la risposta" + (f"; la lista ha trovato «{rr[0]}»" if rr else ""))
    r = dict(r)
    comune = {"rete": rr, "p": r, "quando": r.get("rinvio_quando") or None, "girato_a": r.get("girato_a") or [],
              "domanda": r.get("domanda") or "", "frase": r.get("frase") or "",
              "ordinaria": _ordinario(r, s)[0]}             # come la leggerebbe l'AI senza il grave: serve alle tre righe
    basso, alto = s["lettore_seconda_netta"][1], s["lettore_seconda_netta"][0]
    sec = seconda or {}
    fallita = bool(seconda) and not isinstance(sec.get("p"), (int, float))
    if fallita:
        return _d(stato="dubbio_a_dre", grave=bool(rr) or sec.get("campo") in ("non_contattare", "ostile"),
                  contesa={"campo": sec.get("campo")}, motivo="la seconda lettura non ha risposto", **comune)
    netta = None
    if seconda:
        p2 = float(sec["p"])
        netta = "si" if p2 >= alto else "no" if p2 <= basso else None
        if netta:
            r[sec.get("campo") or "detto_no"] = p2         # la seconda, se e' netta, prende il posto della prima
    fonte_ai = "ai+seconda" if seconda else "ai"

    # 3. IL GRAVE
    g = max(r.get("non_contattare", 0), r.get("ostile", 0))
    soppresso = r.get("non_contattare", 0) >= r.get("ostile", 0)
    da_non_contattare = s["lettore_non_contattare"][0]
    per_sempre = s["lettore_non_contattare_per_sempre"][0]
    campo_grave = "non_contattare" if soppresso else "ostile"
    grave_su_seconda = seconda and sec.get("campo") in ("non_contattare", "ostile")
    # 12/10, dalla misura: due casi che il «per sempre» dell'AI da sola non regge. L'ostilita' senza
    # una richiesta di non essere contattato («tendo a non rispondere allo spam», poi ha guardato il
    # sito: per Dre un si'), e un «non scrivetemi» insieme a un «mandate pure». Fermano, e decide Dre.
    sola_ostilita = r.get("non_contattare", 0) < per_sempre       # il «per sempre» vuole la richiesta esplicita
    apre = _vuole(r) >= s["lettore_vuole_analisi_o_call_dubbio"][0]
    if g >= per_sempre and (sola_ostilita or apre):
        return _d(grave=True, stato="dubbio_a_dre", contesa={"campo": campo_grave, "frase": r.get("frase") or (rr[0] if rr else ""),
                                                             "da": "lista" if rr else "prima"},
                  motivo=("l'AI legge ostilita' ma nessuna richiesta di non essere contattato" if sola_ostilita
                          else "chiede di non essere contattato ma accetta anche l'analisi") + ": decide Dre", **comune)
    if g >= per_sempre:
        return _d(etichetta="non_scrivere", sicuro=True, dubbio=False, grave=True, permanente_ok=True,
                  stato="seconda" if grave_su_seconda else "letta",
                  fonte="ai+seconda" if grave_su_seconda else ("ai+rete" if rr else "ai"), soppresso=soppresso,
                  motivo=f"l'AI legge una richiesta di non essere contattato ({g:.0%})", **comune)
    if rr:
        if not grave_su_seconda:
            return _d(grave=True, serve_seconda=True, stato="letta",
                      contesa={"campo": campo_grave, "frase": rr[0], "da": "lista", "direbbe": "non_scrivere"},
                      motivo=f"la lista ha trovato «{rr[0]}», l'AI dice {g:.0%}: rileggo", **comune)
        # la seconda lettura esclude il grave con nettezza (la frase sta nell'informativa, nella firma,
        # nella nostra mail citata, o e' sua ma non chiede di non essere contattato: «non vogliamo piu'
        # spendere in pubblicita', pero' mandate l'analisi»): due letture dell'AI d'accordo non perdono
        # contro una parola. Il grave si scarta e decide il resto. A Dre va solo il dubbio che resta
        # (12/10 sera: prima si scartava solo se `dove` era firma/informativa/citazione)
        if netta == "no":
            pass
        else:
            return _d(grave=True, stato="dubbio_a_dre", contesa={"campo": campo_grave, "frase": rr[0], "da": "lista"},
                      motivo=f"la lista ha trovato «{rr[0]}» e la seconda lettura non lo conferma ({sec.get('p'):.0%})", **comune)
    elif g >= da_non_contattare:
        if r.get("autorisposta", 0) >= s["autorisposta"][0]:
            pass                                             # un automatismo con parole forti: decide il punto 4
        elif not grave_su_seconda:
            return _d(grave=True, serve_seconda=True, contesa={"campo": campo_grave, "frase": r.get("frase") or "", "da": "prima", "direbbe": "non_scrivere"},
                      motivo=f"l'AI non e' sicura che chieda di non essere contattato ({g:.0%}): rileggo", **comune)
        elif netta != "no":
            return _d(grave=True, stato="dubbio_a_dre", contesa={"campo": campo_grave, "frase": r.get("frase") or "", "da": "prima"},
                      motivo=f"due letture a meta' sul «non scrivetemi» ({g:.0%})", **comune)

    # 4. IL RESTO LO DECIDE L'AI
    e, sicuro, dubbio = _ordinario(r, s)
    # 5. LE VERIFICHE: una qualunque fallita chiede una seconda lettura, che decide se e' netta
    # il taglio sporco (una firma o un pezzo di citazione nel testo suo) chiede una seconda lettura solo
    # quando la lettura direbbe un no: e' l'unica direzione con effetti permanenti
    problemi = [x for x in problemi if x != "taglio" or e == "no"]
    if problemi and e not in ("illeggibile",):
        # no e si' insieme: si rilegge il si' (se e' pieno, vince la regola «chi chiede l'analisi la riceve»)
        campo = ("vuole_analisi" if r.get("vuole_analisi", 0) >= r.get("vuole_call", 0) else "vuole_call") \
            if "no_e_si" in problemi else _campo_dell_etichetta(e, r)
        if not seconda:
            return _d(etichetta=e, serve_seconda=True, stato="letta",
                      contesa={"campo": campo, "frase": r.get("frase") or "", "da": "prima", "direbbe": e, "problemi": list(problemi)},
                      motivo=f"la lettura non torna ({', '.join(problemi)}): rileggo", **comune)
        if not netta:
            return _d(etichetta=e, stato="dubbio_a_dre", contesa={"campo": campo, "frase": r.get("frase") or "", "da": "prima", "direbbe": e},
                      motivo=f"due letture a meta' su «{PAROLE.get(e, e)}»", **comune)
    # il freno: niente parte da solo. Si accende su un no, un automatismo, un illeggibile, un
    # fuori target e su qualunque dubbio; un sì sicuro, un rinvio o un «altro» chiaro non frenano
    freno = e in ("no", "auto", "illeggibile", "fuori_target") or dubbio
    stato = "seconda" if seconda else "letta"
    return _d(etichetta=e, sicuro=sicuro, dubbio=dubbio, freno=freno, grave=False,
              permanente_ok=sicuro and not dubbio and e != "fuori_target",
              fonte=fonte_ai, stato=stato, soppresso=False,
              motivo=f"l'AI legge «{PAROLE.get(e, e)}»" + (" (in dubbio)" if dubbio else ""), **comune)


def permanente_ok(dec):
    """Un effetto permanente (soppressione, attesa chiusa, classe fuori dai positivi) solo
    con Dre o con l'AI sicura. Mai su una lettura in dubbio, senza AI o senza regole."""
    if not dec:
        return False
    if dec.get("fonte") == "dre":
        return True
    return bool(dec.get("permanente_ok")) and dec.get("fonte") in ("ai", "ai+rete", "ai+seconda") \
        and dec.get("stato") in ("letta", "seconda") and not dec.get("dubbio")


def classe(dec, attuale=None, manuale=False):
    """La classe del Workspace che segue dalla decisione. Una classe messa a mano non si tocca;
    un dubbio, l'AI giu' o le regole illeggibili lasciano la classe com'e'."""
    if manuale:
        return attuale
    tieni = attuale or "da_classificare"
    if not dec or dec.get("stato") in ("senza_ai", "senza_regole", "dubbio_a_dre") or dec.get("serve_seconda"):
        return tieni
    e = dec.get("etichetta")
    if e == "non_scrivere":
        if not permanente_ok(dec):
            return tieni
        return "soppresso" if dec.get("soppresso") else "nervoso"
    if e == "fuori_target":
        return "fuori_target" if dec.get("fonte") == "dre" else tieni      # lo scarto lo decide Dre
    if dec.get("dubbio") and e != "si":
        return tieni
    if e == "no":
        return "negativo" if permanente_ok(dec) else tieni
    return {"auto": "ooo", "rinvio": "rinvio", "si": "positivo", "persona_sbagliata": "persona_sbagliata",
            "illeggibile": "da_classificare", "altro": "tiepido"}.get(e, tieni)


POSITIVE = ("positivo", "tiepido", "rinvio")


def va_a_dre(dec, attuale=None):
    """I casi (a) e (b) del piano: quando un dubbio diventa una domanda a Dre.
    (a) qualunque dubbio sul grave; (b) un dubbio che toglierebbe la classe o farebbe
    qualcosa di irreversibile (un messaggio nuovo senza classe, un'azienda che uscirebbe
    dai positivi). Il caso (c), un dubbio su chi ha gia' una bozza ferma, lo porta la bozza."""
    if not dec or dec.get("stato") != "dubbio_a_dre":
        return False
    if dec.get("grave"):
        return True
    if attuale in (None, "", "da_classificare"):
        return True
    return attuale in POSITIVE and dec.get("etichetta") not in ("si", "rinvio")


# ── LE VERIFICHE ────────────────────────────────────────────────────────────────
NOSTRI = ("studiogalilei", "galilei", "odyn", "smartlead")
PEC = ("@legalmail.it", "@postecert.it", "@cert.")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)


# il verbo di rimando prima di un indirizzo («scrivete a», «inviate a»): senza, un indirizzo in firma
# non e' un «ci gira a». Una regola, un posto: la usa anche il ramo vecchio di lettura.ha_gia
RIMANDO = re.compile(r"(scriv|invi|mand|contatt|rivolg)\w*\s[^@]{0,40}$")


def rimando_prima(testo, indirizzo):
    t = (testo or "").lower()
    pos = t.find((indirizzo or "").lower())
    return pos >= 0 and bool(RIMANDO.search(t[max(0, pos - 60):pos]))


def _norm(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = re.sub(r"[«»\"“”'’`]", "", t)
    return re.sub(r"\s+", "", t)


def verifica(r, testo_suo, s=None, mie=(), oggi=None):
    """Quello che il codice sa controllare della lettura, senza fidarsi del modello.
    Torna (r ripulita, problemi). Un problema chiede una seconda lettura (giudica)."""
    if not r:
        return r, []
    r = dict(r)
    problemi = []
    suo_n = _norm(testo_suo)
    frase = (r.get("frase") or "").strip()
    if frase and _norm(frase) not in suo_n:
        problemi.append("frase")                 # la frase citata non sta nel testo suo: inventata o presa dalla firma
    mie = {str(m).lower() for m in (mie or ()) if m}
    buoni = []
    for g in r.get("girato_a") or []:
        gl = str(g).strip().lower()
        if not gl or gl not in (testo_suo or "").lower():
            continue                              # un indirizzo o un nome che non ha scritto lui
        if gl in mie or any(n in gl for n in NOSTRI):
            continue
        if "@" in gl and ("pec" in gl.split("@")[-1] or any(x in gl for x in PEC)):
            if not rimando_prima(testo_suo, gl):
                continue                          # una pec senza «scrivete a» e' una firma legale
        buoni.append(g)
    r["girato_a"] = buoni[:3]
    if s and r.get("detto_no", 0) >= s["lettore_dice_no"][0] and _vuole(r) >= s["lettore_vuole_analisi_o_call_dubbio"][0]:
        problemi.append("no_e_si")               # dice no e sì insieme: una delle due e' sbagliata
    if r.get("taglio_sporco"):
        problemi.append("taglio")                 # il modello dice che nel testo suo c'e' roba nostra o della firma
    oggi = oggi or datetime.date.today()
    q = (r.get("rinvio_quando") or "").strip()
    try:
        d = datetime.date.fromisoformat(q[:10]) if q else None
    except ValueError:
        d = None
    r["rinvio_quando"] = d.isoformat() if d and oggi < d <= oggi + datetime.timedelta(days=366) else ""
    return r, problemi


# ── LA DATA DI UN RINVIO ────────────────────────────────────────────────────────
# 12/10 sera, dagli scettici: un rinvio senza data non tornava piu' (RINVIO SCADUTO vuole
# next_action_date). Il modello ora calcola le date relative da oggi; se la persona non dice
# proprio quando, si riprende dopo un mese, e la nota lo dice. Una regola, un posto: la usano il
# sync e il recupero notturno. (Da portare nel Manuale, sezione F, con le altre.)
GIORNI_RINVIO_SENZA_DATA = 30
# lo stesso per un fuori ufficio che non dice quando rientra: senza una data nessuno lo riprende
# (clara.py «rientri» guarda ooo_until). Misurato il 12/10: sui 28 fuori ufficio veri la data
# scritta («fino al 21 agosto») la trovava la regex solo una volta.
GIORNI_OOO_SENZA_DATA = 14


def ripresa(quando, oggi=None):
    """(data, nota) per un rinvio: la data detta dalla persona, o quella di ripiego."""
    if quando:
        return quando, "Ricontatto: l'aveva chiesto lui"
    oggi = oggi or datetime.date.today()
    return ((oggi + datetime.timedelta(days=GIORNI_RINVIO_SENZA_DATA)).isoformat(),
            f"Ricontatto: aveva detto «più avanti» senza una data, riprovo dopo {GIORNI_RINVIO_SENZA_DATA} giorni")


def rientro(quando, oggi=None):
    """La data da cui riprendere un fuori ufficio: quella detta, o quella di ripiego."""
    if quando:
        return quando
    return ((oggi or datetime.date.today()) + datetime.timedelta(days=GIORNI_OOO_SENZA_DATA)).isoformat()


# ── LE TRE RIGHE PER DRE ────────────────────────────────────────────────────────
def tre_righe(dec, testo_suo=""):
    """Il dubbio detto a Dre in tre righe: cosa ha scritto, come la leggo, cosa succede."""
    frase = (dec.get("frase") or (dec.get("contesa") or {}).get("frase") or " ".join((testo_suo or "").split()))[:140]
    p = dec.get("p") or {}
    con = dec.get("contesa") or {}
    g = max(p.get("non_contattare", 0), p.get("ostile", 0))
    if dec.get("grave") and con.get("da") == "lista":
        e = dec.get("ordinaria") or "altro"
        io = (f"Io la leggo come {PAROLE.get(e, e)} ({p.get(_campo_dell_etichetta(e, p), 0):.0%})" if e != "altro"
              else "Io non ci leggo né un sì né un no")
        come = (f"{io}, e la richiesta di non essere contattato solo al {g:.0%}; ma la lista ha trovato "
                f"«{con.get('frase')}», e la seconda lettura non lo esclude")
    elif dec.get("grave"):
        come = f"Io la leggo come richiesta di non essere contattato ({g:.0%}), ma non ne sono sicura; la seconda lettura resta a metà"
    else:
        e = dec.get("etichetta") or "altro"
        quanto = p.get(_campo_dell_etichetta(e, p), 0) if p else 0
        come = f"Io la leggo come {PAROLE.get(e, e)} ({quanto:.0%}); la seconda lettura resta a metà"
    return (f"Ha scritto: «{frase}»\n{come}.\n"
            f"Finché non mi dici, non parte niente e non chiudo niente.")
