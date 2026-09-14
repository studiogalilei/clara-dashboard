"""Carica la Clara Capsule nei Documenti (sezione brand e modelli), una volta.
   python3 scripts/carica_brand.py <cartella capsule v3> <cartella capsule v1>"""
import mimetypes, os, re, sys, urllib.request, json
sys.path.insert(0, os.path.dirname(__file__))
from stanza import env, sb

SB = env("VITE_SUPABASE_URL"); SK = env("SUPABASE_SERVICE_KEY")

def metti(path_locale, path_remoto):
    mime = mimetypes.guess_type(path_locale)[0] or "application/octet-stream"
    if path_locale.endswith(".md"): mime = "text/markdown"
    if path_locale.endswith(".svg"): mime = "image/svg+xml"
    data = open(path_locale, "rb").read()
    req = urllib.request.Request(f"{SB}/storage/v1/object/vault/{path_remoto}", data=data, method="POST",
                                 headers={"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": mime, "x-upsert": "true"})
    with urllib.request.urlopen(req, timeout=600) as r: r.read()
    return mime, len(data)

COLORI = {"blu": "blu", "bianco": "bianco", "nero": "nero", "rosso": "rosso", "verde": "verde", "azzurro": "azzurro"}
def nome_logo(f):
    b = re.sub(r"\.(svg|png)$", "", f)
    if b == "SG_master_originale": return "Marchio, master originale"
    if b == "google_partner": return "Google Partner"
    if b == "stripe": return "Stripe"
    p = b.replace("SG_", "").split("_")
    tipo = {"logo": "Logo", "simbolo": "Simbolo"}.get(p[0], p[0].capitalize())
    resto = p[1:]
    reparto = ""
    if resto and resto[0] in ("ai", "marketing", "software"):
        reparto = {"ai": "AI", "marketing": "Marketing", "software": "Software"}[resto[0]]; resto = resto[1:]
    payoff = False
    if resto and resto[0] == "payoff": payoff = True; resto = resto[1:]
    colore = " ".join(resto).replace("_", " ")
    return f"{tipo}{' ' + reparto if reparto else ''}{' con payoff' if payoff else ''}, {colore}"

def nome_bello(gruppo, f):
    b = re.sub(r"\.[a-z0-9]+$", "", f).replace("sg-", "").replace("-", " ")
    if gruppo == "loghi": return nome_logo(f)
    if gruppo == "copertine": return "Copertina " + b.replace("copertina ", "")
    if gruppo == "sfondi": return "Sfondo " + b.replace("sfondo ", "")
    if gruppo == "segni": return "Segno: " + b.replace("segno ", "") if "segno" in b else "Esempio di pagina interna"
    if gruppo == "incisioni": return "Incisione: " + b.replace("incisione ", "")
    return b[0].upper() + b[1:]

def main():
    v3, v1 = sys.argv[1], sys.argv[2]
    esistenti = {r["path"] for r in (sb("GET", "/rest/v1/vault_file?select=path&limit=2000") or [])}
    piano = []   # (locale, remoto, sezione, gruppo, nome, nota)
    for gruppo in ("loghi", "copertine", "sfondi", "segni", "incisioni"):
        for f in sorted(os.listdir(os.path.join(v3, gruppo))):
            if f.startswith("."): continue
            piano.append((os.path.join(v3, gruppo, f), f"brand/{gruppo}/{f}", "brand", gruppo, nome_bello(gruppo, f), None))
    for f, nome, nota in (("sg-intreccio.svg", "Intreccio SG (vettoriale)", "l'angolo delle copertine, al 30%"),
                          ("sg-intreccio.png", "Intreccio SG (PNG)", None),
                          ("sg-pattern.png", "Pattern aziendale", "si tila al 7% sui fondi"),
                          ("clara-logo.svg", "Logo di Clara", None)):
        piano.append((os.path.join(v3, f), f"brand/marchio/{f}", "brand", "marchio", nome, nota))
    piano.append((os.path.join(v3, "loghi", "SG_master_originale.svg"), "brand/marchio/SG_master_originale.svg", "brand", "marchio", "Marchio, master originale", "da qui nasce tutto: non si ridisegna"))
    for f, nome, nota in (("sg-regole-documenti.md", "Regole dei documenti", "colori, copertine, tono, nomi: tutto"),
                          ("sg-brand-guidelines.html", "Brand guidelines", "il sistema visivo completo"),
                          ("clara-sg-system-prompt.md", "Clara SG, istruzioni per il progetto", "da incollare nelle istruzioni del progetto"),
                          ("clara-capsule-onboarding.md", "Clara Capsule, come si installa", None),
                          ("LEGGIMI.md", "Capsule, la mappa", None)):
        piano.append((os.path.join(v3, f), f"brand/regole/{f}", "brand", "regole", nome, nota))
    piano.append((os.path.join(v1, "tono", "sg-brand-tone.md"), "brand/regole/sg-brand-tone.md", "brand", "regole", "Brand tone, come parla lo Studio", None))
    piano.append((os.path.join(v1, "tono", "check_tono.py"), "brand/regole/check_tono.py", "brand", "regole", "Controllo del tono (script)", "python3 check_tono.py documento.pdf"))
    piano.append(("/Users/dramane/Downloads/clara-capsule (3).zip", "brand/regole/clara-capsule.zip", "brand", "regole", "Clara Capsule (zip completo)", "il kit per lavorare come Clara su Claude o ChatGPT"))
    for f in sorted(os.listdir(os.path.join(v1, "documenti"))):
        if f.endswith(".pdf"):
            piano.append((os.path.join(v1, "documenti", f), f"modelli/esempi/{f}", "modelli", "esempi", nome_bello("esempi", f), "documento pubblicato, da usare come riferimento"))

    fatti = saltati = 0
    for locale, remoto, sezione, gruppo, nome, nota in piano:
        if remoto in esistenti or not os.path.exists(locale):
            saltati += 1; continue
        mime, dim = metti(locale, remoto)
        sb("POST", "/rest/v1/vault_file", {"nome": nome, "path": remoto, "mime": mime, "dimensione": dim, "sezione": sezione, "gruppo": gruppo, "nota": nota})
        fatti += 1
        print(f"  {sezione}/{gruppo:10} {nome[:44]:44} {dim//1024:6} KB")
    print(f"caricati {fatti}, saltati {saltati}")

if __name__ == "__main__":
    main()
