CREATE TABLE public.company_alerts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_key text NOT NULL,
  meeting_id text NOT NULL,
  target_name text NOT NULL,
  room_id text NOT NULL,
  sender_id text NOT NULL,
  sender_name text,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL DEFAULT (now() + interval '10 minutes')
);
GRANT ALL ON public.company_alerts TO service_role;
ALTER TABLE public.company_alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "No direct client access to alerts" ON public.company_alerts FOR SELECT USING (false);
CREATE INDEX company_alerts_lookup ON public.company_alerts (group_key, meeting_id, expires_at);