CREATE TABLE public.drafts_crawl_cache (
  root text PRIMARY KEY,
  result jsonb,
  scanned_at timestamptz,
  lock_until timestamptz NOT NULL DEFAULT 'epoch'
);
GRANT ALL ON public.drafts_crawl_cache TO service_role;
ALTER TABLE public.drafts_crawl_cache ENABLE ROW LEVEL SECURITY;

-- Atomically claim the right to rescan one Drafts tree; false while another scan holds the lock.
CREATE OR REPLACE FUNCTION public.claim_drafts_crawl(_root text, _lock_seconds int)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE ok boolean;
BEGIN
  INSERT INTO public.drafts_crawl_cache(root, lock_until)
  VALUES (_root, now() + make_interval(secs => _lock_seconds))
  ON CONFLICT (root) DO UPDATE SET lock_until = EXCLUDED.lock_until
  WHERE public.drafts_crawl_cache.lock_until < now()
  RETURNING true INTO ok;
  RETURN coalesce(ok, false);
END $$;
REVOKE ALL ON FUNCTION public.claim_drafts_crawl(text, int) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_drafts_crawl(text, int) TO service_role;