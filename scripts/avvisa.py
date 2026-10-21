#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AVVISA — la notifica sul telefono di Dre, Web Push (7/9/2026).

PERCHE' WEB PUSH E NON UN'APP
Dre: «una webapp che mi aggiungo in Home sull'iPhone, deve inviare
notifiche». La Dashboard e' gia' una web app installabile; il browser le da'
un indirizzo a cui mandare i messaggi, e lo salva nelle preferenze (chiave
push-iscrizioni: una lista, telefono e computer insieme). Questo script
prende quegli indirizzi e manda. Niente store, niente Telegram, niente
servizi in mezzo: lo standard del browser, che regge da anni.

COME SI ACCENDE
Le chiavi VAPID (VITE_VAPID_PUBLIC nel browser, VAPID_PRIVATE qui) sono nei
secret di GitHub e in .env.local. Dre preme «Attiva le notifiche» in
Impostazioni dalla Dashboard aperta dalla Home dell'iPhone. Serve che la
Dashboard stia su https (dopo il deploy).

Senza chiavi o senza iscrizioni avvisa() non fa niente e non rompe niente:
gli script chiamanti non devono saperlo. Gli indirizzi morti (410/404) si
tolgono da soli. SENZA_PUSH=1 (le prove) spegne tutto.

USO
  from avvisa import avvisa; avvisa("3 bozze da approvare")
  python3 scripts/avvisa.py "prova"         manda un messaggio a tutti gli iscritti
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import env, sb, per_dre                        # noqa: E402

DASHBOARD = env("DASHBOARD_URL") or "./"
MITTENTE = "mailto:dramane@studiogalilei.com"
TTL = 6 * 3600          # sei ore: un telefono spento la riceve alla riaccensione; dopo, c'e' la mail
ATTESA = 10             # secondi: il servizio di push lento non tiene fermo il giro


def _morto(e):
    """Un indirizzo che non esiste piu' (404/410): il telefono ha tolto l'app o il permesso."""
    codice = getattr(getattr(e, "response", None), "status_code", None)
    return codice in (404, 410)


def manda_a(iscrizione, testo, titolo="Clara", url=None, tag=None, privata=None):
    """Una notifica a UN dispositivo. Torna True se il servizio l'ha presa; un indirizzo morto
    alza IndirizzoMorto, gli altri errori salgono come sono (chi chiama decide)."""
    webpush, WebPushException = _libreria()
    privata = privata or env("VAPID_PRIVATE")
    dati = {"titolo": titolo, "testo": testo, "url": url or DASHBOARD}
    if tag:
        dati["tag"] = tag
    try:
        webpush(subscription_info={"endpoint": iscrizione["endpoint"], "keys": iscrizione.get("keys") or {}},
                data=json.dumps(dati), vapid_private_key=privata, vapid_claims={"sub": MITTENTE},
                ttl=TTL, timeout=ATTESA)
        return True
    except WebPushException as e:
        if _morto(e):
            raise IndirizzoMorto(iscrizione["endpoint"]) from e
        raise


class IndirizzoMorto(Exception):
    pass


def _libreria():
    """pywebpush (installata nel direttore). Una funzione sola, cosi' le prove la sostituiscono."""
    from pywebpush import webpush, WebPushException
    return webpush, WebPushException


def utente(email):
    """L'id di chi ha questa mail (per mandare a una persona sola, es. Dre)."""
    email = (email or "").strip().lower()
    r = sb("GET", "/auth/v1/admin/users?page=1&per_page=1000") or {}
    for u in (r.get("users") if isinstance(r, dict) else r) or []:
        if (u.get("email") or "").lower() == email:
            return u["id"]
    return None


def avvisa(testo, titolo="Clara", url=None, a=None, tag=None):
    """Manda ai dispositivi iscritti di `a` (lista di user id; None = ai ceo). Torna quanti hanno ricevuto.
    Non alza mai per un dispositivo: un errore si scrive e si va avanti, un indirizzo morto si toglie."""
    testo, titolo = per_dre(testo), per_dre(titolo)         # niente «·» sul telefono (22/10)
    privata = env("VAPID_PRIVATE")
    if not privata or os.environ.get("SENZA_PUSH"):
        return 0
    try:
        _libreria()
    except ImportError:
        print("  (pywebpush non installato: niente notifica)")
        return 0
    if a is None:
        # senza destinatari espliciti si avvisa la direzione: le bozze e le domande sono loro
        a = [r["id"] for r in (sb("GET", "/rest/v1/profili?select=id&ruolo=eq.ceo") or [])]
    righe = [r for r in (sb("GET", "/rest/v1/preferenze?select=owner,valore&chiave=eq.push-iscrizioni") or []) if r.get("owner") in a]
    mandate = 0
    for r in righe:
        iscrizioni = r.get("valore") if isinstance(r.get("valore"), list) else []
        morti = set()
        for i in iscrizioni:
            if not i.get("endpoint"):
                continue
            try:
                manda_a(i, testo, titolo=titolo, url=url, tag=tag, privata=privata)
                mandate += 1
            except IndirizzoMorto:
                print(f"  (indirizzo morto, tolto: {i['endpoint'][:40]}…)")
                morti.add(i["endpoint"])
            except Exception as e:                       # noqa: BLE001
                print(f"  (push non mandata: {str(e)[:160]})")
        if morti:
            togli_morti(r["owner"], morti)
    return mandate


def togli_morti(owner, morti):
    """Toglie gli indirizzi morti rileggendo la lista appena prima di scrivere: un dispositivo
    iscritto nel frattempo (dal telefono, mentre il giro mandava) non si perde."""
    ora = sb("GET", f"/rest/v1/preferenze?select=valore&owner=eq.{owner}&chiave=eq.push-iscrizioni") or []
    lista = ora[0].get("valore") if ora and isinstance(ora[0].get("valore"), list) else []
    vive = [i for i in lista if i.get("endpoint") not in morti]
    if len(vive) != len(lista):
        sb("PATCH", f"/rest/v1/preferenze?owner=eq.{owner}&chiave=eq.push-iscrizioni", {"valore": vive})


BENVENUTO_TENTATIVI = 3


def benvenuti():
    """La notifica di prova a chi ha appena premuto «Attiva le notifiche» (17/10).
    Il browser segna l'iscrizione nuova con benvenuto: «da-mandare» (src/lib/notifiche.ts); qui le
    si manda «Notifiche attive» dal cloud, con la stessa strada degli avvisi veri: se arriva sul
    telefono, arrivano anche gli altri. Poi benvenuto diventa la data. Tre tentativi e basta
    (benvenuto: «fallito», e lo si dice nel registro), un indirizzo morto si toglie.
    Torna quante ne ha mandate."""
    if not env("VAPID_PRIVATE") or os.environ.get("SENZA_PUSH"):
        return 0
    righe = sb("GET", "/rest/v1/preferenze?select=owner,valore&chiave=eq.push-iscrizioni") or []
    mandate = 0
    for r in righe:
        lista = r.get("valore") if isinstance(r.get("valore"), list) else []
        esiti = {}
        for i in lista:
            if i.get("benvenuto") != "da-mandare" or not i.get("endpoint"):
                continue
            try:
                manda_a(i, "Da adesso gli avvisi del Workspace arrivano anche qui. Tocca per aprire Oggi.",
                        titolo="Notifiche attive", url=_base() + "#/s/oggi", tag="benvenuto")
                esiti[i["endpoint"]] = "mandata"
                mandate += 1
            except IndirizzoMorto:
                esiti[i["endpoint"]] = "morto"
            except Exception as e:                       # noqa: BLE001
                print(f"  (prova di notifica non mandata: {str(e)[:160]})")
                esiti[i["endpoint"]] = "errore"
        if esiti:
            _segna_benvenuti(r["owner"], esiti)
    if mandate:
        print(f"  notifiche di prova mandate: {mandate}")
    return mandate


def _base():
    return (env("DASHBOARD_URL") or "https://studiogalilei.github.io/clara/").split("#")[0]


def _segna_benvenuti(owner, esiti):
    """Si rilegge la lista appena prima di scrivere (un dispositivo nuovo nel frattempo non si perde)."""
    import datetime
    ora = sb("GET", f"/rest/v1/preferenze?select=valore&owner=eq.{owner}&chiave=eq.push-iscrizioni") or []
    lista = ora[0].get("valore") if ora and isinstance(ora[0].get("valore"), list) else []
    nuova = []
    for i in lista:
        e = esiti.get(i.get("endpoint"))
        if e == "morto":
            continue
        if e == "mandata":
            i = {**i, "benvenuto": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        elif e == "errore":
            n = int(i.get("benvenuto_tentativi") or 0) + 1
            i = {**i, "benvenuto_tentativi": n, **({"benvenuto": "fallito"} if n >= BENVENUTO_TENTATIVI else {})}
            if n >= BENVENUTO_TENTATIVI:
                print(f"  LA PROVA DI NOTIFICA NON PARTE da {n} giri: {i.get('dispositivo', '?')[:40]}")
        nuova.append(i)
    sb("PATCH", f"/rest/v1/preferenze?owner=eq.{owner}&chiave=eq.push-iscrizioni", {"valore": nuova})


def main():
    testo = " ".join(sys.argv[1:]) or "Prova di notifica"
    n = avvisa(testo)
    print(f"mandata a {n} dispositivi" if n else "non mandata (manca VAPID_PRIVATE, pywebpush, o nessuno e' iscritto)")


if __name__ == "__main__":
    main()
