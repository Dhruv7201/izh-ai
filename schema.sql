-- SQL: iZhinga itinerary + embeddings + minimal API catalog
-- Requires pgvector
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS travel;

-- Set your embedding dimension consistently
-- Change 1536 → your embedding size
----------------------------------------------------------

-- 1) Itinerary table with versioning
CREATE TABLE travel.itinerary_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    itinerary_group_id UUID NOT NULL,
    user_id UUID NOT NULL,                       -- will map to backend users table later
    version INTEGER NOT NULL DEFAULT 1,
    title TEXT,
    summary TEXT,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft',
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    itinerary_embedding VECTOR(1536),
    embedding_source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX ON travel.itinerary_versions (itinerary_group_id);
CREATE INDEX ON travel.itinerary_versions (user_id);
CREATE INDEX ON travel.itinerary_versions (status);

CREATE INDEX IF NOT EXISTS idx_itinerary_embedding_ivfflat
    ON travel.itinerary_versions USING ivfflat (itinerary_embedding) WITH (lists = 100);

----------------------------------------------------------

-- 2) Activities inside itinerary
CREATE TABLE travel.itinerary_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    itinerary_version_id UUID NOT NULL REFERENCES travel.itinerary_versions(id) ON DELETE CASCADE,
    day_index INTEGER NOT NULL,
    start_time TIME,
    end_time TIME,
    location_id UUID,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON travel.itinerary_activities (itinerary_version_id);
CREATE INDEX ON travel.itinerary_activities (day_index);

----------------------------------------------------------

-- 3) User Embeddings
CREATE TABLE travel.user_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    embedding_type TEXT NOT NULL,
    source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON travel.user_embeddings (user_id);
CREATE INDEX IF NOT EXISTS idx_user_embeddings_ivfflat
    ON travel.user_embeddings USING ivfflat (embedding) WITH (lists = 100);

----------------------------------------------------------

-- 4) Social Media Embeddings
CREATE TABLE travel.user_social_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    platform TEXT NOT NULL,
    external_id TEXT,
    post_text TEXT,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON travel.user_social_embeddings (user_id);
CREATE INDEX IF NOT EXISTS idx_user_social_embeddings_ivfflat
    ON travel.user_social_embeddings USING ivfflat (embedding) WITH (lists = 100);

----------------------------------------------------------

-- 5) Preferences Table
CREATE TABLE travel.preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    pref_key TEXT NOT NULL,
    pref_value JSONB NOT NULL,
    weight FLOAT DEFAULT 1.0,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON travel.preferences (user_id);
CREATE INDEX ON travel.preferences (pref_key);

CREATE INDEX IF NOT EXISTS idx_preferences_embedding_ivfflat
    ON travel.preferences USING ivfflat (embedding) WITH (lists = 100);

----------------------------------------------------------

-- 6) MINIMAL API Endpoints Table
-- This will be autoinserted from FastAPI introspection
-- So only store useful basic metadata (no schemas etc.)

CREATE TABLE travel.api_endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,         -- internal name, e.g. "get_itinerary"
    path TEXT NOT NULL,                -- "/itinerary/{id}"
    method TEXT NOT NULL,              -- GET / POST / PUT
    description TEXT,                  -- summary/description pulled from FastAPI docstring
    tags TEXT[],                       -- FastAPI tags to group endpoints
    rate_limit JSONB DEFAULT '{}'::jsonb,  -- optional limits
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON travel.api_endpoints (name);
CREATE INDEX ON travel.api_endpoints (path);

----------------------------------------------------------

-- 7) Trigger to maintain only one current version
CREATE OR REPLACE FUNCTION travel.ensure_single_current_itinerary()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_current = TRUE THEN
        UPDATE travel.itinerary_versions
        SET is_current = FALSE
        WHERE itinerary_group_id = NEW.itinerary_group_id
          AND id <> NEW.id;
    END IF;

    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_single_current_itinerary
BEFORE INSERT OR UPDATE ON travel.itinerary_versions
FOR EACH ROW
EXECUTE FUNCTION travel.ensure_single_current_itinerary();

----------------------------------------------------------

-- 8) View: quickly fetch only current versions
CREATE OR REPLACE VIEW travel.current_itineraries AS
SELECT *
FROM travel.itinerary_versions
WHERE is_current = TRUE AND deleted_at IS NULL;

----------------------------------------------------------
-- END OF SCRIPT
