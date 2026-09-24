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

import hashlib
import json
import os
import re
import subprocess
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
          "fuori_target", "da_classificare")

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
negativo      chiude: «non interessati», «rimuovetemi», «abbiamo gia'
              un'agenzia» detto come stop senza finestra futura, oppure ti
              scarica in modo generico («guardi i contatti sul sito»).
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


def _salva_cache(d):
    try:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except Exception:
        pass          # la cache e' una comodita', non un dato: se salta, pazienza


def _impronta(testo, modello=None):
    base = (modello or (MODELLO_OPENAI if FORNITORE == "openai" else MODELLO_CLAUDE)) + "\x00" + REGOLE + "\x00" + " ".join((testo or "").split())
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def _chiedi(prompt, modello=None):
    """L'unico punto che parla con un modello. Cambiare fornitore = cambiare qui."""
    if FORNITORE == "openai":
        return _chiedi_openai(prompt, modello or MODELLO_OPENAI)
    return _chiedi_claude(prompt, modello or MODELLO_CLAUDE)


def _chiedi_openai(prompt, modello):
    chiave = _env("OPENAI_API_KEY")
    if not chiave:
        raise RuntimeError("manca OPENAI_API_KEY in .env.local")
    corpo = json.dumps({
        "model": modello,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=corpo, method="POST",
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
    _conta_uso(modello, uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0))
    return d["choices"][0]["message"]["content"] or ""


def _chiedi_claude(prompt, modello):
    """Claude Code sul Mac col piano di Dre: solo come ponte, non va in cloud."""
    r = subprocess.run(["claude", "-p", "--model", modello], input=prompt,
                       capture_output=True, text=True, timeout=ATTESA_MAX)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "il cervello non ha risposto")[:200])
    return r.stdout


USO = os.path.expanduser("~/.odyn-uso-cervello.json")


def _conta_uso(modello, dentro, fuori):
    """Quanti token ha consumato il cervello, per modello: cosi' il costo si
    misura invece di temerlo."""
    try:
        d = json.load(open(USO, encoding="utf-8")) if os.path.exists(USO) else {}
        m = d.setdefault(modello, {"dentro": 0, "fuori": 0, "chiamate": 0})
        m["dentro"] += dentro; m["fuori"] += fuori; m["chiamate"] += 1
        json.dump(d, open(USO, "w", encoding="utf-8"))
    except Exception:
        pass


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

Cosa chiedere
- <massimo tre domande vere, quelle che sbloccano la trattativa o il lavoro>

Attento a
- <massimo due cose: promesse fatte, cose delicate, date scadute>

REGOLE
Solo quello che c'e' nei dati che ti do: se una cosa non la sai, non la scrivi.
Niente introduzioni, niente commenti tuoi, niente consigli generici da manuale.
Niente parole gonfie (innovativo, soluzioni, sinergia, a 360, ottimizzare, implementare).
Niente punti esclamativi, niente trattini lunghi.
Massimo dodici righe in tutto.

CALL: {quando}, {tipo}
AZIENDA: {azienda}

QUELLO CHE SAPPIAMO:
{dati}
"""


def preparo(dati, azienda="", quando="", tipo="", modello=None):
    """Il punto della situazione prima di una call. None se non ce la fa."""
    grezzo = " ".join((dati or "").split())
    if len(grezzo) < 120:
        return None
    try:
        fuori = _chiedi(PREPARO.format(azienda=azienda or "?", quando=quando or "?", tipo=tipo or "call", dati=grezzo[:14000]) + istruzione("lettura"))
    except Exception:
        return None
    fuori = (fuori or "").strip()
    if len(fuori) < 50 or "Chi sono" not in fuori:
        return None
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
