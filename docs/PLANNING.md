# VibeFlow — PLANNING.md

> **Version:** 1.0
> **Author:** Kaustubh
> **Repo:** https://github.com/kaustubh05-prog/VibeFlow
> **Started:** March 2026

---

## 🎯 Vision

VibeFlow is a self-hosted, intelligent music companion that learns your listening
taste across Spotify and YouTube Music, adapts your local library queue in
real-time based on what you skip or enjoy in a session, and proactively delivers
a daily song recommendation and a weekend playlist — all without relying on any
streaming platform's built-in algorithm.

---

## 🧩 Problem Statement

1. **Generic shuffle** on Spotify, YT Music, and Samsung Music is completely random — it doesn't know you're in the mood for Punjabi right now, or lo-fi at 2 AM.
2. **Platform silos** — taste data on Spotify and YT Music never merge, so neither platform has the full picture of your preferences.
3. **Local library is blind** — 500–600 downloaded songs have no intelligence layer. The shuffle doesn't understand genre, mood, or your current session intent.
4. **No proactive discovery** — you have to manually hunt for new music. Nothing tells you "this song would be perfect for you today."

---

## ✅ Scope

### In Scope
- Spotify listening history + audio features ingestion (via Spotify Web API)
- YouTube Music liked songs + history ingestion (via `ytmusicapi`)
- Local music library scanning + feature extraction (via `librosa`)
- Genre classification for local files (CNN / XGBoost on mel-spectrograms)
- Long-term hybrid recommendation engine (Content-Based + ALS Collaborative)
- Sequential session model (LSTM / BERT4Rec)
- Real-time session-aware queue adaptation (Contextual Bandit — LinUCB)
- Skip behavior tracking and reward signal pipeline
- Daily song recommendation (scheduled, 8 AM)
- Weekend playlist generation (Fridays, 7 PM) using UMAP + HDBSCAN clustering
- FastAPI REST backend
- Streamlit dashboard (history, taste profile, manual controls)
- Telegram Bot for push delivery
- PostgreSQL for all persistent storage
- Fully containerized via Docker Compose

### Out of Scope (v1.0)
- Mobile app
- Audio playback engine (VibeFlow recommends; you play on your preferred app)
- Multi-user support
- Lyrics analysis / NLP sentiment
- Facial expression / mood detection from camera
- Social features (sharing playlists)

---

## 🏗️ High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         DATA LAYER                           │
│  Local Music Files → librosa + mutagen scanner               │
│  Phone Playlists → M3U parser
│  ytmusicapi       →  Liked Songs, Play History               │
│  Local Scanner    →  MP3/FLAC files via librosa              │
│  PostgreSQL       →  Central persistent store                │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                     FEATURE PIPELINE                         │
│    Audio Features · Behavioral Signals · Temporal Context    │
│    Genre Labels · MFCC Vectors · Skip Signals                │
└───────────────┬───────────────────────────┬──────────────────┘
                │                           │
┌───────────────▼──────────┐   ┌────────────▼─────────────────┐
│    LONG-TERM ENGINE      │   │      SESSION-AWARE AGENT      │
│  Content-Based (Cosine)  │   │  Contextual Bandit (LinUCB)   │
│  Collaborative (ALS)     │   │  Context: genre, energy,      │
│  Sequential (LSTM)       │   │  skip_rate, time of day       │
│  Weekend: UMAP+HDBSCAN   │   │  Reward: play% and skips      │
│  Output: Daily + Weekly  │   │  Output: Live next song       │
└───────────────┬──────────┘   └────────────┬─────────────────┘
                └──────────────┬─────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                        OUTPUT LAYER                          │
│  FastAPI Backend  →  REST API Endpoints                      │
│  APScheduler      →  Daily 8AM / Friday 7PM jobs            │
│  Streamlit UI     →  Dashboard + Manual Overrides            │
│  Telegram Bot     →  Push Notifications                      │
└──────────────────────────────────────────────────────────────┘
```

---

## 🤖 ML Strategy

### Model 1 — Genre Classifier

| Property  | Detail                                           |
|-----------|--------------------------------------------------|
| Purpose   | Assign genre tags to all 500–600 local songs     |
| Input     | Mel-spectrogram or MFCC features per audio file  |
| Algorithm | XGBoost (fast baseline) → CNN if accuracy < 85% |
| Training  | GTZAN dataset (1000 songs, 10 genres)            |
| Output    | Genre label + confidence score                   |
| Library   | `librosa`, `scikit-learn`, `PyTorch` (if CNN)    |

### Model 2 — Content-Based Recommender

| Property  | Detail                                               |
|-----------|------------------------------------------------------|
| Purpose   | Find songs sonically similar to what you've enjoyed  |
| Input     | 13-dim audio feature vector per song                 |
| Algorithm | Cosine Similarity                                    |
| Library   | `scikit-learn`                                       |

### Model 3 — Collaborative Filter

| Property  | Detail                                              |
|-----------|-----------------------------------------------------|
| Purpose   | Long-term implicit preference learning              |
| Input     | Implicit feedback matrix (user × song interactions) |
| Algorithm | ALS — Alternating Least Squares                     |
| Library   | `implicit`                                          |

### Model 4 — Sequential Model

| Property  | Detail                                               |
|-----------|------------------------------------------------------|
| Purpose   | "Given what I played in this session, what's next?"  |
| Input     | Ordered sequence of last N songs (feature vectors)   |
| Algorithm | LSTM (start) → BERT4Rec (upgrade)                   |
| Library   | `PyTorch`                                            |

### Model 5 — Contextual Bandit Agent ⭐ CORE FEATURE

| Property  | Detail                                                         |
|-----------|----------------------------------------------------------------|
| Purpose   | Real-time queue adaptation based on skip behavior              |
| Input     | Context vector: `[genre_embedding, skip_rate_last_5,`          |
|           | `avg_energy_session, hour_of_day, day_of_week,`                |
|           | `tempo_variance, completion_rate_last_5]`                      |
| Algorithm | LinUCB (Linear Upper Confidence Bound)                         |
| Reward    | `+1.0` played >80% · `+0.5` played 40–80%                     |
|           | `-0.5` skipped 15–40s · `-1.0` skipped <15s                   |
| Update    | After every single song — live weight updates                  |
| Library   | Custom NumPy implementation (~50 lines) or `vowpalwabbit`      |

### Model 6 — Weekend Playlist Generator

| Property  | Detail                                              |
|-----------|-----------------------------------------------------|
| Purpose   | Build a 25–30 song playlist from the week's taste   |
| Algorithm | UMAP (reduce dims) → HDBSCAN (cluster moods)        |
|           | Sample proportionally from each cluster             |
| Library   | `umap-learn`, `hdbscan`                             |

---

## 🗃️ Database Design

### PostgreSQL — Core Tables

```sql
-- Master song registry (all sources)
songs (song_id PK, title, artist, album, source, duration_ms,
       file_path, genre, danceability, energy, valence, tempo,
       acousticness, instrumentalness, speechiness, mfcc_vector JSONB)

-- Full listening history with behavioral signals
listening_history (id, song_id FK, played_at, play_duration_ms,
                   song_duration_ms, completion_pct, skipped BOOL,
                   skip_time_ms, source, session_id)

-- Session groupings (>30 min gap = new session)
sessions (session_id PK, started_at, ended_at, dominant_genre,
          avg_energy, song_count, skip_rate)

-- Bandit agent state — persisted across restarts
bandit_state (song_id PK, A_matrix JSONB, b_vector JSONB,
              play_count, skip_count, last_updated)

-- All generated recommendations + outcome tracking
recommendations (id, rec_type, song_id FK, recommended_at,
                 was_played BOOL, user_rating INT)
```

---

## 🛠️ Tech Stack

| Layer             | Technology                              |
|-------------------|-----------------------------------------|
| Language          | Python 3.11+                            |
| Data — Playlists  | Custom M3U parser                       |
| Data — YT Music   | `ytmusicapi`                            |
| Data — Local      | `librosa`, `mutagen`, `ffmpeg`          |
| Genre Classifier  | `scikit-learn` XGBoost / `PyTorch`      |
| Recommender       | `implicit`, `scikit-learn`              |
| Sequential Model  | `PyTorch`                               |
| Bandit Agent      | Custom NumPy / `vowpalwabbit`           |
| Clustering        | `umap-learn`, `hdbscan`                 |
| Database          | PostgreSQL 15                           |
| ORM               | SQLAlchemy + Alembic (migrations)       |
| Backend           | FastAPI + Uvicorn                       |
| Scheduler         | APScheduler                             |
| Dashboard         | Streamlit                               |
| Notifications     | `python-telegram-bot`                   |
| Containerization  | Docker + Docker Compose                 |
| Env Management    | `python-dotenv`                         |
| Testing           | `pytest`                                |
| Linting           | `ruff`, `black`                         |

---

## 📁 Repository Structure

```
VibeFlow/
├── PLANNING.md
├── TASKS.md
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── requirements.txt
│
├── data_collection/
│   ├── __init__.py
│   ├── spotify_client.py       # OAuth2 + history + audio features
│   ├── ytmusic_client.py       # ytmusicapi wrapper
│   ├── local_scanner.py        # Walk dir, extract librosa features
│   └── ingestion_pipeline.py  # Unified → DB writer
│
├── models/
│   ├── __init__.py
│   ├── genre_classifier/
│   │   ├── train.py
│   │   ├── predict.py
│   │   └── saved/             # Serialized model artifacts
│   ├── content_based.py
│   ├── collaborative.py
│   ├── sequential.py
│   ├── bandit/
│   │   ├── linucb.py          # LinUCB core implementation
│   │   ├── context_builder.py # Feature vector construction
│   │   └── session_tracker.py # Active session state manager
│   └── weekend_playlist.py
│
├── api/
│   ├── __init__.py
│   ├── main.py                # FastAPI app entry point
│   ├── routers/
│   │   ├── recommend.py       # /recommend/* endpoints
│   │   ├── session.py         # /session/* endpoints
│   │   └── library.py        # /library/* endpoints
│   └── scheduler.py          # APScheduler job definitions
│
├── db/
│   ├── __init__.py
│   ├── models.py             # SQLAlchemy ORM models
│   ├── schema.sql            # Raw SQL reference
│   └── migrations/           # Alembic migration files
│
├── dashboard/
│   └── app.py                # Streamlit UI
│
├── bot/
│   └── telegram_bot.py       # Telegram push notification bot
│
└── tests/
    ├── test_bandit.py
    ├── test_recommender.py
    └── test_ingestion.py
```

---

## ⚠️ Known Constraints & Mitigations

| Constraint                              | Mitigation Strategy                                    |
|-----------------------------------------|--------------------------------------------------------|
| YT Music has no official API            | Use `ytmusicapi` (unofficial, stable)                  |
| Local songs missing Spotify ID          | Use `librosa` features; skip Spotify lookup            |
| Bandit needs warm-up period             | Pre-seed with content-based scores (cold start)        |
| ALS needs interaction volume            | Start content-based; switch to hybrid at 200+ logs     |
| Spotify rate limits (30 req/s)          | Cache responses; poll max once per hour                |
| Skip intent is ambiguous                | Time-threshold bucketing (<15s / 15–40s / >40s)        |
| GTZAN only has 10 genre classes         | Map to 6 broad buckets for v1.0 accuracy               |

---

## 🔭 Future Roadmap (v2.0+)

- [ ] Mood detection from device motion/time patterns
- [ ] NLP-based lyric sentiment as additional feature
- [ ] Multi-user support with shared taste graphs
- [ ] Mobile app (React Native) with embedded player
- [ ] LLM-powered natural language playlist requests ("Play something chill for a Sunday morning")
- [ ] Integration with Last.fm scrobbling