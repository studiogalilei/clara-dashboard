"""CARICA UNA LISTA DI LEAD IN UNA CAMPAGNA SMARTLEAD, PULITA (Dre, 22/10).

  python3 scripts/carica_lead.py lista.csv --campagna 4003942          # prova a secco: solo conteggi
  python3 scripts/carica_lead.py lista.csv --campagna 4003942 --vero   # carica
  python3 scripts/carica_lead.py --pausa-generiche [--vero]            # mette in pausa le generiche mai contattate

Le regole, tutte prima di caricare:
- solo mail personali (stanza.mail_personale) e verificate (colonna result = ok, se c'e');
- niente doppioni: ne' nel file, ne' gia' in una campagna Smartlead, ne' nel database;
- niente aziende gia' scritte (un'altra persona della stessa azienda e' gia' in Smartlead);
- niente aziende cliente, in pipeline, perse o che hanno detto no;
- serve il nome e l'icebreaker (la prima mail li usa).
Il CSV e' quello di Lorenzo: first_name, last_name, email, website, company_clean_final (o company_name),
icebreaker, role, result. Stampa solo numeri: mai mail o nomi (il repo e' pubblico, i log pure).
La pausa usa il comando pausa di Smartlead (reversibile), mai DELETE; tocca solo chi non ha ricevuto
nessuna mail e non ha risposto.
"""
import argparse, collections, csv, os, sys, time

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


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("file", nargs="?")
    a.add_argument("--campagna", type=int)
    a.add_argument("--vero", action="store_true")
    a.add_argument("--pausa-generiche", action="store_true")
    o = a.parse_args()
    if o.pausa_generiche:
        pausa_generiche(o.vero)
    elif o.file and o.campagna:
        carica(o.file, o.campagna, o.vero)
    else:
        a.error("serve un file e --campagna, oppure --pausa-generiche")
