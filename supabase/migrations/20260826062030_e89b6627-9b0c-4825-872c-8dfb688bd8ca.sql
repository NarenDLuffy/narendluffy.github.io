CREATE TABLE public.company_presence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_key text NOT NULL,
  user_id text NOT NULL,
  meeting_id text NOT NULL,
  room_id text NOT NULL,
  session_id text,
  display_name text,
  updated_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL DEFAULT now() + interval '2 hours',
  UNIQUE (group_key, user_id, meeting_id)
);

CREATE INDEX company_presence_lookup_idx
  ON public.company_presence (group_key, meeting_id, expires_at);

GRANT ALL ON public.company_presence TO service_role;

ALTER TABLE public.company_presence ENABLE ROW LEVEL SECURITY;

CREATE POLICY "No direct client access to presence"
  ON public.company_presence FOR SELECT USING (false);