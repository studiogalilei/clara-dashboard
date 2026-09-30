#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA BIBLIOTECA DEI CASI (Dre, 30/9/2026, chiudendo il metro).

Parole sue: «prendi con le pinze le mie risposte, veramente ogni caso e' unico.
La cosa bella e' un'intelligenza che migliora sulla base dei casi unici».

Quindi niente caselle rigide: i commenti che Dre ha scritto nel metro (97 il
30/9) sono casi gia' giudicati, con la mail vera e la sua mossa spiegata. Quando
Clara scrive una bozza, pesca i 2-3 casi piu' simili alla mail a cui risponde e
li mette nel prompt come esempi del SUO modo. La biblioteca cresce da sola: ogni
nuovo esame nel metro aggiunge casi, senza toccare il codice.

Uso:
    import casi
    blocco = casi.simili("il testo della mail a cui rispondo")   # "" se niente
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb_tutte                                # noqa: E402

_VUOTE = {"buongiorno", "buonasera", "salve", "grazie", "cordiali", "saluti", "gentile",
          "della", "delle", "dello", "degli", "nostra", "nostro", "vostra", "vostro",
          "questa", "questo", "sono", "siamo", "abbiamo", "avete", "essere", "anche",
          "come", "che", "per", "con", "una", "del", "the", "and", "you", "for", "not"}


def _parole(t):
    return {w for w in re.findall(r"[a-zà-ù]{4,}", (t or "").lower()) if w not in _VUOTE}


_biblioteca = None


def _carica():
    global _biblioteca
    if _biblioteca is None:
        try:
            righe = sb_tutte("/rest/v1/metro_risposte?select=testo,etichetta,nota&nota=not.is.null",
                             chiave="interaction_id")
        except Exception:                                    # noqa: BLE001
            righe = []      # senza rete la biblioteca e' vuota: le bozze si scrivono lo stesso
        _biblioteca = [{**r, "parole": _parole(r["testo"])} for r in righe if (r.get("nota") or "").strip()]
    return _biblioteca


def simili(testo, quanti=3, minimo=2):
    """I casi di Dre piu' simili a questa mail, pronti per il prompt. "" se nessuno somiglia."""
    mie = _parole(testo)
    if not mie:
        return ""
    punteggi = sorted(((len(mie & c["parole"]), c) for c in _carica()), key=lambda x: -x[0])
    scelti = [c for n, c in punteggi[:quanti] if n >= minimo]
    if not scelti:
        return ""
    righe = ["\nCASI GIA' GIUDICATI DA DRE (mail simili a questa: segui il suo modo, non copiare le parole):"]
    for c in scelti:
        righe.append(f"- Mail: «{' '.join(c['testo'].split())[:220]}»\n  La mossa di Dre: {' '.join(c['nota'].split())[:400]}")
    return "\n".join(righe) + "\n"
