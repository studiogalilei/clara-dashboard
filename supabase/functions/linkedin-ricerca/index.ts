// LE NOTE PER CHI HA RISPOSTO: le ricerche pubbliche su un'azienda (27/11/2026).
//
// La routine «LinkedIn Desk: note per chi ha risposto» prepara il «Gestionale Operativo AI per <azienda>» partendo da
// fatti pubblici. Qui passa da SearchAPI (la chiave resta nei segreti di Supabase, la routine chiama con la chiave di
// servizio): la scheda su Google Maps, le recensioni piu' critiche e una ricerca Google normale.
//   {tipo: "maps", q}                     -> le schede trovate (nome, voto, numero recensioni, indirizzo, sito, data_id)
//   {tipo: "recensioni", data_id, pagine} -> le recensioni dalla piu' bassa, al massimo 3 pagine
//   {tipo: "google", q}                   -> i primi risultati (titolo, link, frase)
// IN CLOUD: supabase functions deploy linkedin-ricerca   (segreto: SEARCHAPI_KEY)
const CHIAVE = Deno.env.get("SEARCHAPI_KEY") ?? "";

async function chiedi(parametri: Record<string, string>) {
  const qs = new URLSearchParams({ ...parametri, hl: "it", gl: "it", api_key: CHIAVE });
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 40000);
  try {
    const r = await fetch(`https://www.searchapi.io/api/v1/search?${qs}`, { signal: ctl.signal });
    return await r.json();
  } finally {
    clearTimeout(t);
  }
}

Deno.serve(async (req) => {
  if (!CHIAVE) return Response.json({ errore: "manca SEARCHAPI_KEY" }, { status: 500 });
  const b = await req.json().catch(() => ({}));
  try {
    if (b.tipo === "maps" && typeof b.q === "string" && b.q.length <= 160) {
      const d = await chiedi({ engine: "google_maps", q: b.q });
      const schede = (d.local_results ?? []).slice(0, 8).map((r: Record<string, unknown>) => ({
        nome: r.title, voto: r.rating, recensioni: r.reviews, indirizzo: r.address, tipo: r.type, sito: r.website, data_id: r.data_id,
      }));
      return Response.json({ schede });
    }
    if (b.tipo === "recensioni" && typeof b.data_id === "string") {
      const pagine = Math.min(3, Math.max(1, Number(b.pagine) || 2));
      const tutte: unknown[] = [];
      let token = "";
      for (let i = 0; i < pagine; i++) {
        const d = await chiedi({ engine: "google_maps_reviews", data_id: b.data_id, sort_by: "lowest_rating", ...(token ? { next_page_token: token } : {}) });
        for (const r of d.reviews ?? []) tutte.push({ voto: r.rating, data: String(r.iso_date ?? "").slice(0, 10), testo: String(r.text ?? "").slice(0, 700) });
        token = d.pagination?.next_page_token ?? "";
        if (!token) break;
      }
      return Response.json({ recensioni: tutte });
    }
    if (b.tipo === "google" && typeof b.q === "string" && b.q.length <= 200) {
      const d = await chiedi({ engine: "google", q: b.q });
      const risultati = (d.organic_results ?? []).slice(0, 8).map((r: Record<string, unknown>) => ({ titolo: r.title, link: r.link, frase: r.snippet }));
      return Response.json({ risultati });
    }
    return Response.json({ errore: "tipo: maps, recensioni o google" }, { status: 400 });
  } catch (e) {
    return Response.json({ errore: String(e) }, { status: 502 });
  }
});
