#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA FIRMA DI DEFAULT SU SMARTLEAD (Dre, 23/9/2026).

«Una firma di default più clean, così scrivo i messaggi e basta.» Una firma
sola, con il logo ufficiale (Marketing, AI & Software), su tutte le caselle di
Lorenzo; e via le tre righe scritte a mano dentro i testi delle campagne,
che uscivano come seconda firma.

  firma_smartlead.py --prova      dice cosa farebbe
  firma_smartlead.py              imposta la firma sulle caselle e pulisce le sequenze
"""
import json, os, re, sys, time, urllib.request, urllib.error

BASE = "https://server.smartlead.ai/api/v1"
FIRMA = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "firma_smartlead.html"), encoding="utf-8").read().strip()
CAMPAGNE = (4003942, 4003943, 4003944, 4003946, 4003947, 4003948)
# quello che oggi sta scritto a mano in fondo ai 18 testi
INLINE = re.compile(r"(<br>)*\s*<span style=\"font-size: 18px; font-weight: 400\">Lorenzo Fornasier</span><br><strong style=\"font-weight: 700\">Studio Galilei</strong><br><strong style=\"font-weight: 700\"><em><u>studiogalilei\.com</u></em></strong>\s*$")
PROVA = "--prova" in sys.argv


def chiave():
    for r in open(os.path.expanduser("~/.hermes/config.yaml"), encoding="utf-8"):
        m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", r)
        if m:
            return m.group(1).strip("\"'")
    sys.exit("manca SMARTLEAD_API_KEY")


K = chiave()


def api(m, p, corpo=None):
    req = urllib.request.Request(f"{BASE}{p}{'&' if '?' in p else '?'}api_key={K}", method=m,
                                 data=json.dumps(corpo).encode() if corpo is not None else None,
                                 headers={"User-Agent": "clara/1.0", "Content-Type": "application/json"})
    for t in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                try:
                    return json.loads(raw or b"null")
                except Exception:
                    return raw.decode(errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (401, 429, 500, 502, 503) and t < 4:
                time.sleep(4 * (t + 1)); continue
            raise RuntimeError(f"{e.code} {m} {p}: {e.read()[:150]}")


def main():
    # il logo deve essere online, se no la firma esce rotta
    url = re.search(r'src="([^"]+)"', FIRMA).group(1)
    try:
        urllib.request.urlopen(url, timeout=30).read()
    except Exception:
        sys.exit(f"il logo non e' ancora online ({url}): serve il push del repo prima")
    acc = []
    for off in (0, 100):
        acc += api("GET", f"/email-accounts/?offset={off}&limit=100") or []
    lor = [a for a in acc if "lorenzo" in (a.get("from_name") or "").lower()]
    print(f"caselle di Lorenzo: {len(lor)}")
    n = 0
    for a in lor:
        if PROVA:
            continue
        api("POST", f"/email-accounts/{a['id']}", {"signature": FIRMA}); n += 1; time.sleep(0.3)
    print(f"  firma impostata su {n} caselle" if not PROVA else "  [prova] firma non toccata")
    for cid in CAMPAGNE:
        seq = api("GET", f"/campaigns/{cid}/sequences")
        nuove, toccate = [], 0
        for s in seq:
            b, k = INLINE.subn("", s["email_body"])
            toccate += bool(k)
            nuove.append({"id": s["id"], "seq_number": s["seq_number"], "seq_delay_details": {"delay_in_days": s["seq_delay_details"]["delay_in_days"]},
                          "subject": s["subject"], "email_body": b.rstrip("<br>").rstrip()})
        if PROVA:
            print(f"  [prova] {cid}: {toccate}/{len(seq)} testi da pulire"); continue
        api("POST", f"/campaigns/{cid}/sequences", {"sequences": nuove}); time.sleep(1)
        dopo = api("GET", f"/campaigns/{cid}/sequences")
        ok = len(dopo) == 3 and not any(INLINE.search(d["email_body"]) for d in dopo)
        print(f"  {cid}: {toccate} testi puliti, {'ok' if ok else 'PROBLEMA'}")


if __name__ == "__main__":
    main()
