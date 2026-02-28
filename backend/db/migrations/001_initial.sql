-- JumpAI Initial Schema
-- Run in your Supabase SQL editor or against a PostgreSQL instance.

-- Users table (Supabase Auth populates auth.users — this is app metadata)
CREATE TABLE IF NOT EXISTS public.user_profiles (
    user_id    UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Jump analysis jobs
CREATE TABLE IF NOT EXISTS public.jobs (
    job_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES public.user_profiles(user_id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    step        TEXT DEFAULT '',
    filename    TEXT,
    video_url   TEXT,   -- Supabase Storage URL after upload
    error       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Full analysis results (one per completed job)
CREATE TABLE IF NOT EXISTS public.analysis_results (
    job_id              UUID PRIMARY KEY REFERENCES public.jobs(job_id) ON DELETE CASCADE,
    user_id             UUID REFERENCES public.user_profiles(user_id) ON DELETE CASCADE,
    jump_height_inches  FLOAT,
    jump_height_cm      FLOAT,
    flight_time_ms      FLOAT,
    confidence          FLOAT,
    scorecard           JSONB,
    biomechanics        JSONB,
    claude_report       TEXT,
    jump_event          JSONB,
    video_metadata      JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_jobs_user_id       ON public.jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status        ON public.jobs(status);
CREATE INDEX IF NOT EXISTS idx_results_user_id    ON public.analysis_results(user_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON public.analysis_results(created_at DESC);

-- Row-level security: users can only see their own data
ALTER TABLE public.jobs            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles   ENABLE ROW LEVEL SECURITY;

CREATE POLICY jobs_user_select ON public.jobs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY results_user_select ON public.analysis_results
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY profiles_user_select ON public.user_profiles
    FOR SELECT USING (auth.uid() = user_id);
