# 🎵 VibeFlow — Intelligent Cross-Platform Music Companion

> A hybrid ML + Agent-based music recommendation system that learns your taste
> across Spotify and YouTube Music, adapts your playlist in real-time based on
> skips and session context, and delivers a daily song pick + weekend playlist.

---

## 📌 Project Overview

| Field        | Detail                                               |
|--------------|------------------------------------------------------|
| Project Name | VibeFlow                                             |
| Type         | Personal ML Project / Portfolio                      |
| Platforms    | Spotify + YouTube Music + Local Library              |
| Core Problem | Generic shuffle ignores real-time genre/mood intent  |
| Solution     | Hybrid Recommender + Session-Aware Contextual Bandit |
| Output       | Daily Song · Weekend Playlist · Live Adaptive Queue  |

---

## 🎯 Core Features

### Feature 1 — Long-Term Taste Profile (Recommender System)

Builds a persistent taste model from your Spotify and YT Music history. Delivers:

- **Daily Song Recommendation** — One perfectly matched song every morning
- **Weekend Playlist** — A 25–30 song playlist generated every Friday night, curated using mood clustering across your listening week

### Feature 2 — Real-Time Session Adaptation (Contextual Bandit Agent) ⭐ NEW

Monitors what you're actively playing and adapts the queue on the fly.

- Detects current genre/mood from the active session (last 3–5 songs)
- Tracks skip behavior: skipped in <15s = strong negative signal
- Removes songs acoustically similar to skipped tracks from the queue
- Promotes songs similar to fully-played tracks
- Works on your **local downloaded library** (500–600 songs) without needing an internet connection

---

## 🧠 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                       DATA LAYER                        │
│  Spotify Web API ──► Listening History DB               │
│  ytmusicapi      ──► (PostgreSQL)                       │
│  Local Files     ──► Audio Feature Store                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   FEATURE PIPELINE                      │
│  - Audio Features (librosa): MFCC, Spectral Centroid,   │
│    Chroma, Tempo, Energy, Valence                       │
│  - Spotify Audio Features API (for online tracks)       │
│  - Behavioral Features: skip rate, replay count,        │
│    completion rate, save/like                           │
│  - Temporal Features: time of day, day of week,         │
│    session length                                       │
│  - Genre Labels: CNN classifier on mel-spectrograms     │
└────────────────────────┬────────────────────────────────┘
                         │
           ┌─────────────┴──────────────┐
           │                            │
┌──────────▼──────────┐    ┌────────────▼────────────────┐
│   LONG-TERM ENGINE  │    │     SESSION-AWARE AGENT      │
│    (Recommender)    │    │     (Contextual Bandit)      │
│                     │    │                              │
│  - Content-Based    │    │  Context Vector:             │
│    (Cosine Sim on   │    │  [genre_now, skip_rate,      │
│    audio features)  │    │   session_energy, time,      │
│  - Collaborative    │    │   last_3_songs_features]     │
│    Filtering (ALS)  │    │                              │
│  - Temporal Decay   │    │  Action: next song to play   │
│  - LSTM/BERT4Rec    │    │  Reward: play% > 80% = +1   │
│    (sequential)     │    │          skip < 15s  = -1   │
│                     │    │                              │
│  Output:            │    │  Algorithm: LinUCB           │
│  Daily Song +       │    │  (Linear Upper Confidence    │
│  Weekend Playlist   │    │   Bound — fast & efficient)  │
└──────────┬──────────┘    └────────────┬────────────────┘
           │                            │
           └─────────────┬──────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                     OUTPUT LAYER                        │
│  FastAPI Backend  ──► REST Endpoints                    │
│  APScheduler      ──► Daily / Weekly triggers           │
│  Streamlit UI     ──► Dashboard + Manual controls       │
│  Telegram Bot     ──► Daily push notification           │
└─────────────────────────────────────────────────────────┘
```

---

## 🤖 ML Models — Detailed Breakdown

### 1. Genre Classifier (for Local Library)
- **Input**: Raw audio file (`.mp3` / `.flac`)
- **Method**: Extract mel-spectrogram → CNN classifier
- **Alternative (lightweight)**: Extract MFCC + Spectral features via `librosa` → Random Forest / XGBoost genre classifier
- **Training Data**: GTZAN dataset (1000 labeled songs, 10 genres)
- **Output**: Genre label + confidence score per local song
- **Library**: `librosa`, `scikit-learn` or `PyTorch`

### 2. Content-Based Recommender
- **Input**: Audio feature vectors (13 features per song)
- **Method**: Cosine Similarity
- **Use Case**: "Songs that sound like what I've been playing"
- **Library**: `scikit-learn`

### 3. Collaborative Filter (Long-Term)
- **Input**: Implicit feedback matrix (user × song interactions)
- **Method**: ALS (Alternating Least Squares) Matrix Factorization
- **Use Case**: "Users with similar taste loved this track"
- **Library**: `implicit`

### 4. Sequential Model (Session Prediction)
- **Input**: Ordered sequence of last N songs played
- **Method**: LSTM or BERT4Rec (Transformer-based)
- **Use Case**: "Given what I've played in this session, what's next?"
- **Library**: `PyTorch`

### 5. Contextual Bandit Agent (Real-Time Adaptation) ⭐ CORE
- **Input**: Context vector = `[genre_embedding, skip_rate_last_5, avg_energy_session, hour_of_day, day_of_week, tempo_variance]`
- **Algorithm**: **LinUCB** (Linear Upper Confidence Bound)
- **Why LinUCB**: Fast, interpretable, works with small data, balances exploration (try new songs) vs exploitation (play known favs)
- **Reward Signal**:
  - `+1.0` → Song played >80% through
  - `+0.5` → Song played 40–80%
  - `-0.5` → Song skipped after 15–40s
  - `-1.0` → Song skipped within 15s
- **Update Cycle**: After **every** song — the agent updates its weights live
- **Library**: `vowpalwabbit` or custom NumPy implementation (LinUCB is ~50 lines)

### 6. Weekend Playlist Generator
- **Method**: UMAP (dimensionality reduction) + HDBSCAN (clustering) on the week's listening features
- **Output**: 5–6 mood clusters → sample 5 songs per cluster = 25–30 song playlist
- **Library**: `umap-learn`, `hdbscan`

---

## 🗃️ Database Schema

```sql
-- Songs Master Table (covers both online + local)
CREATE TABLE songs (
    song_id          VARCHAR PRIMARY KEY,  -- Spotify ID or MD5 hash for local
    title            VARCHAR NOT NULL,
    artist           VARCHAR NOT NULL,
    album            VARCHAR,
    source           VARCHAR,              -- 'spotify', 'ytmusic', 'local'
    duration_ms      INTEGER,
    file_path        VARCHAR,              -- NULL for streaming tracks
    genre            VARCHAR,
    danceability     FLOAT, energy FLOAT, valence FLOAT,
    tempo            FLOAT, acousticness FLOAT,
    instrumentalness FLOAT, speechiness   FLOAT,
    mfcc_vector      JSONB,               -- 13-dim MFCC for local files
    added_at         TIMESTAMP DEFAULT NOW()
);

-- Listening History
CREATE TABLE listening_history (
    id               SERIAL PRIMARY KEY,
    song_id          VARCHAR REFERENCES songs(song_id),
    played_at        TIMESTAMP NOT NULL,
    play_duration_ms INTEGER,             -- How long was it actually played?
    song_duration_ms INTEGER,
    completion_pct   FLOAT,               -- play_duration / song_duration
    skipped          BOOLEAN DEFAULT FALSE,
    skip_time_ms     INTEGER,             -- At what point was it skipped?
    source           VARCHAR,             -- 'spotify', 'ytmusic', 'local'
    session_id       VARCHAR              -- Groups songs in same listening session
);

-- Sessions
CREATE TABLE sessions (
    session_id       VARCHAR PRIMARY KEY,
    started_at       TIMESTAMP,
    ended_at         TIMESTAMP,
    dominant_genre   VARCHAR,
    avg_energy       FLOAT,
    song_count       INTEGER,
    skip_rate        FLOAT
);

-- Bandit State (persisted between sessions)
CREATE TABLE bandit_state (
    song_id          VARCHAR PRIMARY KEY,
    A_matrix         JSONB,              -- LinUCB A matrix per arm
    b_vector         JSONB,              -- LinUCB b vector per arm
    play_count       INTEGER DEFAULT 0,
    skip_count       INTEGER DEFAULT 0,
    last_updated     TIMESTAMP
);

-- Recommendations Log
CREATE TABLE recommendations (
    id               SERIAL PRIMARY KEY,
    rec_type         VARCHAR,            -- 'daily', 'weekend', 'session'
    song_id          VARCHAR REFERENCES songs(song_id),
    recommended_at   TIMESTAMP,
    was_played       BOOLEAN,
    user_rating      INTEGER             -- Optional: 1-5 explicit rating
);
```

---

## 🛠️ Tech Stack

| Layer             | Technology                          | Purpose                          |
|-------------------|-------------------------------------|----------------------------------|
| Data Collection   | Spotify Web API, ytmusicapi         | Fetch history + audio features   |
| Audio Analysis    | librosa, ffmpeg                     | Local file feature extraction    |
| Genre Classifier  | PyTorch CNN or scikit-learn XGBoost | Label local songs by genre       |
| Recommender       | implicit (ALS), scikit-learn        | Long-term taste modeling         |
| Sequential Model  | PyTorch (LSTM / BERT4Rec)           | Session-level prediction         |
| Bandit Agent      | vowpalwabbit or custom NumPy        | Real-time session adaptation     |
| Clustering        | umap-learn, hdbscan                 | Weekend playlist generation      |
| Database          | PostgreSQL                          | Persistent storage               |
| Backend           | FastAPI                             | REST API for all interactions    |
| Scheduler         | APScheduler                         | Daily song + weekly playlist jobs|
| Frontend          | Streamlit                           | Dashboard + playlist controls    |
| Notifications     | Telegram Bot API (python-telegram-bot) | Daily push delivery           |
| Containerization  | Docker + Docker Compose             | Deploy everything cleanly        |

---

## 📡 API Endpoints (FastAPI)

```
GET  /recommend/daily      →  Today's recommended song
GET  /recommend/weekend    →  This weekend's playlist
GET  /session/next         →  Next song from bandit agent (real-time)
POST /session/feedback     →  Send skip/play signal to update bandit
GET  /library/genres       →  Genre breakdown of local library
GET  /stats/taste-profile  →  Your long-term taste summary
POST /library/scan         →  Trigger re-scan of local music folder
GET  /history/sessions     →  Past listening sessions
```

---

## 🗓️ Build Phases

### Phase 1 — Foundation (Week 1–2)
- [ ] Spotify OAuth2 setup + history fetcher
- [ ] ytmusicapi setup + liked songs/history pull
- [ ] PostgreSQL schema setup + Docker Compose
- [ ] Local file scanner: walk directory, extract metadata + librosa features
- [ ] Unified song ingestion pipeline

### Phase 2 — Genre Intelligence (Week 3)
- [ ] Download GTZAN dataset
- [ ] Train genre classifier (XGBoost on MFCC first, CNN if needed)
- [ ] Tag all 500–600 local songs with genre + confidence
- [ ] Build genre distribution visualizer in Streamlit

### Phase 3 — Long-Term Recommender (Week 4–5)
- [ ] Content-based recommender (cosine similarity)
- [ ] ALS collaborative filter (use `implicit` library)
- [ ] Hybrid blending layer (weighted average of both scores)
- [ ] Daily song scheduler (APScheduler → runs at 8 AM)

### Phase 4 — Contextual Bandit Agent (Week 6–7) ⭐
- [ ] Session tracker: group songs by inactivity gap (>30 min = new session)
- [ ] Context vector builder (genre, energy, skip_rate, time features)
- [ ] LinUCB implementation (from scratch in NumPy — great for learning)
- [ ] Feedback endpoint: `POST /session/feedback`
- [ ] Bandit state persistence in PostgreSQL (survives restarts)
- [ ] Real-time queue manager: agent picks next song before current ends

### Phase 5 — Weekend Playlist (Week 8)
- [ ] Weekly aggregator: collect all session vectors from Mon–Fri
- [ ] UMAP → HDBSCAN clustering
- [ ] Playlist sampler: pick proportionally from each cluster
- [ ] Friday 7 PM trigger via APScheduler

### Phase 6 — Polish & Deliver (Week 9–10)
- [ ] Streamlit dashboard (history, taste profile, manual controls)
- [ ] Telegram bot for daily/weekly delivery
- [ ] Docker Compose final setup (FastAPI + PostgreSQL + Streamlit)
- [ ] README + Architecture diagram for GitHub
- [ ] Demo video recording

---

## ⚠️ Key Challenges & Mitigations

| Challenge                            | Mitigation                                                       |
|--------------------------------------|------------------------------------------------------------------|
| YT Music ↔ Spotify song mapping      | `rapidfuzz` fuzzy matching on title + artist                     |
| Local songs not on Spotify           | Use `librosa` features directly, skip Spotify lookup             |
| Cold start (new songs/new user)      | Pre-seed bandit with content-based similarity scores             |
| Skip signal ambiguity                | Use time-based thresholds (<15s hard skip, 15–40s soft)          |
| Bandit over-exploiting favorites     | LinUCB's UCB term handles exploration automatically              |
| Spotify API rate limits              | Cache all API calls; poll history max once per hour              |
| Genre model accuracy                 | Start with 6 broad genres, not 20 fine-grained ones             |

---

## 📁 Project Structure

```
vibeflow/
├── docker-compose.yml
├── .env                          # API keys, DB credentials
│
├── data_collection/
│   ├── spotify_client.py         # OAuth + history fetcher
│   ├── ytmusic_client.py         # ytmusicapi wrapper
│   ├── local_scanner.py          # Local file feature extractor
│   └── ingestion_pipeline.py     # Unified song → DB writer
│
├── models/
│   ├── genre_classifier/
│   │   ├── train.py
│   │   └── predict.py
│   ├── content_based.py          # Cosine similarity recommender
│   ├── collaborative.py          # ALS matrix factorization
│   ├── sequential.py             # LSTM / BERT4Rec
│   ├── bandit/
│   │   ├── linucb.py             # Core LinUCB implementation
│   │   ├── context_builder.py    # Builds context vector per session
│   │   └── session_tracker.py    # Tracks active session state
│   └── weekend_playlist.py       # UMAP + HDBSCAN generator
│
├── api/
│   ├── main.py                   # FastAPI app
│   ├── routers/
│   │   ├── recommend.py
│   │   ├── session.py
│   │   └── library.py
│   └── scheduler.py              # APScheduler jobs
│
├── dashboard/
│   └── app.py                    # Streamlit UI
│
├── bot/
│   └── telegram_bot.py           # Daily notification bot
│
└── db/
    ├── models.py                 # SQLAlchemy ORM models
    └── schema.sql                # Raw schema for reference
```

---

## 🏆 What Makes VibeFlow Different

| Feature                              | Spotify   | YT Music  | Samsung Music | VibeFlow ✅ |
|--------------------------------------|:---------:|:---------:|:-------------:|:-----------:|
| Cross-platform taste profile         | ❌        | ❌        | ❌            | ✅          |
| Works on local downloads             | ❌        | ❌        | Shuffle only  | ✅          |
| Adapts to session skip behavior      | Partial   | ❌        | ❌            | ✅ (Bandit) |
| Genre-aware real-time queue          | Partial   | ❌        | ❌            | ✅          |
| Daily single song pick               | ❌        | ❌        | ❌            | ✅          |
| Weekend playlist generation          | Partial   | ❌        | ❌            | ✅          |
| Fully private / self-hosted          | ❌        | ❌        | ❌            | ✅          |

---

*VibeFlow v1.0 · 2026*