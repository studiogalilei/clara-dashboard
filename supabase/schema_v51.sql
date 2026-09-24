-- LE SETTE MIGLIORIE ACCETTATE DA DRE (24/9/2026)
-- avvisi: la notifica arriva a chi deve fare la task, non solo al ceo.
-- lezioni: una volta a settimana Clara legge le correzioni di Dre alle bozze
--          (bozza_originale vs bozza approvata) e propone tre regole.
-- arricchisci: Clara riempie sito, settore e «chi sono» da quello che sa (fit,
--          raccolta, una ricerca precisa); a Dre restano referente, ruolo, telefono.
-- clara_misure: tre numeri per sapere se Clara migliora.
alter table task add column if not exists avvisata_il timestamptz;

insert into operazioni (chiave, nome, cosa, comando, cadenza_minuti, ordine, attiva) values
  ('avvisi', 'Le notifiche a chi deve fare', 'Una task nuova arriva sul telefono di chi la deve fare, con la scadenza.', 'python3 scripts/avvisi.py', 5, 4, false),
  ('lezioni', 'Le lezioni dalle correzioni', 'Ogni settimana Clara confronta le sue bozze con quelle che Dre ha mandato e propone tre regole in Posta.', 'python3 scripts/lezioni.py', 10080, 30, false),
  ('arricchisci', 'Clara riempie quello che sa', 'Sito, settore e «chi sono» dalle fonti che ha (fit, raccolta, ricerca precisa). Referente, ruolo e telefono restano a chi ha parlato con la persona.', 'python3 scripts/arricchisci.py', 60, 9, false)
on conflict (chiave) do update set cosa = excluded.cosa, comando = excluded.comando, cadenza_minuti = excluded.cadenza_minuti;

-- MISURARE CLARA (da Galileo: prima si misura, poi si migliora)
create or replace function clara_misure()
returns jsonb language sql stable security definer set search_path = public as $$
  with b as (
    select pr.id, pr.at, pr.stato, pr.azione, p.last_reply_at
    from proposte pr left join prospects p on p.id = pr.prospect_id
    where pr.tipo in ('risposta', 'umano') and pr.azione ? 'bozza' and pr.at > now() - interval '30 days'
  )
  select jsonb_build_object(
    'bozze', (select count(*) from b),
    'minuti_mediani', (select round(percentile_cont(0.5) within group (order by extract(epoch from (at - last_reply_at)) / 60))
                       from b where last_reply_at is not null and at > last_reply_at and at - last_reply_at < interval '3 days'),
    'mandate', (select count(*) from b where stato = 'fatta'),
    'senza_correzioni', (select count(*) from b where stato = 'fatta' and azione ? 'bozza_originale' and azione->>'bozza_originale' = azione->>'bozza'),
    'con_correzioni', (select count(*) from b where stato = 'fatta' and azione ? 'bozza_originale' and azione->>'bozza_originale' <> azione->>'bozza'),
    'rifiutate', (select count(*) from b where stato = 'no')
  );
$$;
grant execute on function clara_misure() to authenticated;
