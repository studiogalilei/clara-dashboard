#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA STRADA VELOCE: una risposta, un lead, subito (21/10/2026).

PERCHE'
Dre, 21/10 alle 14: «TUTTE le cose le voglio in realtime». Il collaudo della mattina diceva: la
prima risposta entrava in 5 minuti, ma quella DOPO l'analisi (la conversazione di Dre) in 65-110,
e il telefono suonava 82-108 minuti dopo la mail. Non perche' i pezzi fossero lenti: ognuno
aspettava il giro del direttore, e il campanello di Smartlead lanciava il direttore intero, che il
cron annullava 2 volte su 3.

COSA FA
Per UN lead, in fila, senza aspettare nessun giro:
  1. il suo filo da Smartlead, scritto in prospects e interactions con LE STESSE funzioni del sync
     (sync_v2.sincronizza_lead -> sincronizza_filo: il corpo del giro, non una copia); dentro c'e'
     gia' il lettore AI sulla sua mail (quando la risposta e' nuova);
  2. la misura: «risposta entrata dopo N minuti», dall'ora della mail su Smartlead a adesso, in
     snella_numeri «risposte_veloci» (la scheda Clara la mette nel diario);
  3. le conversazioni (scripts/conversazioni.py): la notifica sul telefono se la palla e' a Dre;
  4. la sua scheda nell'app (schede.py --uno);
  5. il foglio (foglio.py, un giro intero: 15-25 secondi) con la scheda Clara;
  6. se e' un si' senza analisi, il lampo per lui (lampo.py --email): fit, analisi, bozza, e i
     cancelli di sempre (prima_risposta, manda).
Ogni passo ha il suo try/except: uno che cade non ferma gli altri, e lo si legge nel registro
(la corsa in `corse`, operazione «risposta», con i secondi di ogni tratto).

IDEMPOTENTE. Due chiamate per la stessa mail non fanno danni: il sync trova la stessa risposta
(non nuova, niente lettore), le interactions sono uniche, la conversazione gia' in memoria non
suona due volte, la misura resta la prima, il lampo salta chi ha gia' una proposta o l'analisi.

CHI LA CHIAMA
.github/workflows/risposta.yml, lanciato da supabase/functions/smartlead-webhook a ogni EMAIL_REPLY
(gruppo risposta-<email>, mai annullato). Il direttore col suo sync resta la rete di sicurezza.

USO
  python3 scripts/risposta.py --email <email> [--campagna <id>] [--prova]
  --oppure <email2>   un secondo indirizzo da provare se Smartlead non conosce il primo
  --bussato <iso>     quando Smartlead ha bussato (per misurare l'avvio di GitHub)
  --prova             legge e misura, non scrive e non manda (vale per tutti i pezzi)
"""
import datetime
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from stanza import sb, quando, _a_secco                         # noqa: E402

PROVA = _a_secco()
OPERAZIONE = "risposta"
CHIAVE_MISURE = "risposte_veloci"
TIENI_MISURE = datetime.timedelta(days=3)
ATTESA_RIPROVA = 20          # secondi: se Smartlead ha bussato ma il filo non ha ancora la mail nuova
REGISTRO = []                # [(passo, esito, secondi, nota)]


def arg(nome, default=None):
    if nome in sys.argv and sys.argv.index(nome) + 1 < len(sys.argv):
        v = sys.argv[sys.argv.index(nome) + 1]
        return v if v and not v.startswith("--") else default
    return default


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def _utc(iso):
    """Un'ora di Smartlead («2026-10-21T08:49:26», senza fuso: e' UTC) come datetime con fuso."""
    if not iso:
        return None
    t = quando(str(iso))
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def passo(nome, fn):
    """Un tratto della strada: misurato, e un errore non ferma gli altri (regola 4 del 28/9)."""
    t0 = time.time()
    print(f"▶ {nome}")
    try:
        out = fn()
        REGISTRO.append((nome, "ok", time.time() - t0, ""))
        return out
    except Exception as e:                                       # noqa: BLE001
        REGISTRO.append((nome, "errore", time.time() - t0, f"{type(e).__name__}: {str(e)[:300]}"))
        print(f"  {nome}: non riuscito ({type(e).__name__}: {str(e)[:200]}); vado avanti")
        return None


def _sotto(nome, argomenti, minuti):
    """Uno script di sempre, come processo suo (cosi' i suoi interruttori valgono e un suo crash non
    tocca il resto). Torna le ultime righe di quello che ha detto; alza se cade."""
    extra = ["--prova"] if PROVA else []
    r = subprocess.run([sys.executable, os.path.join(HERE, nome)] + argomenti + extra,
                       capture_output=True, text=True, timeout=minuti * 60, cwd=RADICE)
    uscita = ((r.stdout or "") + ("\n" + r.stderr if r.stderr else "")).strip()
    for riga in uscita.splitlines()[-6:]:
        print("  " + riga[:160])
    if r.returncode != 0:
        raise RuntimeError(f"{nome} e' uscito con {r.returncode}: {uscita[-300:]}")
    return uscita


# ── 1. il filo da Smartlead, con le funzioni del sync ────────────────────

def sincronizza(email, campagna, oppure, bussato):
    import sync_v2 as S
    if PROVA:
        S.DRY = True                               # la prova a secco del sync, qualunque sia la riga di comando
    esito = S.sincronizza_lead(email, campagna)
    if not esito.get("trovato") and oppure:
        print(f"  Smartlead non conosce il primo indirizzo ({esito.get('perche')}): provo il secondo")
        esito = S.sincronizza_lead(oppure, campagna)
        if esito.get("trovato"):
            esito["email"] = oppure
    esito.setdefault("email", email)
    # Smartlead ha bussato per una mail che nel filo non c'e' ancora? (la storia arriva un attimo dopo)
    if bussato and esito.get("trovato") and not esito.get("nuova"):
        ultima = _utc(esito.get("ultima_risposta"))
        if ultima and _utc(bussato) - ultima > datetime.timedelta(minutes=10):
            print(f"  il filo non ha ancora la mail nuova: riprovo fra {ATTESA_RIPROVA} secondi")
            time.sleep(ATTESA_RIPROVA)
            esito = {**esito, **S.sincronizza_lead(esito["email"], campagna)}
    if not esito.get("trovato"):
        raise RuntimeError(f"lead non sincronizzato: {esito.get('perche')}")
    rec = esito.get("rec") or {}
    lett = ((rec.get("enriched") or {}).get("lettore") or {})
    letta = esito.get("lettore_nuovo") or (lett.get("fonte") == "lettore" and (lett.get("risposta_il") or "")[:19] == (esito.get("ultima_risposta") or "")[:19])
    com_e = "nuova" if esito.get("nuova") else "gia' nota"
    palla = "aspetta noi" if esito.get("awaiting") else "palla a lui"
    lettore = "ha letto adesso" if esito.get("lettore_nuovo") else ("gia' letta" if letta else "liste")
    print(f"  filo letto: risposta delle {esito.get('ultima_risposta')} UTC, {com_e}, classe «{esito.get('cls')}», {palla}, lettore AI: {lettore}")
    return esito


# ── 2. la misura ──────────────────────────────────────────────────────────

def misura(esito, bussato, partita):
    """Dall'ora della mail su Smartlead a adesso, in minuti; scritta una volta per mail."""
    ultima = _utc(esito.get("ultima_risposta"))
    if not ultima:
        raise RuntimeError("il filo non dice l'ora della risposta")
    ora = adesso()
    minuti = round((ora - ultima).total_seconds() / 60, 1)
    tratti = {"mail_il": ultima.isoformat(timespec="seconds")}
    if bussato:
        b = _utc(bussato)
        tratti["smartlead_al_campanello_s"] = int((b - ultima).total_seconds())
        tratti["campanello_alla_corsa_s"] = int((partita - b).total_seconds())
    print(f"  risposta entrata dopo {minuti} minuti dalla mail" + (f" (campanello +{tratti['smartlead_al_campanello_s']}s, avvio corsa +{tratti['campanello_alla_corsa_s']}s)" if bussato else ""))
    pid = (esito.get("rec") or {}).get("id")
    if PROVA or not pid:
        print("  (prova: la misura non si scrive)" if PROVA else "  (lead senza scheda: la misura non si scrive)")
        return minuti
    chiave = f"{pid}:{(esito.get('ultima_risposta') or '')[:19]}"
    dati = (sb("GET", f"/rest/v1/snella_numeri?select=dati&chiave=eq.{CHIAVE_MISURE}") or [{}])[0].get("dati") or {}
    if chiave in dati:
        print(f"  (gia' misurata: {dati[chiave].get('minuti')} minuti, resta quella)")
        return dati[chiave].get("minuti")
    dati = {k: v for k, v in dati.items() if isinstance(v, dict) and v.get("entrata_il") and ora - quando(v["entrata_il"]) < TIENI_MISURE}
    dati[chiave] = {"pid": pid, "minuti": minuti, "entrata_il": ora.isoformat(timespec="seconds"), "via": "campanello" if bussato else "a mano", **tratti}
    sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave",
       [{"chiave": CHIAVE_MISURE, "dati": dati, "aggiornato_il": ora.isoformat(timespec="seconds")}],
       {"Prefer": "resolution=merge-duplicates,return=minimal"})
    return minuti


# ── 3. la notifica, se la palla e' a Dre ──────────────────────────────────

def conversazioni():
    import segnale_provvisorio as S
    import conversazioni as C
    S.GIRO.update(pagate=0, memoria_rotta=False, sonda=False, giorno_restano=None, tetto_giorno=False)
    return C.giro(prova=PROVA)


# ── 6. il lampo, se e' un si' senza analisi ───────────────────────────────

def serve_il_lampo(esito):
    rec = esito.get("rec") or {}
    return esito.get("cls") == "positivo" and esito.get("awaiting") and not rec.get("analysis_sent")


# ── il registro ───────────────────────────────────────────────────────────

def registra(email, esito, minuti, partita):
    durata = int((adesso() - partita).total_seconds() * 1000)
    caduti = [r for r in REGISTRO if r[1] == "errore"]
    righe = [f"{n}: {e} in {s:.1f}s" + (f" ({nota})" if nota else "") for n, e, s, nota in REGISTRO]
    testa = (f"strada veloce per un lead: {'ok' if not caduti else str(len(caduti)) + ' passi caduti'}; "
             f"risposta entrata dopo {minuti} minuti" if minuti is not None else "strada veloce: il filo non si e' letto")
    dettaglio = testa + "\n" + "\n".join(righe)
    print("\n" + dettaglio)
    if PROVA:
        print("(prova: la corsa non si registra)")
        return
    try:
        sb("POST", "/rest/v1/operazioni?on_conflict=chiave",
           [{"chiave": OPERAZIONE, "nome": "La strada veloce", "comando": None, "cadenza_minuti": 525600, "ordine": 26, "attiva": True}],
           {"Prefer": "resolution=ignore-duplicates,return=minimal"})
        sb("PATCH", f"/rest/v1/operazioni?chiave=eq.{OPERAZIONE}",
           {"ultima_corsa": adesso().isoformat(), "ultimo_esito": "ok" if not caduti else "errore",
            "ultimo_dettaglio": dettaglio[-500:], "ultima_durata_ms": durata})
        sb("POST", "/rest/v1/corse", {"operazione": OPERAZIONE, "esito": "ok" if not caduti else "errore",
                                       "dettaglio": dettaglio[-2000:], "righe": int(round(minuti)) if minuti is not None else None,
                                       "durata_ms": durata})
    except Exception as e:                                       # noqa: BLE001
        print(f"  (corsa non registrata: {str(e)[:120]})")


def main():
    email = (arg("--email") or "").strip().lower()
    if not email or "@" not in email:
        sys.exit("uso: python3 scripts/risposta.py --email <email> [--campagna <id>] [--prova]")
    campagna = arg("--campagna")
    oppure = (arg("--oppure") or "").strip().lower() or None
    bussato = arg("--bussato")
    evento = arg("--evento") or "EMAIL_REPLY"
    partita = adesso()
    print(f"STRADA VELOCE {'(prova) ' if PROVA else ''}per un lead, evento {evento}, {partita:%H:%M:%S} UTC")

    esito = passo("filo da Smartlead (sync + lettore)", lambda: sincronizza(email, campagna, oppure, bussato))
    if not esito:
        registra(email, None, None, partita)
        sys.exit(2)
    email = esito.get("email") or email
    minuti = passo("misura", lambda: misura(esito, bussato, partita))
    passo("conversazioni (la notifica a Dre)", conversazioni)
    passo("scheda nell'app", lambda: _sotto("schede.py", ["--uno", email], 3))
    passo("foglio e scheda Clara", lambda: _sotto("foglio.py", [], 5))
    if serve_il_lampo(esito):
        passo("lampo (si' senza analisi)", lambda: _sotto("lampo.py", ["--email", email], 15))
    else:
        rec = esito.get("rec") or {}
        perche = "ha gia' l'analisi" if rec.get("analysis_sent") else "non e' un si' che aspetta noi"
        print(f"  niente lampo: {perche}")
    registra(email, esito, minuti, partita)


if __name__ == "__main__":
    main()
