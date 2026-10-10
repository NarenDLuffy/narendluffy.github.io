CREATE TABLE public.meeting_settings (
  meeting_id text PRIMARY KEY,
  remote_ftp_host text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
GRANT ALL ON public.meeting_settings TO service_role;
ALTER TABLE public.meeting_settings ENABLE ROW LEVEL SECURITY;