// LA PARTITA IVA CHE SI COMPILA DA SOLA (15/9/2026).
//
// Sui dati veri nessuna delle 13.193 aziende ha i dati fiscali, quindi ogni
// primo preventivo si ferma li': ragione sociale, partita IVA e indirizzo da
// cercare e battere a mano. Ma quei dati sono pubblici: il registro europeo
// VIES li restituisce dalla partita IVA. Non si puo' chiamarlo dal browser
// (non manda le intestazioni CORS), quindi passa da qui.
//
// COME SI METTE IN CLOUD (una volta):
//   npx supabase functions deploy piva --project-ref tqssfcuzezlczfceqsmk
// Resta protetta dal JWT: la chiama solo chi e' dentro il Workspace.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

function risposta(corpo: unknown, stato = 200) {
  return new Response(JSON.stringify(corpo), {
    status: stato,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

// «IT 12485671007», «12485671007», «IT12485671007» sono la stessa cosa
function pulisci(grezzo: string): { paese: string; numero: string } | null {
  const t = (grezzo || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (!t) return null;
  const paese = /^[A-Z]{2}/.test(t) ? t.slice(0, 2) : "IT";
  const numero = /^[A-Z]{2}/.test(t) ? t.slice(2) : t;
  if (numero.length < 8 || numero.length > 12) return null;
  return { paese, numero };
}

// «VIALE F TOMMASO MARINETTI 221 \n00143 ROMA RM\n» in una riga leggibile
function indirizzo(grezzo: string): string {
  return (grezzo || "")
    .split("\n")
    .map((r) => r.trim())
    .filter(Boolean)
    .join(", ")
    .replace(/\s{2,}/g, " ");
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  const url = new URL(req.url);
  const chiesto = url.searchParams.get("p") ?? "";
  const p = pulisci(chiesto);
  if (!p) return risposta({ trovata: false, perche: "Partita IVA non valida" }, 400);

  try {
    const r = await fetch(
      `https://ec.europa.eu/taxation_customs/vies/rest-api/ms/${p.paese}/vat/${p.numero}`,
      { headers: { Accept: "application/json" } },
    );
    if (!r.ok) return risposta({ trovata: false, perche: "Il registro europeo non risponde" }, 502);
    const d = await r.json();
    if (!d.isValid) return risposta({ trovata: false, perche: "Questa partita IVA non risulta" });
    return risposta({
      trovata: true,
      ragione: (d.name ?? "").trim(),
      indirizzo: indirizzo(d.address ?? ""),
      piva: `${p.paese}${p.numero}`,
    });
  } catch (e) {
    return risposta({ trovata: false, perche: String(e).slice(0, 120) }, 502);
  }
});
