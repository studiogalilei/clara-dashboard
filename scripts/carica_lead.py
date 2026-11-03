"""CARICA UNA LISTA DI LEAD IN UNA CAMPAGNA SMARTLEAD, PULITA (Dre, 22/10).

  python3 scripts/carica_lead.py lista.csv --campagna 4003942          # prova a secco: solo conteggi
  python3 scripts/carica_lead.py lista.csv --campagna 4003942 --vero   # carica
  python3 scripts/carica_lead.py --pausa-generiche [--vero]            # mette in pausa le generiche mai contattate
  python3 scripts/carica_lead.py --controlla-ads 4003943 4003947 [--vero]  # pausa a chi fa gia' Ads sul serio
  python3 scripts/carica_lead.py --controlla-icebreaker 4003942 [--vero]   # pausa a chi ha un icebreaker storto

Le regole, tutte prima di caricare:
- solo mail personali (stanza.mail_personale) e verificate (colonna result = ok, se c'e');
- niente doppioni: ne' nel file, ne' gia' in una campagna Smartlead, ne' nel database;
- niente aziende gia' scritte (un'altra persona della stessa azienda e' gia' in Smartlead);
- niente aziende cliente, in pipeline, perse o che hanno detto no;
- serve il nome e l'icebreaker (la prima mail li usa);
- l'icebreaker deve reggere la frase della prima mail: "abbiamo dato un'occhiata a {azienda}, {icebreaker},
  vi faccio i miei complimenti". Prima le regole fisse (icebreaker_storto), poi un giudice (icebreaker_ko).
  Origine: il 3/11 un lead ha ricevuto "il sito non e' disponibile, vi faccio i miei complimenti".
Il CSV e' quello di Lorenzo: first_name, last_name, email, website, company_clean_final (o company_name),
icebreaker, role, result. Stampa solo numeri: mai mail o nomi (il repo e' pubblico, i log pure).
La pausa usa il comando pausa di Smartlead (reversibile), mai DELETE; tocca solo chi non ha ricevuto
nessuna mail e non ha risposto.
"""
import argparse, collections, csv, json, os, re, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import stanza
from sync_v2 import sl_get, sl_post

ATTIVE = ("ACTIVE",)


def campagne():
    return sl_get("/campaigns/")


def lead_di(cid):
    off, tutti = 0, []
    while True:
        ls = (sl_get(f"/campaigns/{cid}/leads?limit=100&offset={off}") or {}).get("data") or []
        tutti += ls
        off += 100
        if len(ls) < 100:
            return tutti


def gia_in_smartlead():
    mail, domini = set(), set()
    for c in campagne():
        for x in lead_di(c["id"]):
            e = (x["lead"].get("email") or "").lower()
            mail.add(e)
            if stanza.dominio_vero(e):
                domini.add(stanza.dominio_vero(e))
    return mail, domini


def bloccati_dal_database():
    pros = stanza.sb_tutte("/rest/v1/prospects?select=id,email,fuori,stage,pipeline_stage,no_followup,classificazione")
    mail = {(p.get("email") or "").lower() for p in pros}
    domini = set()
    for p in pros:
        fermo = (p.get("fuori") or p.get("stage") in ("cliente", "perso") or p.get("pipeline_stage") in ("cliente", "perso")
                 or p.get("no_followup") or p.get("classificazione") in ("soppresso", "nervoso"))
        d = stanza.dominio_vero(p.get("email"))
        if fermo and d:
            domini.add(d)
    return mail, domini


FRASE_PRIMA_MAIL = "Insieme al mio collega abbiamo dato un'occhiata a {azienda}, {icebreaker}, vi faccio i miei complimenti."
STORTI = re.compile(r"\b(la tua|il tuo|i tuoi|le tue|non (e'|è) (attualmente )?disponibile|non disponibile|in costruzione|"
                    r"manutenzione|non funziona|irraggiungibile|complimenti)\b|https?:|www\.|\{|\}", re.I)


def icebreaker_storto(i):
    """Le regole fisse: vuoto, tu al posto del voi, sito giu' o in costruzione, link, variabili, punto finale."""
    i = (i or "").strip()
    return not i or i.endswith(".") or bool(STORTI.search(i))


GIUDICE_ICEBREAKER = """Ti do frasi di apertura di mail commerciali B2B in italiano. Ogni frase viene montata cosi':
"Insieme al mio collega abbiamo dato un'occhiata a {azienda}, {icebreaker}, vi faccio i miei complimenti."
Segna KO ogni caso in cui la frase montata suonerebbe sbagliata o imbarazzante a chi la riceve:
- l'icebreaker non e' un complimento sincero (sito non disponibile, in costruzione, poche informazioni, difetti, offerte a tempo, ironia involontaria);
- da' del tu invece del voi;
- contiene link, variabili, inglese, numeri in formato inglese, errori di grammatica ("un stand", "nel scoprire");
- parla d'altro: una persona invece dell'azienda, celebrita', banner dei cookie, politica, luoghi che non c'entrano;
- non si lega alla frase (non inizia con un gerundio, finisce col punto).
Tutto il resto e' OK, anche se un po' generico. Severo ma non pedante. Solo i KO."""
SCHEMA_KO = {"type": "object", "additionalProperties": False, "required": ["ko"],
             "properties": {"ko": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                              "required": ["n", "motivo"],
                                                              "properties": {"n": {"type": "integer"}, "motivo": {"type": "string"}}}}}}


def icebreaker_ko(coppie, a_blocchi=60):
    """Il giudice su [(azienda, icebreaker)]: restituisce {indice: motivo} dei KO. Senza chiave solleva."""
    import cervello, lettore
    chiave = lettore._env("ANTHROPIC_API_KEY")
    if not chiave:
        raise RuntimeError("manca la chiave Anthropic: il giudice degli icebreaker non puo' girare")
    ko = {}
    for b in range(0, len(coppie), a_blocchi):
        righe = "\n".join(f"{b + k} | {a} | {i}" for k, (a, i) in enumerate(coppie[b:b + a_blocchi]))
        corpo = {"model": cervello.MODELLO_CLAUDE, "max_tokens": 4000, "system": GIUDICE_ICEBREAKER,
                 "messages": [{"role": "user", "content": righe}],
                 "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA_KO}}}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(corpo).encode("utf-8"), method="POST",
                                     headers={"x-api-key": chiave, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        for t in range(3):
            try:
                d = json.loads(urllib.request.urlopen(req, timeout=180).read())
                break
            except OSError:
                if t == 2:
                    raise
                time.sleep(3 * (t + 1))
        if d.get("stop_reason") != "end_turn":
            raise RuntimeError(f"giudice icebreaker incompleto ({d.get('stop_reason')})")
        testo = "".join(x.get("text", "") for x in d.get("content") or [] if x.get("type") == "text")
        for k in json.loads(testo)["ko"]:
            ko[int(k["n"])] = k["motivo"]
    return ko


def pulisci(righe, sl_mail, sl_domini, db_mail, db_domini):
    buoni, scarti, visti = [], collections.Counter(), set()
    for r in righe:
        e = (r.get("email") or "").strip().lower()
        d = stanza.dominio_vero(e)
        if not stanza.mail_personale(e, r.get("role"), r.get("first_name"), r.get("last_name"), r.get("company_clean_final") or r.get("company_name")):
            perche = "mail non personale"
        elif r.get("result") and r["result"].strip().lower() != "ok":
            perche = "mail non verificata"
        elif e in visti:
            perche = "doppia nel file"
        elif e in sl_mail:
            perche = "gia' in Smartlead"
        elif e in db_mail:
            perche = "gia' nel database"
        elif d in db_domini:
            perche = "azienda cliente, in pipeline o che ha detto no"
        elif d in sl_domini:
            perche = "azienda gia' scritta"
        elif not (r.get("first_name") or "").strip() or not (r.get("icebreaker") or "").strip():
            perche = "manca nome o icebreaker"
        elif icebreaker_storto(r.get("icebreaker")):
            perche = "icebreaker storto"
        else:
            visti.add(e)
            buoni.append(r)
            continue
        scarti[perche] += 1
    return buoni, scarti


def come_lead(r):
    azienda = (r.get("company_clean_final") or r.get("company_name") or "").strip()
    return {"first_name": r["first_name"].strip(), "last_name": (r.get("last_name") or "").strip(),
            "email": r["email"].strip().lower(), "company_name": azienda, "website": (r.get("website") or "").strip(),
            "custom_fields": {"azienda": azienda, "icebreaker": r["icebreaker"].strip()}}


def carica(file, cid, vero):
    righe = list(csv.DictReader(open(file, encoding="utf-8-sig")))
    sl_mail, sl_domini = gia_in_smartlead()
    db_mail, db_domini = bloccati_dal_database()
    buoni, scarti = pulisci(righe, sl_mail, sl_domini, db_mail, db_domini)
    ko = icebreaker_ko([((r.get("company_clean_final") or r.get("company_name") or "").strip(), r["icebreaker"].strip()) for r in buoni])
    scarti["icebreaker bocciato dal giudice"] += len(ko)
    buoni = [r for k, r in enumerate(buoni) if k not in ko]
    print(f"righe {len(righe)}, da caricare {len(buoni)}")
    for k, v in scarti.most_common():
        print(f"  scartate: {k} {v}")
    if not vero:
        print("prova a secco: niente caricato (aggiungi --vero)")
        return
    tot = collections.Counter()
    for i in range(0, len(buoni), 100):
        res = sl_post(f"/campaigns/{cid}/leads", {"lead_list": [come_lead(r) for r in buoni[i:i + 100]],
                      "settings": {"ignore_global_block_list": False, "ignore_unsubscribe_list": False,
                                   "ignore_duplicate_leads_in_other_campaign": False}})
        tot.update({k: v for k, v in (res or {}).items() if isinstance(v, int) and not isinstance(v, bool)})
    print("caricati:", dict(tot))


def pausa_generiche(vero):
    da_fermare = []
    for c in campagne():
        if c["status"] not in ATTIVE:
            continue
        for x in lead_di(c["id"]):
            if (x["status"] == "STARTED" and not x.get("lead_category_id")
                    and not stanza.mail_personale(x["lead"].get("email"))):
                da_fermare.append((c["id"], x["lead"]["id"]))
    print(f"generiche mai contattate nelle campagne attive: {len(da_fermare)}")
    if not vero:
        print("prova a secco: niente in pausa (aggiungi --vero)")
        return
    ok = err = 0
    for cid, lid in da_fermare:
        try:
            sl_post(f"/campaigns/{cid}/leads/{lid}/pause", {})
            ok += 1
        except RuntimeError:
            err += 1
        time.sleep(0.25)
    print(f"in pausa {ok}, errori {err}")
    if err:
        stanza.guasto("carica_lead", f"pausa generiche: {err} errori su {len(da_fermare)}")


def controlla_ads(cids, vero):
    """SOLO CHI NON FA ADS O LI FA MALE (Dre, 20/10 e 23/10: «investono si', ma che fanno male: uno con
    15 campagne su Google e 5 su Meta non puo' fare meglio»). Per i lead non ancora contattati delle
    campagne indicate misura Google (Transparency Center) e Meta (Ad Library) con le stesse soglie
    del fit (googlefit.giudizio_ads / giudizio_meta_ads) e mette in pausa chi li fa sul serio.
    Chi li fa poco resta: e' il target. Chi non si riesce a misurare resta, e si conta."""
    import pull, googlefit
    esiti, da_fermare = collections.Counter(), []
    for cid in cids:
        for x in lead_di(cid):
            if x["status"] != "STARTED" or x.get("lead_category_id"):
                continue
            l = x["lead"]
            dom = stanza.dominio_vero(l.get("email")) or ""
            sito = (l.get("website") or "").lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
            dom = sito or dom
            azienda = ((l.get("custom_fields") or {}).get("azienda") or l.get("company_name") or "").strip()
            try:
                g, _ = googlefit.giudizio_ads(pull.fa_ads(dom) if dom else None)
            except Exception:                                 # noqa: BLE001
                g = None
            try:
                m, _ = googlefit.giudizio_meta_ads(googlefit.fa_meta_ads(azienda, dom))
            except Exception:                                 # noqa: BLE001
                m = None
            if "serio" in (g, m):
                esiti["fa Ads sul serio: in pausa"] += 1
                da_fermare.append((cid, l["id"]))
            elif "poco" in (g, m):
                esiti["fa Ads poco: resta (target)"] += 1
            elif g == "no" and m in ("no", None):
                esiti["non fa Ads: resta"] += 1
            else:
                esiti["non misurato: resta"] += 1
    for k, v in esiti.most_common():
        print(f"  {k}: {v}")
    if not vero:
        print("prova a secco: niente in pausa (aggiungi --vero)")
        return
    ok = err = 0
    for cid, lid in da_fermare:
        try:
            sl_post(f"/campaigns/{cid}/leads/{lid}/pause", {})
            ok += 1
        except RuntimeError:
            err += 1
        time.sleep(0.25)
    print(f"in pausa {ok}, errori {err}")
    if err:
        stanza.guasto("carica_lead", f"pausa di chi fa Ads: {err} errori su {len(da_fermare)}")


def controlla_icebreaker(cid, vero):
    """Chi non ha ancora ricevuto la prima mail (STARTED) e ha un icebreaker storto: in pausa (reversibile)."""
    da_vedere = []
    for x in lead_di(cid):
        if x.get("status") != "STARTED":
            continue
        l = x.get("lead") or {}
        cf = l.get("custom_fields") or {}
        da_vedere.append((l.get("id"), (cf.get("azienda") or "").strip(), (cf.get("icebreaker") or "").strip()))
    fissi = {k for k, (_, _, i) in enumerate(da_vedere) if icebreaker_storto(i)}
    giudice = icebreaker_ko([(a, i) for _, a, i in da_vedere])
    da_fermare = [da_vedere[k][0] for k in sorted(fissi | set(giudice))]
    print(f"da mandare {len(da_vedere)}, storti {len(da_fermare)} (regole {len(fissi)}, giudice {len(giudice)})")
    for m, n in collections.Counter(giudice.values()).most_common(10):
        print(f"  {n} {m}")
    if not vero:
        print("prova a secco: nessuna pausa (aggiungi --vero)")
        return
    ok = err = 0
    for lid in da_fermare:
        try:
            sl_post(f"/campaigns/{cid}/leads/{lid}/pause", {})
            ok += 1
        except RuntimeError:
            err += 1
        time.sleep(0.25)
    print(f"in pausa {ok}, errori {err}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("file", nargs="?")
    a.add_argument("--campagna", type=int)
    a.add_argument("--vero", action="store_true")
    a.add_argument("--pausa-generiche", action="store_true")
    a.add_argument("--controlla-ads", type=int, nargs="+", metavar="CAMPAGNA")
    a.add_argument("--controlla-icebreaker", type=int, metavar="CAMPAGNA")
    o = a.parse_args()
    if o.controlla_icebreaker:
        controlla_icebreaker(o.controlla_icebreaker, o.vero)
    elif o.controlla_ads:
        controlla_ads(o.controlla_ads, o.vero)
    elif o.pausa_generiche:
        pausa_generiche(o.vero)
    elif o.file and o.campagna:
        carica(o.file, o.campagna, o.vero)
    else:
        a.error("serve un file e --campagna, oppure --pausa-generiche")
