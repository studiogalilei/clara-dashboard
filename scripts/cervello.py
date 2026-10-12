#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL CERVELLO DI CLARA — la porta, una sola (7/9/2026).

PERCHE' ESISTE
Fino a oggi Clara non leggeva: la classificazione erano sei espressioni
regolari, e una diceva che se nel messaggio c'e' scritto «ok» o «aspetto»
allora e' un lead positivo. Misurato sui dati veri di Dre: su 197 risposte,
7 risponditori automatici di ferie finivano fra i positivi e 70 messaggi
(il 35%) venivano marcati «da classificare», cioe' scaricati su di lui.

Le parole chiave non capiranno mai la differenza che a Dre interessa di piu':
  «parli col nostro direttore marketing per approfondire»  -> caldo
  «guardi i contatti sul sito»                             -> scaricabarile
Sono la stessa forma, dicono l'opposto. Serve qualcuno che legga.

PERCHE' UNA PORTA SOLA
Dre non vuole dipendere da un fornitore. Se il modello si chiama in venti
punti del codice, cambiarlo e' un progetto; se si chiama qui dentro e basta,
e' una funzione. Tutto quello che sa parlare con un modello sta in _chiedi().
Il resto del programma conosce solo leggi().

COSA NON FA
Non scrive niente da nessuna parte. Legge e restituisce un giudizio. Chi lo
usa decide cosa farne. E' la stessa regola del pedaggio: Clara propone, Dre
dispone.

COSA COSTA
Gira su Claude Code col piano Max di Dre, non sull'API: nessun credito da
comprare. In cambio funziona solo col suo Mac acceso. Le letture gia' fatte
restano in cache su disco, quindi rileggere la stessa cosa e' gratis.
"""

import datetime
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env(nome):
    v = os.environ.get(nome)
    if v:
        return v
    for f in (".env.local", ".env"):
        p = os.path.join(RADICE, f)
        if not os.path.exists(p):
            continue
        for riga in open(p, encoding="utf-8"):
            if riga.strip().startswith(nome + "="):
                return riga.split("=", 1)[1].strip().strip("\"'")
    return None

CACHE = os.path.expanduser("~/.odyn-letture.json")

# IL FORNITORE (Dre, 7/9): non Anthropic per questo. OpenAI vince perche' ha
# gia' l'account e perche' la sua API e' la piu' stabile da anni, che conta
# quanto l'intelligenza quando una cosa deve girare da sola. Il fornitore si
# sceglie da FORNITORE in .env.local; finche' non c'e' una chiave OpenAI
# resta Claude Code col piano di Dre, come ponte.
#   FORNITORE=openai   + OPENAI_API_KEY=sk-...
#   FORNITORE=claude   (Claude Code sul Mac, solo come ponte)
FORNITORE = (_env("FORNITORE") or ("openai" if _env("OPENAI_API_KEY") else "claude")).lower()
MODELLO_OPENAI = _env("MODELLO_OPENAI") or "gpt-5-mini"
MODELLO_CLAUDE = "claude-sonnet-5"
A_GRUPPI_DI = 18          # quanti messaggi per volta: piu' su, meno precisione
ATTESA_MAX = 180          # secondi per gruppo

CLASSI = ("positivo", "tiepido", "negativo", "ooo", "rinvio",
          "fuori_target", "da_classificare", "persona_sbagliata", "nervoso", "soppresso")

# Le regole sono di Dre, non mie: vengono dal Playbook Classificazione e
# dalle regole d'oro in CLAUDE.md. Se cambiano li', cambiano qui.
REGOLE = """Sei il lettore dell'inbox di Studio Galilei, agenzia Google Ads che fa
outbound a freddo. Leggi la risposta di un'azienda e dici cosa vuol dire.

LE CLASSI
positivo      apre una porta, anche minima: «si'», «mandami», «mi interessa»,
              chiede prezzi o dettagli col tono aperto, chiede chi siamo per
              curiosita', oppure ti passa al decisore PER APPROFONDIRE.
tiepido       non chiude ma non apre: interesse vago, nessuna richiesta.
rinvio        vuole risentirsi piu' avanti («a ottobre», «dopo le ferie»,
              «fine anno»). E' un DOPO, non un no: per Dre vale quasi come un
              positivo, va solo ripreso alla data giusta.
ooo           risposta automatica di assenza, ferie, fuori ufficio.
negativo      chiude: «non interessati», «abbiamo gia' un'agenzia» detto come
              stop senza finestra futura, oppure ti scarica in modo generico
              («guardi i contatti sul sito»). Calmo, non ostile.
nervoso       infastidito o ostile: «smettetela», «come avete avuto la mia mail»,
              minacce, sarcasmo, insulti. Si lascia stare per sempre, come un no.
soppresso     RICHIESTA DI RIMOZIONE esplicita, CON PAROLE SUE: «rimuovetemi», «cancellate
              i miei dati», «non contattatemi piu'». Mai piu' una mail. Una firma, un
              disclaimer o un'informativa privacy in fondo alla mail NON sono una richiesta
              (12/10: «GDPR = soppresso» faceva leggere un no nell'informativa di un si').
persona_sbagliata  chi risponde non c'entra o non decide: «non sono io la persona»,
              «ha sbagliato indirizzo», «non lavoro piu' qui», «siamo un privato».
              Se pero' indica CHI contattare per approfondire, e' positivo.
fuori_target  non e' un cliente possibile: agenzie di marketing o concorrenti,
              caselle privacy/GDPR/legali, aziende senza clienti da acquisire.
da_classificare  il corpo non e' leggibile (solo firma o disclaimer), o e'
              davvero ambiguo. Usala poco: e' lavoro che scarichi su Dre.

LA DISTINZIONE CHE CONTA DI PIU'
Non conta CHE ti rimandi a un altro, conta PERCHE'.
  «parli col nostro direttore marketing per approfondire» = positivo
  «guardi i contatti sul sito»                            = negativo
  «scriva a info@ / alla direzione / all'indirizzo generico» = negativo:
  e' uno scaricabarile cortese, non un passaggio. Nel confronto del 7/9 tutti
  i modelli lo scambiavano per un'apertura.

DUE ERRORI DA NON FARE
- Un'agenzia di marketing, di comunicazione, di lead generation o un
  consulente Google Ads e' fuori_target, NON negativo: non e' un no, e' che
  non poteva essere un cliente. La differenza conta: negativo parla del nostro
  processo, fuori_target parla della lista.
- «Ok grazie», «ricevuto», «va bene» secchi dopo una mail di chiusura non
  sono un'apertura: sono negativo o tiepido, mai positivo. Le parole positive
  isolate non contano, conta cosa vuole fare la persona.

LA TRAPPOLA DELLE RISPOSTE AUTOMATICHE
Se il messaggio e' una risposta automatica di assenza la classe e' ooo, anche
se dentro ci sono parole che sembrano positive. MA se sotto o sopra
l'automatismo c'e' una risposta vera scritta da una persona, vince quella:
guarda chi ha scritto cosa, non le parole isolate.

QUANDO
Se il messaggio dice o lascia capire da quando ha senso riparlarne, scrivi la
data in formato AAAA-MM-GG. Per un fuori ufficio e' il primo giorno dopo il
rientro. Se non lo dice, scrivi -.

COME RISPONDI
Una riga per messaggio, niente altro: nessuna introduzione, nessun commento,
nessuna riga vuota, nessun elenco puntato.
Formato esatto, con le barre verticali:
NUMERO | classe | data-o-trattino | perche in massimo 10 parole"""


def _cache():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_BLOCCO = threading.Lock()
_CACHE_VIVA = None      # 2/10: rileggere il file a OGNI salvataggio rendeva il giro O(n²)


def _salva_cache(d):
    """Unisce e sostituisce il file in un colpo solo (29/9). Il file si legge UNA volta
    per processo (2/10: la sonda ha mostrato le bozze ferme a rileggere la cache per
    ogni lettura del gigante buono); fra processi vince l'ultimo che scrive, e al
    peggio si riperde qualche voce: la cache e' una comodita', non un dato."""
    global _CACHE_VIVA
    with _BLOCCO:
        try:
            if _CACHE_VIVA is None:
                _CACHE_VIVA = _cache()
            _CACHE_VIVA.update(d)
            tmp = f"{CACHE}.{os.getpid()}.{threading.get_ident()}"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_CACHE_VIVA, f, ensure_ascii=False)
            os.replace(tmp, CACHE)
        except Exception:
            pass


def _impronta(testo, modello=None):
    base = (modello or (MODELLO_OPENAI if FORNITORE == "openai" else MODELLO_CLAUDE)) + "\x00" + REGOLE + "\x00" + " ".join((testo or "").split())
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


# I FORNITORI CHE PARLANO COME OPENAI (8/10/2026).
#
# DeepSeek e xAI espongono lo stesso /chat/completions di OpenAI: cambia l'indirizzo
# e la chiave, non il resto. Tenerli qui dentro evita tre copie della stessa funzione
# con gli stessi tre tentativi e la stessa gestione del 429. Serve per il banco di
# prova dei modelli: si sceglie il fornitore coi numeri, non a opinione.
COMPATIBILI = {
    "openai":   ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
    "deepseek": ("https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY"),
    "xai":      ("https://api.x.ai/v1/chat/completions", "XAI_API_KEY"),
    "zai":      ("https://api.z.ai/api/paas/v4/chat/completions", "ZAI_API_KEY"),   # GLM (Z.ai), 8/10: solo l'API a consumo, il Coding Plan vieta gli script
}


def fornitore_di(modello):
    """Da che parte sta un modello, dal suo nome. Serve a provarne piu' di uno
    nello stesso giro senza cambiare le variabili d'ambiente a mano."""
    m = (modello or "").lower()
    if m.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    if m.startswith("deepseek"):
        return "deepseek"
    if m.startswith("grok"):
        return "xai"
    if m.startswith("glm"):
        return "zai"
    if m.startswith("claude"):
        return "claude"
    return FORNITORE


def _chiedi(prompt, modello=None):
    """L'unico punto che parla con un modello. Cambiare fornitore = cambiare qui."""
    f = fornitore_di(modello) if modello else FORNITORE
    if f in COMPATIBILI:
        return _chiedi_openai(prompt, modello or MODELLO_OPENAI, fornitore=f)
    return _chiedi_claude(prompt, modello or MODELLO_CLAUDE)


# IL TETTO ALL'USCITA (8/10/2026). Sul consumo misurato di settembre-ottobre l'uscita era
# il 46% dei token e l'85% della spesa: 2.355 token medi di ragionamento per chiamata,
# anche per una classificazione da dieci campi, e nessun limite da nessuna parte. Da qui
# ogni chiamata porta un tetto e uno sforzo; chi non li passa prende questi. I valori veri
# stanno nelle Regole del sistema nuovo; questi sono il massimo murato.
# 9/10, CORRETTO: il default a 4.000 troncava le analisi (risposta JSON lunga + ragionamento):
# dall'8/10 sera il cloud non generava piu' analisi, ogni risposta finiva «non in JSON». Il
# tetto stretto vale solo dove e' misurato e sicuro, le letture (1.500, uscita reale 454,
# 833 prove zero fallite): sono la grande maggioranza delle chiamate e il grosso del
# risparmio. Le chiamate lunghe e rare (analisi, bozze, piani) hanno un tetto largo, che
# ferma solo un ragionamento impazzito, non un testo legittimo.
TETTO_USCITA = {"lettura": 1500, "seconda": 4000, "bozza": 16000, "default": 16000}
SFORZO = {"lettura": "low", "seconda": "medium", "bozza": "medium", "default": "medium"}


def _chiedi_openai(prompt, modello, formato=None, fornitore=None, tetto=None, sforzo=None, scopo=None):
    fornitore = fornitore or (FORNITORE if FORNITORE in COMPATIBILI else "openai")
    dove, nome_chiave = COMPATIBILI[fornitore]
    chiave = _env(nome_chiave)
    if not chiave:
        raise RuntimeError(f"manca {nome_chiave} in .env.local")
    richiesta = {"model": modello, "messages": [{"role": "user", "content": prompt}],
                 "max_completion_tokens": int(tetto or TETTO_USCITA["default"])}
    if fornitore == "openai" and modello.startswith(("gpt-5", "o")):
        richiesta["reasoning_effort"] = sforzo or SFORZO["default"]   # solo i modelli che ragionano lo accettano
    if formato:
        richiesta["response_format"] = formato      # 29/9: la risposta in una forma fissa (il lettore unico)
    corpo = json.dumps(richiesta).encode()
    req = urllib.request.Request(
        dove, data=corpo, method="POST",
        headers={"Authorization": "Bearer " + chiave, "Content-Type": "application/json"})
    # il 429 di OpenAI e' quasi sempre «vai troppo veloce», non «sei a secco»:
    # in cloud partono 24 richieste insieme e il limite scatta. Si aspetta e si
    # riprova, a passi piu' lunghi; solo dopo tre tentativi si molla (22/9/2026).
    ultimo = None
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(req, timeout=ATTESA_MAX) as r:
                d = json.load(r)
            break
        except urllib.error.HTTPError as e:
            ultimo = f"OpenAI {e.code}: {e.read()[:200].decode(errors='replace')}"
            # 520 e' un guasto di Cloudflare davanti a OpenAI, 400 «something
            # went wrong reading your request» capita su siti con caratteri
            # strani: entrambi passano al secondo tentativo (22/9, visti in cloud)
            if e.code in (400, 429, 500, 502, 503, 520, 524) and tentativo < 2:
                time.sleep(5 * (tentativo + 1))
                continue
            raise RuntimeError(ultimo)
        except (urllib.error.URLError, TimeoutError) as e:
            ultimo = f"OpenAI rete: {str(e)[:120]}"
            if tentativo < 2:
                time.sleep(5 * (tentativo + 1))
                continue
            raise RuntimeError(ultimo)
    uso = d.get("usage", {})
    _conta_uso(modello, uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0), scopo)
    return d["choices"][0]["message"]["content"] or ""


# ── IL LETTORE UNICO (Dre, 29/9: «a») ───────────────────────────────
# Prima la stessa mail la leggevano quattro regole diverse (sync, analisi, lettura,
# bozze), e ognuna sbagliava a modo suo: misurate il 29/9 sulle 435 risposte che Dre
# ha classificato a mano, «ha detto no» ne prendeva 1 su 3 e «non scrivetemi piu'» 5 su
# 45. Qui una lettura sola risponde a tutte le domande secche, ognuna con la sua
# probabilita' (l'idea di Jev/TypeSafe, fatta col modello che abbiamo gia').
# 12/10: chi decide con queste probabilita' e' senso.giudica, con le soglie del Manuale.
# Le domande sono diventate undici: con ostile, ha_gia_analisi, non_e_lui, fuori_target e
# illeggibile la classe si calcola dalle probabilita', senza un secondo prompt con le classi.

# 12/10: la frase sta in OGNI domanda. Il 12/10 l'informativa in fondo alla mail
# («cancellare il messaggio») faceva leggere un no a chi aveva detto si'.
CONTANO_SOLO_LE_SUE_PAROLE = "(contano solo le sue parole: firme, disclaimer, informative e la nostra mail citata NON contano)"
DOMANDE = {k: f"{v} {CONTANO_SOLO_LE_SUE_PAROLE}" for k, v in {
    "autorisposta": "e' una risposta automatica (fuori ufficio, ferie, ticket, casella chiusa, rimbalzo, casella non presidiata)?",
    "detto_no": "la persona dice di no, che non le interessa, che ha gia' chi la segue?",
    # 12/10 (Manuale di Clara, gesto 13): «cita la privacy» faceva scattare il freno sui disclaimer
    # in firma; su 60 risposte vere tre si' sarebbero stati soppressi per sempre
    "non_contattare": "chiede CON PAROLE SUE, nel messaggio, di non essere piu' contattata o di essere cancellata dalle liste?",
    "ostile": "e' infastidita od ostile con noi: insulti, sarcasmo, «come avete avuto la mia mail», minaccia di segnalarci o denunciarci?",
    "vuole_analisi": "chiede o accetta di ricevere l'analisi o del materiale (anche solo «confermo la mail», «mandi pure»)?",
    "vuole_call": "chiede o accetta di sentirsi, una chiamata, un incontro?",
    "rinvio": "rimanda a piu' avanti (un mese, una data, «dopo l'estate»)?",
    "ha_gia_analisi": "dice di aver gia' ricevuto, letto o guardato la nostra analisi o il nostro materiale?",
    "non_e_lui": "dice che non e' la persona giusta, che non lavora piu' li', che l'indirizzo e' sbagliato, o che e' un privato?",
    "fuori_target": "e' un'agenzia o un concorrente, una casella legale o privacy, o un'azienda che non puo' essere cliente?",
    "illeggibile": "non c'e' un messaggio leggibile scritto da una persona (vuoto, solo firma, solo disclaimer, solo la nostra mail)?",
}.items()}
SCHEMA_LETTURA = {
    "type": "json_schema",
    "json_schema": {"name": "lettura", "strict": True, "schema": {
        "type": "object", "additionalProperties": False,
        "required": list(DOMANDE) + ["rinvio_quando", "girato_a", "domanda", "frase", "perche", "taglio_sporco"],
        "properties": {**{k: {"type": "number"} for k in DOMANDE},
                       "rinvio_quando": {"type": "string"}, "girato_a": {"type": "array", "items": {"type": "string"}},
                       "domanda": {"type": "string"}, "frase": {"type": "string"}, "perche": {"type": "string"},
                       "taglio_sporco": {"type": "boolean"}}}},
}
PROMPT_LETTURA = (
    "Sei il lettore delle risposte alle mail di Studio Galilei (agenzia di Treviso, marketing e Google Ads). "
    "Oggi e' {oggi}. Ti do la mail in tre blocchi. Il senso lo decide SOLO il primo blocco, quello che ha scritto la persona: "
    "il secondo (firma, informativa, mail citate) e il terzo (la nostra ultima mail e il nostro oggetto) servono "
    "a capire il contesto, e se ritrovi il loro testo dentro il primo blocco non e' suo. "
    "Rispondi a ogni domanda con una probabilita' da 0 a 1. Se il testo non basta per capire, dai valori vicini "
    "a 0.5: meglio un dubbio dichiarato che una certezza falsa.\n\nLE DOMANDE:\n{domande}\n\n"
    "Poi: rinvio_quando (AAAA-MM-GG: la data da cui ha senso riscrivergli; per un fuori ufficio il primo giorno di "
    "rientro; le date relative, come «la settimana prossima», «dopo l'estate», «con l'anno nuovo», calcolale da oggi; "
    "se non dice niente sul quando, vuoto), girato_a (indirizzi o nomi a cui "
    "ci rimanda, scritti come li scrive lui, altrimenti lista vuota), domanda (la domanda che ci fa, altrimenti vuoto), "
    "frase (la frase SUA che decide il senso, copiata alla lettera dal primo blocco, massimo 140 caratteri, altrimenti "
    "vuoto), perche (dieci parole), taglio_sporco (true se nel primo blocco c'e' testo che non e' suo: la nostra mail, "
    "una firma, un'informativa).\n\n"
    "QUELLO CHE HA SCRITTO LUI (conta solo questo):\n«{suo}»\n\n"
    "IL RESTO DELLA MAIL (serve a capire, non conta):\n«{resto}»\n\n"
    "LA NOSTRA ULTIMA MAIL E IL NOSTRO OGGETTO (se li ritrovi sopra, non sono suoi):\noggetto: {oggetto}\n«{nostra}»")


def _modello_lettura(modello=None):
    return modello or (MODELLO_OPENAI if FORNITORE == "openai" else MODELLO_CLAUDE)


# LA VERSIONE DEL LETTORE (12/10). La cache e le letture salvate si riconoscono da qui: prima
# l'impronta conteneva REGOLE e non DOMANDE (il cambio del 12/10 a non_contattare non aveva
# invalidato niente). Cambiare una domanda, lo schema, il prompt o il modello = versione nuova.
def _versione(prompt, domande, schema, modello):
    return hashlib.sha256(json.dumps([prompt, domande, schema, modello], ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()[:12]


VERSIONE = _versione(PROMPT_LETTURA, DOMANDE, SCHEMA_LETTURA, _modello_lettura())


def _blocco(t, quanto):
    return " ".join((t or "").split())[:quanto]


def classifica_risposta(testo, resto="", nostra="", oggetto="", modello=None):
    """Legge UNA risposta e torna le probabilita' per ogni domanda secca, piu' quando rinvia, a
    chi ci gira, cosa chiede e la frase che decide. `testo` e' gia' il testo suo (lettura.solo_suo);
    `resto` e' quello che il taglio ha tolto, `nostra` e `oggetto` la nostra ultima mail: arrivano
    in blocchi separati, cosi' se il taglio sbaglia l'AI non legge la nostra mail come sua (12/10).
    Mai un'eccezione: se non risponde torna None, e chi chiama tratta None come «senza AI»."""
    t = _blocco(testo, 2500)
    if len(t) < 3:
        return None
    domande = "\n".join(f"- {k}: {v}" for k, v in DOMANDE.items())
    # 12/10 sera: la data di oggi nel prompt. Senza, il modello lasciava vuota quasi ogni data relativa
    # («ci sentiamo con l'anno nuovo») e quasi ogni rientro dal fuori ufficio (54 su 59 nella misura)
    prompt = PROMPT_LETTURA.format(oggi=datetime.date.today().isoformat(), domande=domande, suo=t, resto=_blocco(resto, 1500) or "(niente)",
                                   nostra=_blocco(nostra, 1200) or "(non la so)", oggetto=_blocco(oggetto, 200) or "(non lo so)")
    global _CACHE_VIVA
    with _BLOCCO:
        if _CACHE_VIVA is None:
            _CACHE_VIVA = _cache()
    # 12/10: l'impronta porta la VERSIONE (domande, schema, prompt, modello) e tutti e tre i blocchi
    chiave_cache = _impronta("lettore2|" + VERSIONE + "|" + datetime.date.today().isoformat() + "|" + t + "|" + _blocco(resto, 1500) + "|" + _blocco(nostra, 1200) + "|" + _blocco(oggetto, 200), modello)
    cache = _CACHE_VIVA
    if chiave_cache in cache:
        return dict(cache[chiave_cache])
    try:
        f = fornitore_di(modello) if modello else FORNITORE
        if f in COMPATIBILI:
            grezzo = _chiedi_openai(prompt, _modello_lettura(modello), formato=SCHEMA_LETTURA, fornitore=f,
                                    tetto=TETTO_USCITA["lettura"], sforzo=SFORZO["lettura"], scopo="lettura")
        else:
            grezzo = _chiedi_claude(prompt + "\n\nRispondi SOLO con un oggetto JSON con esattamente quei campi.", modello or MODELLO_CLAUDE)
        m = re.search(r"\{.*\}", grezzo, re.S)
        r = json.loads(m.group(0)) if m else None
    except Exception as e:                                       # noqa: BLE001
        print(f"  (il lettore non ha risposto: {str(e)[:80]})")
        return None
    if not isinstance(r, dict) or any(not isinstance(r.get(k), (int, float)) or isinstance(r.get(k), bool) for k in DOMANDE):
        return None
    for d in DOMANDE:
        r[d] = max(0.0, min(1.0, float(r[d])))
    r["versione"] = VERSIONE
    cache[chiave_cache] = r
    _salva_cache(cache)
    return r


# LA SECONDA LETTURA (12/10). Quando la lista dei gravi e l'AI non sono d'accordo, o la
# lettura non torna (frase inventata, no e si' insieme, taglio sporco), non ci si blocca in
# silenzio: si rilegge UNA domanda, con piu' ragionamento. Se e' netta decide lei
# (senso.giudica), se resta a meta' il caso va a Dre.
SCHEMA_SECONDA = {
    "type": "json_schema",
    "json_schema": {"name": "seconda", "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "required": ["p", "dove", "perche"],
        "properties": {"p": {"type": "number"},
                       "dove": {"type": "string", "enum": ["suo", "firma", "informativa", "citazione", "nessuno"]},
                       "perche": {"type": "string"}}}},
}


def rileggi(testo_suo, contesa, prima=None, modello=None):
    """Una domanda sola, rifatta con piu' ragionamento. contesa = {campo, frase, da, direbbe}.
    Torna {campo, p, dove, perche} o None se non risponde (per chi chiama: dubbio a Dre)."""
    campo = (contesa or {}).get("campo") or "detto_no"
    domanda = DOMANDE.get(campo, DOMANDE["detto_no"])
    chi = "Una lista di parole" if (contesa or {}).get("da") == "lista" else "Una prima lettura"
    frase = (contesa or {}).get("frase") or ""
    perche = ((prima or {}).get("perche") or "").strip()
    prompt = (f"Sei la seconda lettura delle risposte alle mail di Studio Galilei. {chi} "
              + (f"ha trovato «{frase}» in questa risposta" if frase else "ha letto questa risposta")
              + f" e direbbe di si' a questa domanda: {domanda}\n"
              + (f"La prima lettura diceva: «{perche}».\n" if perche else "")
              + "Leggi SOLO quello che ha scritto la persona qui sotto. Dimmi:\n"
              f"- p: la probabilita' da 0 a 1 che la risposta alla domanda sia davvero si';\n"
              f"- dove: dove sta la frase trovata (suo = scritta da lei nel messaggio; firma; informativa = note legali "
              f"o privacy; citazione = la nostra mail citata; nessuno = non c'e');\n- perche: dieci parole.\n\n"
              f"LA RISPOSTA:\n«{_blocco(testo_suo, 2500)}»")
    try:
        f = fornitore_di(modello) if modello else FORNITORE
        if f in COMPATIBILI:
            grezzo = _chiedi_openai(prompt, _modello_lettura(modello), formato=SCHEMA_SECONDA, fornitore=f,
                                    tetto=TETTO_USCITA["seconda"], sforzo=SFORZO["seconda"], scopo="seconda")
        else:
            grezzo = _chiedi_claude(prompt + "\n\nRispondi SOLO con un oggetto JSON {p, dove, perche}.", modello or MODELLO_CLAUDE)
        m = re.search(r"\{.*\}", grezzo, re.S)
        r = json.loads(m.group(0)) if m else None
    except Exception as e:                                       # noqa: BLE001
        print(f"  (la seconda lettura non ha risposto: {str(e)[:80]})")
        return None
    if not isinstance(r, dict) or not isinstance(r.get("p"), (int, float)) or isinstance(r.get("p"), bool):
        return None
    return {"campo": campo, "p": max(0.0, min(1.0, float(r["p"]))), "dove": r.get("dove") or "nessuno",
            "perche": str(r.get("perche") or "")[:200]}


def decisioni(r):
    """Le soglie ASIMMETRICHE. Fermarsi costa poco, sbagliare verso il lead costa tanto:
    un dubbio sul «non contattare» ferma gia' a 0.2; un «sì» vale solo sopra 0.8 e senza
    nessun no in vista. Torna l'etichetta del metro e se c'e' un dubbio da far vedere a Dre."""
    if not r:
        return {"etichetta": "altro", "dubbio": True, "blocca": True}
    if r["non_contattare"] >= 0.2:
        return {"etichetta": "non_scrivere", "dubbio": r["non_contattare"] < 0.8, "blocca": True}
    if r["autorisposta"] >= 0.7:
        return {"etichetta": "fuori_ufficio", "dubbio": False, "blocca": False}
    if r["detto_no"] >= 0.5:
        return {"etichetta": "no", "dubbio": r["detto_no"] < 0.8, "blocca": True}
    if r["rinvio"] >= 0.6:
        return {"etichetta": "rinvio", "dubbio": r["rinvio"] < 0.8, "blocca": False}
    if max(r["vuole_analisi"], r["vuole_call"]) >= 0.8 and r["detto_no"] < 0.2:
        return {"etichetta": "si", "dubbio": False, "blocca": False}
    if max(r["vuole_analisi"], r["vuole_call"]) >= 0.5:
        return {"etichetta": "si", "dubbio": True, "blocca": False}
    return {"etichetta": "altro", "dubbio": True, "blocca": False}


def _chiedi_claude(prompt, modello):
    """Claude Code sul Mac col piano di Dre: solo come ponte, non va in cloud."""
    r = subprocess.run(["claude", "-p", "--model", modello], input=prompt,
                       capture_output=True, text=True, timeout=ATTESA_MAX)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "il cervello non ha risposto")[:200])
    return r.stdout


USO = os.path.expanduser("~/.odyn-uso-cervello.json")
_USO_DB = {"vivo": True}


def _conta_uso(modello, dentro, fuori, scopo=None):
    """Quanti token ha consumato il cervello, per modello: cosi' il costo si
    misura invece di temerlo. 12/10: anche nel database (tabella uso_modelli, schema_v81):
    il file muore col runner del direttore, e il costo di un giorno non si poteva dire.
    E' solo un contatore: se la scrittura non riesce non si ferma niente, e in prova a secco
    (PROVA=1, --prova) non si scrive."""
    try:
        d = json.load(open(USO, encoding="utf-8")) if os.path.exists(USO) else {}
        m = d.setdefault(modello, {"dentro": 0, "fuori": 0, "chiamate": 0})
        m["dentro"] += dentro; m["fuori"] += fuori; m["chiamate"] += 1
        json.dump(d, open(USO, "w", encoding="utf-8"))
    except Exception:
        pass
    if not _USO_DB["vivo"]:
        return
    try:
        import sys
        from stanza import sb, _a_secco
        if _a_secco():
            return
        sb("POST", "/rest/v1/uso_modelli", {"script": os.path.basename(sys.argv[0] or "?")[:60], "scopo": scopo or "altro",
                                             "modello": modello, "token_in": int(dentro or 0), "token_out": int(fuori or 0)},
           {"Prefer": "return=minimal"})
    except Exception:                                            # noqa: BLE001
        _USO_DB["vivo"] = False                  # tabella assente o rete giu': per questo giro solo il file


RIGA = re.compile(r"^\s*(\d+)\s*\|\s*([a-z_]+)\s*\|\s*([\d-]{1,10})\s*\|\s*(.*?)\s*$")


# IL RECAP DI UNA CALL (Dre, 15/9).
#
# «Per i recap vorrei il formato di Granola: è semplice e fa capire subito,
# quello di Google a volte mi rompe e non è così intuitivo.» Ha ragione: gli
# appunti di Gemini sono corretti ma lunghi, e nella Scheda diventano un muro
# che nessuno rilegge. Qui dentro tornano corti: due righe che dicono a che
# punto siamo, cosa ci si è detti, cosa si è deciso, chi fa cosa. Gli appunti
# interi restano dove sono, col link: non si butta niente, si legge meglio.
RECAP = """Sei l'assistente di uno studio italiano. Ti do gli appunti di una call con un cliente.
Riscrivili nel formato qui sotto, in italiano, come li scriverebbe chi c'era: corti, concreti, niente giri di parole.

FORMATO, esatto, salta le sezioni che restano vuote:

In due righe: <a che punto siamo, in massimo due frasi. La prima cosa che uno legge>

Cosa si sono detti
- <un punto per riga, massimo cinque, solo quello che conta>

Deciso
- <le decisioni prese, se ce ne sono>

Chi fa cosa
- Noi: <cosa tocca a noi, con la data se è stata detta>
- Loro: <cosa tocca a loro>

Resta aperto
- <le domande senza risposta, se ce ne sono>

REGOLE
Niente introduzioni e niente commenti tuoi: solo il formato.
Non inventare niente: se una cosa non è stata detta, la sezione non c'è.
Niente parole gonfie (innovativo, soluzioni, sinergia, a 360, ottimizzare, implementare).
Niente punti esclamativi, niente trattini lunghi, niente puntini elenco diversi da «- ».
I numeri e le date come sono stati detti.
Massimo quindici righe in tutto.

AZIENDA: {azienda}
QUANDO: {quando}

APPUNTI:
{testo}
"""


def recap(testo, azienda="", quando="", modello=None):
    """Gli appunti di una call, riscritti corti. Torna None se non ce la fa:
    chi chiama tiene quello che aveva, non resta senza niente."""
    grezzo = " ".join((testo or "").split())
    if len(grezzo) < 200:
        return None
    try:
        fuori = _chiedi(RECAP.format(azienda=azienda or "?", quando=quando or "?", testo=grezzo[:14000]) + istruzione("lettura"))
    except Exception:
        return None
    fuori = (fuori or "").strip()
    if len(fuori) < 60 or "In due righe" not in fuori:
        return None
    # le regole di casa valgono anche qui, senza fidarsi del modello
    fuori = re.sub(r"\s*—\s*", ": ", fuori).replace("–", "-").replace("·", ",").replace("•", "-")
    return fuori.replace("!", ".")


PREPARO = """Sei l'assistente di uno studio italiano di marketing e software.
Fra poche ore c'e' una call con questo cliente. Prepara chi ci va, in modo che
entri in call sapendo tutto senza dover leggere niente d'altro.

FORMATO, esatto, salta le sezioni che restano vuote:

Chi sono: <una riga: cosa fanno, dove, da dove sono arrivati>

A che punto siamo
- <massimo quattro righe: cosa ci siamo detti finora, cosa aspetta chi>

{blocco_domande}

Come parlargli
- <una riga: la taglia dell'azienda dal bilancio (micro sotto 1 M€, piccola fino a 10, media oltre), il registro e le parole
  da usare e da evitare: al titolare di una micro si parla di clienti e telefonate, non di budget e KPI; a una media
  di canale, costo per acquisizione e margine. Se il bilancio manca, salta la sezione>

Attento a
- <massimo due cose: promesse fatte, cose delicate, date scadute, un bilancio in perdita>

REGOLE
Solo quello che c'e' nei dati che ti do: se una cosa non la sai, non la scrivi.
Se c'e' il BILANCIO, le domande si adattano alla taglia: a una micro non chiedi il budget marketing,
chiedi quanti clienti nuovi in un mese cambierebbero le cose; a una media chiedi chi decide e quanto
spendono oggi. Il PREZZO SUGGERITO e' interno: serve a te per tarare le domande, non si nomina mai.
{regola_domande}
Niente introduzioni, niente commenti tuoi, niente consigli generici da manuale.
Niente parole gonfie (innovativo, soluzioni, sinergia, a 360, ottimizzare, implementare).
Niente punti esclamativi, niente trattini lunghi.
{righe_massime}

CALL: {quando}, {tipo}
AZIENDA: {azienda}

QUELLO CHE SAPPIAMO:
{dati}
"""


# LE DOMANDE DELLA CONOSCITIVA (regola di Dre del 12/8, scritta nel CLAUDE.md del vault e
# persa quando e' nato questo prompt: «massimo tre domande». Dre, 7/10, dopo una
# conoscitiva: «sono domande del cazzo: si va dal generico al preciso per creare rapporto e
# connessione, e allo stesso tempo dimostrare che si sa del settore e di loro, con la
# terminologia del settore in modo naturale; minimo 8 domande»).
DOMANDE_CONOSCITIVA = """Le domande
1. <prima domanda>
2. <seconda domanda>
<...fino a 8, 9 o 10 domande numerate>"""
REGOLA_CONOSCITIVA = """LE DOMANDE DELLA CONOSCITIVA (la regola di Dre): da 8 a 10 domande numerate, dal generico al preciso.
L'ordine: le prime due o tre aprono e creano rapporto (la loro storia, il territorio, cosa li rende
fieri); poi il loro mercato e i loro clienti; poi come lavorano oggi per trovarne di nuovi; poi i
numeri; le ultime due arrivano al punto (cosa cambierebbe davvero per loro, chi decide).
Servono a due cose insieme: creare rapporto e connessione, e far sentire che conosciamo il loro
settore e la loro azienda. Quindi ogni domanda usa in modo naturale le parole del LORO mestiere
(per un'agenzia immobiliare: incarichi, esclusive, acquisizioni, valutazioni, portali, provvigioni;
per un installatore: sopralluoghi, preventivi, cantieri, detrazioni; e cosi' via per ogni settore),
e dove puoi cita un dettaglio vero di loro (la zona, cosa vendono, cosa hanno scritto, l'analisi).
Mai domande da questionario generico («quali sono i vostri obiettivi?»): una domanda che potrebbe
andare a chiunque e' sbagliata. Una frase per domanda, scritta come la direbbe Dre a voce."""


def preparo(dati, azienda="", quando="", tipo="", modello=None):
    """Il punto della situazione prima di una call. None se non ce la fa."""
    grezzo = " ".join((dati or "").split())
    if len(grezzo) < 120:
        return None
    conoscitiva = "conoscitiva" in (tipo or "").lower()
    blocco = DOMANDE_CONOSCITIVA if conoscitiva else """Cosa chiedere
- <massimo tre domande vere, quelle che sbloccano la trattativa o il lavoro>"""
    try:
        fuori = _chiedi(PREPARO.format(azienda=azienda or "?", quando=quando or "?", tipo=tipo or "call", dati=grezzo[:14000],
                                       blocco_domande=blocco, regola_domande=REGOLA_CONOSCITIVA if conoscitiva else "",
                                       righe_massime="Massimo trenta righe in tutto." if conoscitiva else "Massimo quattordici righe in tutto.")
                        + istruzione("lettura"))
    except Exception:
        return None
    fuori = (fuori or "").strip()
    if len(fuori) < 50 or "Chi sono" not in fuori:
        return None
    if conoscitiva and len(re.findall(r"(?m)^\s*\d{1,2}[.)]\s", fuori)) < 8:
        return None                       # meno di 8 domande: la regola di Dre non e' rispettata, si riprova al giro dopo
    if re.search(r"prezzo suggerito|€/mese", fuori, re.I):
        fuori = "\n".join(r for r in fuori.splitlines() if not re.search(r"prezzo suggerito|€/mese", r, re.I))   # interno, non entra nella preparazione
    fuori = re.sub(r"\s*—\s*", ": ", fuori).replace("–", "-").replace("·", ",").replace("•", "-")
    return fuori.replace("!", ".")


# ── IL MANUALE DI CLARA (24/9/2026) ────────────────────────────────
# Dre: «c'è da darle tutti gli strumenti e le cose che le potrebbero servire, in
# ordine e struttura, e le regole». Il manuale e' la testa di Clara: un documento
# solo, nel bucket privato (riservato/manuale-clara.md), scritto da Achille con le
# regole di Dre e corretto da Dre. Ogni operazione lo carica per intero prima di
# fare qualsiasi cosa. Le parti: "testa" (il manuale), "outbound" (preflight,
# intenti, stile), "template" (le risposte di Dre parola per parola),
# "analisi" (playbook + esempio). Se il bucket non risponde, si va avanti con
# quello che c'e', e si dice.
_RISERVATO = {"testa": "manuale-clara.md", "outbound": None, "template": "risposte-template.md", "analisi": "playbook-analisi.md"}


def _dal_bucket(nome):
    import tempfile
    loc = os.path.join(tempfile.gettempdir(), "odyn-riservato-" + nome)
    if os.path.exists(loc) and time.time() - os.path.getmtime(loc) < 3600:
        return open(loc, encoding="utf-8").read()
    from stanza import env
    req = urllib.request.Request(f"{env('VITE_SUPABASE_URL')}/storage/v1/object/vault/riservato/{nome}",
                                 headers={"apikey": env("SUPABASE_SERVICE_KEY"), "Authorization": f"Bearer {env('SUPABASE_SERVICE_KEY')}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        testo = r.read().decode("utf-8")
    open(loc, "w", encoding="utf-8").write(testo)
    return testo


def manuale(*parti):
    """La testa di Clara, assemblata: manuale("testa", "outbound", "template")."""
    parti = parti or ("testa",)
    pezzi = []
    for p in parti:
        try:
            if p == "outbound":
                t = _env("PLAYBOOK_OUTBOUND") or ""
                if not t:
                    v = os.path.expanduser("~/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/ODYN Cockpit/riservato/clara-sg-outbound.md")
                    t = open(v, encoding="utf-8").read() if os.path.exists(v) else ""
            else:
                t = _dal_bucket(_RISERVATO[p])
            if t:
                pezzi.append(t)
        except Exception as e:                                       # noqa: BLE001
            print(f"  (manuale, parte «{p}» non caricata: {str(e)[:80]})")
    return "\n\n".join(pezzi)


def ruolo(nome):
    """Il mansionario del ruolo (scripts/ruoli/<NOME>.md): il lavoro, cosa puo'
    fare, cosa non puo' MAI fare, quando fermarsi e chiedere. Dal metodo dei
    quattro ruoli (29/9): ogni agente sa dove finisce il suo mestiere.
    Se il file manca si va avanti senza: e' una guida, non un requisito."""
    import os
    try:
        qui = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(qui, "ruoli", f"{nome.upper()}.md"), encoding="utf-8") as f:
            t = f.read().strip()
        return t + "\n\n" if t else ""
    except Exception:
        return ""


def istruzione(chiave):
    """Le istruzioni che Dre scrive nella sala di controllo (tabella istruzioni).
    Senza tabella o senza testo si va avanti senza: sono un di piu', non un requisito."""
    try:
        from stanza import sb
        r = sb("GET", f"/rest/v1/istruzioni?chiave=eq.{chiave}&select=testo&limit=1") or []
        t = (r[0].get("testo") or "").strip() if r else ""
        return f"\n\nISTRUZIONI DI DRE ({chiave}), che vincono su tutto il resto:\n{t}" if t else ""
    except Exception:
        return ""


def _leggi_gruppo(gruppo, modello=None):
    """gruppo: lista di (chiave, testo). Torna {chiave: verdetto}."""
    pezzi = []
    for i, (_, testo) in enumerate(gruppo, 1):
        t = " ".join((testo or "").split())[:1200]
        pezzi.append(f"--- messaggio {i} ---\n{t}")
    prompt = manuale("testa") + "\n\n" + REGOLE + istruzione("lettura") + "\n\nI MESSAGGI:\n\n" + "\n\n".join(pezzi)

    fuori = {}
    for riga in _chiedi(prompt, modello).splitlines():
        m = RIGA.match(riga)
        if not m:
            continue                      # le chiacchiere si buttano
        n, classe, quando, perche = m.groups()
        i = int(n) - 1
        if not (0 <= i < len(gruppo)) or classe not in CLASSI:
            continue
        fuori[gruppo[i][0]] = {
            "classe": classe,
            "quando": quando if re.fullmatch(r"\d{4}-\d{2}-\d{2}", quando) else None,
            "perche": perche[:120],
        }
    return fuori


def leggi(messaggi, quando_pronto=None, modello=None):
    """Legge dei messaggi e dice cosa vogliono dire.

    messaggi: lista di dizionari con almeno {"id": ..., "testo": ...}
    torna:    {id: {"classe","quando","perche"}} — solo per quelli capiti.

    Non solleva mai: se il cervello non risponde, torna quello che ha capito
    fin li'. Chi chiama deve saper vivere con una risposta parziale.
    """
    cache = _cache()
    fuori, da_leggere = {}, []
    for m in messaggi:
        testo = m.get("testo") or ""
        if len(testo.strip()) < 15:
            continue                      # una firma non e' un messaggio
        k = _impronta(testo, modello)
        if k in cache:
            fuori[m["id"]] = dict(cache[k])
            continue
        da_leggere.append((m["id"], testo, k))

    for i in range(0, len(da_leggere), A_GRUPPI_DI):
        gruppo = da_leggere[i:i + A_GRUPPI_DI]
        try:
            letti = _leggi_gruppo([(g[0], g[1]) for g in gruppo], modello)
        except Exception as e:
            print(f"  ! il cervello si e' fermato: {str(e)[:120]}")
            break
        per_id = {g[0]: g[2] for g in gruppo}
        for pid, v in letti.items():
            fuori[pid] = v
            cache[per_id[pid]] = v
        _salva_cache(cache)
        if quando_pronto:
            quando_pronto(min(i + A_GRUPPI_DI, len(da_leggere)), len(da_leggere))

    return fuori


def disponibile():
    """Il cervello c'e' e risponde?"""
    try:
        return "vivo" in _chiedi("Rispondi solo con la parola: vivo").lower()
    except Exception:
        return False


if __name__ == "__main__":
    print(f"fornitore: {FORNITORE}, modello: {MODELLO_OPENAI if FORNITORE == 'openai' else MODELLO_CLAUDE}")
    print("cervello disponibile:", disponibile())
    prova = [
        {"id": "a", "testo": "Thank you for your email. I am currently out of the office "
                             "with limited access to email. I will respond upon my return "
                             "on September 24th."},
        {"id": "b", "testo": "Buongiorno, guardi trovi tutti i contatti sul nostro sito. Saluti."},
        {"id": "c", "testo": "Interessante, ne parli col nostro direttore marketing "
                             "Luca Bianchi per approfondire, lo metto in copia."},
        {"id": "d", "testo": "Grazie ma siamo un'agenzia di marketing anche noi, "
                             "facciamo lo stesso lavoro vostro."},
    ]
    for k, v in leggi(prova).items():
        print(f"  {k}: {v['classe']:14} {str(v['quando'] or '-'):12} {v['perche']}")
