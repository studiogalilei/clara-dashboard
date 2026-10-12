#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA MISURA DEL SENSO (12/10/2026): il vecchio e il nuovo, sulle risposte vere.

Si accende senso_v2 solo se i numeri reggono (piano del 12/10, passo 7). Questo script li fa:
  - le risposte vere (email_in dal 12/8) e le 150 del Metro, etichettate da Dre;
  - per ognuna, il VECCHIO (il taglio di prima, le liste, «basta che uno dei due dica no»,
    le regex del sync) e il NUOVO (lettura.senso: il taglio nuovo, l'AI sul testo suo in tre
    blocchi, la lista solo per i gravi, la seconda lettura);
  - i numeri che contano: si' presi per no, «non scrivetemi» mancati, no presi per si' sicuro,
    effetti permanenti senza AI sicura, da_classificare del sync, seconde letture, dubbi a Dre,
    il costo.

Sola lettura: gira con PROVA=1 (niente scritture, nemmeno il contatore). Il vecchio e il nuovo
usano la STESSA lettura del modello: cambia solo chi decide e cosa legge, che e' la fonte del 12/10.
Il dettaglio contiene testi di lead: va fuori dal repository (--out), mai qui dentro.

  PROVA=1 python3 scripts/misura_senso.py --out /percorso/misura.json [--prima /percorso/scripts_di_prima]
"""
import importlib.util
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

os.environ["PROVA"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte                                 # noqa: E402
import cervello                                                # noqa: E402
import lettura                                                 # noqa: E402
import senso as S                                              # noqa: E402
import sync_v2                                                 # noqa: E402
from senso_ombra import vecchio_di, nuovo_di                   # noqa: E402

DAL = "2026-08-12"
# LE SOGLIE PROPOSTE PER IL MANUALE (sezione F), finche' Dre non le approva: si misurano queste.
# Le chiavi che nel Manuale ci sono gia' si leggono da li'; queste sono solo quelle che mancano.
PROPOSTA_MANUALE_F = {
    "lettore_non_contattare_per_sempre": "≥ 0,80", "lettore_dice_no_sicuro": "≥ 0,80",
    "lettore_seconda_netta": "≥ 0,80 conferma, ≤ 0,20 scarta", "lettore_illeggibile": "≥ 0,70",
    "lettore_fuori_target": "≥ 0,70", "lettore_non_e_lui": "≥ 0,70", "lettore_ha_gia_analisi": "≥ 0,70",
}
PREZZO = {"gpt-5": (1.25, 10.0), "gpt-5-mini": (0.25, 2.0)}       # $ per milione di token, da ricontrollare
TOKEN = Counter()


def _conta(modello, dentro, fuori, scopo=None):
    TOKEN[(modello, scopo or "altro", "in")] += dentro
    TOKEN[(modello, scopo or "altro", "out")] += fuori
    TOKEN[(modello, scopo or "altro", "n")] += 1


def _carica(nome, cartella):
    spec = importlib.util.spec_from_file_location(nome + "_prima", os.path.join(cartella, nome + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def anonimo(t, p):
    """Un estratto senza indirizzi, telefoni e nomi della scheda."""
    t = " ".join((t or "").split())
    t = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[email]", t)
    t = re.sub(r"\+?\d[\d .-]{7,}\d", "[tel]", t)
    for k in ("name", "company"):
        for tok in re.split(r"[^\wÀ-ÿ']+", (p or {}).get(k) or ""):
            if len(tok) >= 3:
                t = re.sub(rf"\b{re.escape(tok)}\b", "[nome]" if k == "name" else "[azienda]", t, flags=re.I)
    return t[:160]


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "misura.json")
    prima_dir = sys.argv[sys.argv.index("--prima") + 1] if "--prima" in sys.argv else None
    cervello._conta_uso = _conta
    regole = {r["chiave"]: r["valore"] for r in sb("GET", "/rest/v1/regole?select=chiave,valore&limit=500") or []}
    soglie = S.soglie({**PROPOSTA_MANUALE_F, **regole})
    assert soglie, "le soglie non si leggono"
    lettura._STATO.update({"soglie": soglie, "tabella": False, "acceso": False})
    vecchia_lettura = _carica("lettura", prima_dir) if prima_dir else lettura
    vecchio_sync = _carica("sync_v2", prima_dir) if prima_dir else sync_v2
    while prima_dir and os.path.abspath(prima_dir) in sys.path:
        sys.path.remove(os.path.abspath(prima_dir))      # i moduli di prima non devono prendere il posto di quelli di oggi

    def vecchio_testo_sync(body):
        """Il taglio del sync di prima: lettura.solo_suo di prima, con la firma dentro."""
        t = vecchio_sync.strip_html(body)
        return vecchia_lettura.solo_suo(t, con_firma=True).strip()

    mails = sb_tutte(f"/rest/v1/interactions?select=id,prospect_id,at,body,ref&kind=eq.email_in&at=gte.{DAL}")
    metro = [m for m in sb_tutte("/rest/v1/metro_risposte?select=interaction_id,etichetta,testo", chiave="interaction_id") if m.get("etichetta")]
    gia = {m["id"] for m in mails}
    extra_ids = [m["interaction_id"] for m in metro if m["interaction_id"] not in gia]
    for i in range(0, len(extra_ids), 80):
        mails += sb("GET", f"/rest/v1/interactions?select=id,prospect_id,at,body,ref&id=in.({','.join(extra_ids[i:i + 80])})") or []
    etichetta = {m["interaction_id"]: m["etichetta"] for m in metro}
    pids = sorted({m["prospect_id"] for m in mails if m.get("prospect_id")})
    schede, nostre = {}, {}
    for i in range(0, len(pids), 80):
        blocco = ",".join(pids[i:i + 80])
        for p in sb("GET", f"/rest/v1/prospects?select=id,email,email_alt,name,company,classificazione,analysis_sent&id=in.({blocco})") or []:
            schede[p["id"]] = p
        for r in sb_tutte(f"/rest/v1/interactions?select=id,prospect_id,at,body,kind&kind=in.(email_out,followup,analisi)&prospect_id=in.({blocco})"):
            nostre.setdefault(r["prospect_id"], []).append(r)
    if "--quanti" in sys.argv:
        mails = mails[:int(sys.argv[sys.argv.index("--quanti") + 1])]
    print(f"misura: {len(mails)} risposte ({len(gia)} dal {DAL}, {len(extra_ids)} solo dal Metro), {len(metro)} etichettate da Dre")

    def uno(m):
        p = schede.get(m["prospect_id"]) or {"id": m["prospect_id"]}
        body = lettura.corpo_e_oggetto(m)[0]
        prima = [x for x in nostre.get(m["prospect_id"], []) if (x.get("at") or "") <= (m.get("at") or "")]
        prima.sort(key=lambda x: x.get("at") or "")
        nostra = (prima[-1].get("body") or "") if prima else ""
        vecchio_suo = vecchia_lettura.solo_suo(m.get("body") or "")       # il vecchio leggeva il corpo con l'oggetto in testa
        riga = lettura.senso(p, m, nostra=nostra, attuale=None, chiedi=False)        # la porta sola, come in produzione
        dec = riga.get("decisione") or {}
        r = riga.get("risposte")
        nuovo_suo = riga.get("testo_suo") or ""
        v_sync = vecchio_sync.classifica(vecchio_testo_sync(m.get("body") or "")) if not vecchia_lettura._segnaposto(m.get("body")) else None
        return {
            "id": m["id"], "dal_metro": m["id"] not in gia, "etichetta_dre": etichetta.get(m["id"]),
            "segnaposto_prima": bool(vecchia_lettura._segnaposto(m.get("body"))), "segnaposto_ora": bool(lettura._segnaposto(body)),
            "vecchio": vecchio_di(vecchio_suo, r) if not vecchia_lettura._segnaposto(m.get("body")) else "segnaposto",
            "nuovo": nuovo_di(dec), "etichetta": dec.get("etichetta"), "sicuro": dec.get("sicuro"), "dubbio": dec.get("dubbio"),
            "grave": dec.get("grave"), "stato": dec.get("stato"), "fonte": dec.get("fonte"), "permanente_ok": S.permanente_ok(dec),
            "rete": dec.get("rete"), "seconda": riga.get("seconda"), "frase": anonimo(dec.get("frase"), p),
            "va_a_dre": S.va_a_dre(dec, p.get("classificazione")), "classe_oggi": p.get("classificazione"),
            "sync_vecchio": v_sync, "sync_nuovo": S.classe(dec, None),
            "gia_letta_vecchio": bool(lettura.GIA_LETTA.search(m.get("body") or "")),
            "gia_letta_nuovo": bool(r and r.get("ha_gia_analisi", 0) >= soglie["lettore_ha_gia_analisi"][0]),
            "girato_nuovo": len(dec.get("girato_a") or []),
            "girato_regex": len([e for e in lettura.EMAIL.findall(vecchio_suo) if e.lower() != (p.get("email") or "").lower()
                                 and not any(n in e.lower() for n in lettura.NOSTRI)]),
            "citata_prima": bool(re.search(r"analisi gratuita|mi piacerebbe condivider|gliela mando|ha scritto:|wrote:", vecchio_suo, re.I)),
            "citata_ora": bool(re.search(r"analisi gratuita|mi piacerebbe condivider|gliela mando|ha scritto:|wrote:", nuovo_suo, re.I)),
            "oggetto_prima": bool(re.match(r"\s*(?:re|r|i|fw|fwd)\s*:", vecchio_suo, re.I)),
            "oggetto_ora": bool(re.match(r"\s*(?:re|r|i|fw|fwd)\s*:", nuovo_suo, re.I)),
            "estratto": anonimo(nuovo_suo, p), "estratto_prima": anonimo(vecchio_suo, p),
            "p": {k: round(v, 2) for k, v in (r or {}).items() if isinstance(v, float)},
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        esiti = list(pool.map(uno, mails))
    json.dump(esiti, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    racconta(esiti)
    costo = 0.0
    for (mod, scopo, k), v in sorted(TOKEN.items()):
        if k == "n":
            pin, pout = PREZZO.get(mod, (1.25, 10.0))
            c = TOKEN[(mod, scopo, "in")] / 1e6 * pin + TOKEN[(mod, scopo, "out")] / 1e6 * pout
            costo += c
            print(f"  costo {mod} {scopo}: {v} chiamate, {TOKEN[(mod, scopo, 'in')]} in, {TOKEN[(mod, scopo, 'out')]} out, {c:.2f} $")
    print(f"  costo totale di questa misura: {costo:.2f} $ (le letture gia' in cache non si ripagano)")
    print(f"dettaglio: {out}")


def racconta(e):
    vere = [x for x in e if not x["dal_metro"]]
    dre = [x for x in e if x["etichetta_dre"]]
    tot = Counter(x["etichetta_dre"] for x in dre)
    print(f"\nSUL METRO ({len(dre)} etichettate da Dre: {dict(tot)})")
    for chi in ("vecchio", "nuovo"):
        si_no = sum(1 for x in dre if x["etichetta_dre"] == "si" and x[chi] in ("no", "non_scrivere"))
        ns = sum(1 for x in dre if x["etichetta_dre"] == "non_scrivere" and x[chi] != "non_scrivere")
        no_si = sum(1 for x in dre if x["etichetta_dre"] in ("no", "non_scrivere") and x[chi] == "si"
                    and (chi == "vecchio" or (x["sicuro"] and not x["dubbio"])))
        auto = sum(1 for x in dre if x["etichetta_dre"] == "fuori_ufficio" and x[chi] != "fuori_ufficio")
        giuste = sum(1 for x in dre if x["etichetta_dre"] == x[chi])
        print(f"  {chi:8} giuste {giuste}/{len(dre)} | si' presi per no {si_no}/{tot['si']} | «non scrivetemi» mancati {ns}/{tot['non_scrivere']}"
              f" | no presi per si'{' sicuro' if chi == 'nuovo' else ''} {no_si}/{tot['no'] + tot['non_scrivere']} | autorisposte mancate {auto}/{tot['fuori_ufficio']}")
    print(f"\nSULLE RISPOSTE VERE dal {DAL} ({len(vere)})")
    print(f"  segnaposto: prima {sum(x['segnaposto_prima'] for x in vere)}, ora {sum(x['segnaposto_ora'] for x in vere)}")
    print(f"  testo suo con la nostra mail citata dentro: prima {sum(x['citata_prima'] for x in vere)}, ora {sum(x['citata_ora'] for x in vere)}")
    print(f"  testo suo che comincia con l'oggetto: prima {sum(x['oggetto_prima'] for x in vere)}, ora {sum(x['oggetto_ora'] for x in vere)}")
    print(f"  decisioni: vecchio {dict(Counter(x['vecchio'] for x in vere))}")
    print(f"             nuovo  {dict(Counter(x['nuovo'] for x in vere))}")
    print(f"  stati del nuovo: {dict(Counter(x['stato'] for x in vere))} | fonti: {dict(Counter(x['fonte'] for x in vere))}")
    print(f"  seconde letture: {sum(1 for x in vere if x['seconda'])} ({sum(1 for x in vere if x['seconda'])/max(len(vere),1):.0%})"
          f" | dubbi a Dre (casi a e b): {sum(x['va_a_dre'] for x in vere)} | rete grave trovata: {sum(1 for x in vere if x['rete'])}")
    sv, sn = Counter(x["sync_vecchio"] for x in vere), Counter(x["sync_nuovo"] for x in vere)
    print(f"  sync, classe vecchia: {dict(sv)}")
    print(f"  sync, classe nuova:   {dict(sn)}")
    print(f"  sync da_classificare: prima {sv['da_classificare']}/{len(vere)} ({sv['da_classificare']/max(len(vere),1):.0%}), "
          f"ora {sn['da_classificare']}/{len(vere)} ({sn['da_classificare']/max(len(vere),1):.0%})")
    perm_v = sum(1 for x in vere if x["sync_vecchio"] not in (None, "da_classificare"))
    perm_n = sum(1 for x in vere if x["sync_nuovo"] in ("negativo", "soppresso", "nervoso") and not x["permanente_ok"])
    print(f"  classi fuori dai positivi senza AI sicura: prima {sum(1 for x in vere if x['sync_vecchio'] in ('negativo',))} "
          f"(il sync scriveva {perm_v} classi con le sole regex), ora {perm_n}")
    print(f"  «ha gia' letto l'analisi»: regex {sum(x['gia_letta_vecchio'] for x in vere)}, AI {sum(x['gia_letta_nuovo'] for x in vere)}")
    print(f"  «ci gira a»: indirizzi nel testo suo (regex, prima del filtro firma) {sum(1 for x in vere if x['girato_regex'])}, AI verificato {sum(1 for x in vere if x['girato_nuovo'])}")
    cambia = [x for x in e if x["vecchio"] != x["nuovo"] and x["vecchio"] != "segnaposto"]
    print(f"\nDECISIONI CHE CAMBIANO: {len(cambia)} su {len(e)}")
    for x in sorted(cambia, key=lambda x: (x["vecchio"], x["nuovo"])):
        dre_ = f" Dre: {x['etichetta_dre']}" if x["etichetta_dre"] else ""
        print(f"  [{x['vecchio']:>13} → {x['nuovo']:<13}] {x['fonte']}/{x['stato']}{dre_} rete={x['rete'] or '-'} «{x['estratto'][:110]}»")


if __name__ == "__main__":
    main()
