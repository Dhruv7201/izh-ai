

CREATE TABLE IF NOT EXISTS user_embedding (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    embedding TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    endpoint VARCHAR(255),
    model VARCHAR(100),
    tokens_used INTEGER,
    cost DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_user_id ON api_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage(created_at);

-- POI Tables
CREATE TABLE IF NOT EXISTS pois (
    id SERIAL PRIMARY KEY,
    destination_name VARCHAR(255) NOT NULL,
    destination_lat DECIMAL(10, 8) NOT NULL,
    destination_lng DECIMAL(11, 8) NOT NULL,
    poi_uuid UUID NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    name VARCHAR(500) NOT NULL,
    lat DECIMAL(10, 8) NOT NULL,
    lng DECIMAL(11, 8) NOT NULL,
    rating DECIMAL(3, 2),
    address TEXT,
    cluster_id VARCHAR(50),
    ingestion_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(poi_uuid),
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS poi_details (
    id SERIAL PRIMARY KEY,
    poi_id INTEGER REFERENCES pois(id) ON DELETE CASCADE,
    categories JSONB DEFAULT '[]'::jsonb,
    opening_hours JSONB DEFAULT '[]'::jsonb,
    duration_minutes INTEGER DEFAULT 90,
    best_time JSONB DEFAULT '["any"]'::jsonb,
    photos JSONB DEFAULT '[]'::jsonb,
    user_ratings_total INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(poi_id)
);

CREATE INDEX IF NOT EXISTS idx_pois_destination ON pois(destination_name, destination_lat, destination_lng);
CREATE INDEX IF NOT EXISTS idx_pois_cluster_id ON pois(cluster_id);
CREATE INDEX IF NOT EXISTS idx_pois_source ON pois(source, source_id);
CREATE INDEX IF NOT EXISTS idx_pois_location ON pois(lat, lng);
CREATE INDEX IF NOT EXISTS idx_pois_ingestion_date ON pois(ingestion_date);
CREATE INDEX IF NOT EXISTS idx_poi_details_poi_id ON poi_details(poi_id);