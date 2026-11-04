-- v109 (4/11): la call prenotata da Clara porta l'orario confermato (book_meeting.meeting_at);
-- il postino crea l'evento con Meet nel calendario di Dramane e Google manda l'invito al lead.
alter table clara_decisioni add column if not exists appuntamento timestamptz;
notify pgrst, 'reload schema';
