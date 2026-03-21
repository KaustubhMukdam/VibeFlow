-- VibeFlow Database Schema v1.0

CREATE TABLE IF NOT EXISTS songs (
    song_id              VARCHAR(255) PRIMARY KEY,
    title                VARCHAR(500) NOT NULL,
    artist               VARCHAR(500) NOT NULL,
    album                VARCHAR(500),
    source               VARCHAR(50) CHECK (source IN ('spotify', 'ytmusic', 'local', 'ytmusic_only')),
    duration_ms          INTEGER,
    file_path            TEXT,
    genre                VARCHAR(100),
    genre_confidence     FLOAT,
    danceability         FLOAT,
    energy               FLOAT,
    valence              FLOAT,
    tempo                FLOAT,
    acousticness         FLOAT,
    instrumentalness     FLOAT,
    speechiness          FLOAT,
    loudness             FLOAT,
    mfcc_vector          JSONB,
    added_at             TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id           VARCHAR(255) PRIMARY KEY,
    started_at           TIMESTAMP NOT NULL,
    ended_at             TIMESTAMP,
    dominant_genre       VARCHAR(100),
    avg_energy           FLOAT,
    song_count           INTEGER DEFAULT 0,
    skip_rate            FLOAT DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS listening_history (
    id                   SERIAL PRIMARY KEY,
    song_id              VARCHAR(255) REFERENCES songs(song_id) ON DELETE CASCADE,
    played_at            TIMESTAMP NOT NULL,
    play_duration_ms     INTEGER,
    song_duration_ms     INTEGER,
    completion_pct       FLOAT GENERATED ALWAYS AS (
                             CASE WHEN song_duration_ms > 0
                             THEN (play_duration_ms::FLOAT / song_duration_ms) * 100
                             ELSE NULL END
                         ) STORED,
    skipped              BOOLEAN DEFAULT FALSE,
    skip_time_ms         INTEGER,
    source               VARCHAR(50),
    session_id           VARCHAR(255) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS bandit_state (
    song_id              VARCHAR(255) PRIMARY KEY REFERENCES songs(song_id) ON DELETE CASCADE,
    A_matrix             JSONB NOT NULL,
    b_vector             JSONB NOT NULL,
    play_count           INTEGER DEFAULT 0,
    skip_count           INTEGER DEFAULT 0,
    total_reward         FLOAT DEFAULT 0.0,
    last_updated         TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recommendations (
    id                   SERIAL PRIMARY KEY,
    rec_type             VARCHAR(50) CHECK (rec_type IN ('daily', 'weekend', 'session')),
    song_id              VARCHAR(255) REFERENCES songs(song_id),
    recommended_at       TIMESTAMP DEFAULT NOW(),
    was_played           BOOLEAN DEFAULT FALSE,
    user_rating          INTEGER CHECK (user_rating BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS playlists (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    source     VARCHAR(50) DEFAULT 'local',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    id          SERIAL PRIMARY KEY,
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    song_id     VARCHAR(255) REFERENCES songs(song_id) ON DELETE CASCADE,
    position    INTEGER,
    UNIQUE(playlist_id, song_id)
);


-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_history_played_at ON listening_history(played_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_song_id   ON listening_history(song_id);
CREATE INDEX IF NOT EXISTS idx_history_session   ON listening_history(session_id);
CREATE INDEX IF NOT EXISTS idx_songs_source      ON songs(source);
CREATE INDEX IF NOT EXISTS idx_songs_genre       ON songs(genre);
CREATE INDEX IF NOT EXISTS idx_recs_type_date    ON recommendations(rec_type, recommended_at DESC);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_pid ON playlist_tracks(playlist_id);
