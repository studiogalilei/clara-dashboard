"""I modelli rigenerati col brand entrano nei Documenti (sezione modelli, gruppo
modelli) e i vecchi esempi (capsule v1, regole superate) escono.
   python3 scripts/carica_modelli.py <cartella con i PDF> [--tieni-esempi]"""
import mimetypes, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # i moduli comuni stanno in scripts/
from stanza import env, sb

SB = env("VITE_SUPABASE_URL"); SK = env("SUPABASE_SERVICE_KEY")
NOMI = {
    "sg-condizioni-modello.pdf": ("Condizioni economiche (modello)", "il documento formale: lo genera il widget Preventivi con i dati veri"),
    "sg-guida-pagamenti.pdf": ("Guida ai pagamenti", "da mandare al cliente prima della call di avviamento"),
    "sg-casi-studio.pdf": ("Casi studio", "tre lavori raccontati per intero, con i numeri"),
    "sg-presentazione.pdf": ("Presentazione dello Studio", "il documento istituzionale: chi siamo, come si lavora"),
    "sg-studio-di-mercato-agriverse.pdf": ("Studio di mercato (esempio Agriverse)", "un esempio vero di studio di mercato, a sette mosse"),
    "sg-report-mensile.pdf": ("Report mensile (modello)", "quello che ogni specialist manda al cliente entro il 5 del mese"),
    "sg-verbale-call.pdf": ("Verbale di call (modello)", "cosa si e' deciso, chi fa cosa entro quando"),
    "sg-proposta-tecnica.pdf": ("Proposta tecnica (modello)", "per i lavori software: cosa costruiamo, in che ordine, cosa serve da voi"),
}

def metti(locale, remoto):
    data = open(locale, "rb").read()
    req = urllib.request.Request(f"{SB}/storage/v1/object/vault/{remoto}", data=data, method="POST",
                                 headers={"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/pdf", "x-upsert": "true"})
    with urllib.request.urlopen(req, timeout=600) as r: r.read()
    return len(data)

def togli(remoto):
    req = urllib.request.Request(f"{SB}/storage/v1/object/vault/{remoto}", method="DELETE", headers={"apikey": SK, "Authorization": f"Bearer {SK}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: r.read()
    except urllib.error.HTTPError as e:
        print("  (storage)", remoto, e.code)

def main():
    cartella = sys.argv[1]
    esistenti = {r["path"]: r for r in (sb("GET", "/rest/v1/vault_file?select=id,path,gruppo&sezione=eq.modelli&limit=500") or [])}
    for f in sorted(os.listdir(cartella)):
        if not f.endswith(".pdf"): continue
        nome, nota = NOMI.get(f, (f[:-4].replace("sg-", "").replace("-", " ").capitalize(), None))
        remoto = f"modelli/modelli/{f}"
        dim = metti(os.path.join(cartella, f), remoto)
        if remoto in esistenti:
            sb("PATCH", f"/rest/v1/vault_file?id=eq.{esistenti[remoto]['id']}", {"dimensione": dim, "nome": nome, "nota": nota})
        else:
            sb("POST", "/rest/v1/vault_file", {"nome": nome, "path": remoto, "mime": "application/pdf", "dimensione": dim, "sezione": "modelli", "gruppo": "modelli", "nota": nota})
        print(f"  {nome[:44]:44} {dim // 1024:6} KB")
    if "--tieni-esempi" not in sys.argv:
        vecchi = [r for r in esistenti.values() if r["gruppo"] == "esempi"]
        for r in vecchi:
            sb("DELETE", f"/rest/v1/vault_file?id=eq.{r['id']}")
            togli(r["path"])
        print(f"  tolti {len(vecchi)} esempi vecchi (regole superate)")

if __name__ == "__main__":
    main()
