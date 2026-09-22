-- v49 (22/9/2026): L'IMPRONTA DIGITALE.
--
-- Dre: «se fanno pubblicità non è positivo di per sé: la domanda diventa se la
-- fanno bene o male, e lì si va a penetrare». Prima sapevamo solo fa_ads sì/no,
-- che non dice niente sull'angolo da usare nella mail.
--
-- Ora si misura, per ogni dominio: chi paga gli annunci (e se quel pagante
-- compare su più aziende, cioè è un rivenditore), e quali tag ha sul sito, che
-- dicono se misura quello che spende. Sono gli stessi strumenti che Carlo
-- installa ai clienti nuovi: Clarity, Analytics, Tag Manager, Google Ads.
--
-- Il limite è scritto nel dato stesso: misura='forse' quando c'è Tag Manager,
-- perché lì dentro il tag conversioni può esserci senza comparire nell'HTML
-- (misurato: solo il 13% lo mostra nel codice, il 54% ha Tag Manager).

alter table raccolta add column if not exists angolo         text;
alter table raccolta add column if not exists angolo_perche  text;
alter table raccolta add column if not exists misura         text;
alter table raccolta add column if not exists sito_letto_tag boolean;
alter table raccolta add column if not exists tag_google_ads  boolean;
alter table raccolta add column if not exists tag_analytics   boolean;
alter table raccolta add column if not exists tag_tag_manager boolean;
alter table raccolta add column if not exists tag_clarity     boolean;
alter table raccolta add column if not exists tag_meta_pixel  boolean;

-- i quattro angoli di Dre: non_fa_ads | fermo | investe | rivenditore
comment on column raccolta.angolo is
  'La situazione pubblicitaria in una parola, da cui dipende l''angolo della mail';
comment on column raccolta.misura is
  'si = tag conversioni visto | forse = c''e'' Tag Manager, puo'' stare dentro | no = nessuno dei due | non_letto';

create index if not exists idx_raccolta_da_impronta on raccolta(angolo) where angolo is null;
create index if not exists idx_raccolta_angolo on raccolta(angolo, misura);
