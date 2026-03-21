# VibeFlow — TASKS.md
 
> Track all development tasks here. Move items across status as you work.
> Format: Checkbox · Task description · [Estimated effort]
 
---
 
## Status Legend
 
- `[ ]` = Not started
- `[~]` = In progress
- `[x]` = Done
- `[!]` = Blocked
 
---
 
## 🏁 PHASE 0 — Project Bootstrap
 
- [x] Initialize repo with folder structure from PLANNING.md `[30 min]`
- [x] Create `.gitignore` (Python, .env, __pycache__, model artifacts) `[10 min]`
- [x] Create `.env.example` with all required keys listed (no values) `[10 min]`
- [x] Write `docker-compose.yml` with PostgreSQL 15 service `[30 min]`
- [x] Add `requirements.txt` with all dependencies listed `[20 min]`
- [x] Create base `README.md` with project description + setup steps `[30 min]`
- [x] Set up Python virtual environment locally `[10 min]`
- [x] Verify PostgreSQL container starts and is accessible `[15 min]`
 
---
 
## 📡 PHASE 1 — Data Collection & Ingestion
 
### Pre-requisite: Transfer Music from Phone
- [ ] Connect phone via USB → File Transfer (MTP) mode `[10 min]`
- [ ] Copy Music folder from phone → `VibeFlow/music_library/` `[varies]`
- [ ] Install "Playlist Backup" app → export playlists as M3U `[15 min]`
- [ ] Copy M3U files → `VibeFlow/music_library/playlists/` `[5 min]`

### Database ORM
- [ ] Write SQLAlchemy ORM models for all 5 tables `[2 hr]`
- [ ] Set up Alembic for migrations `[1 hr]`
- [ ] Write and run initial migration `[30 min]`
- [ ] Write DB health check endpoint `[15 min]`

### Local Music Library (Primary Source)
- [ ] Write `local_scanner.py` to recursively walk music directory `[1 hr]`
- [ ] Extract metadata using `mutagen` (title, artist, album) `[1 hr]`
- [ ] Extract audio features using `librosa`:
  - [ ] MFCC (13 coefficients, mean per track) `[1 hr]`
  - [ ] Spectral Centroid, Rolloff, Bandwidth `[30 min]`
  - [ ] Chroma features `[30 min]`
  - [ ] Tempo + Beat strength `[30 min]`
  - [ ] RMS Energy `[15 min]`
- [ ] Compute MD5 hash as stable `song_id` for local files `[30 min]`
- [ ] Store all local songs in `songs` table with `source='local'` `[45 min]`
- [ ] Add POST `/library/scan` endpoint to trigger rescans `[45 min]`

### M3U Playlist Parser (New)
- [ ] Write `playlist_parser.py` to read M3U/M3U8 files `[1.5 hr]`
- [ ] Match M3U entries to songs already in DB by filename/title `[1 hr]`
- [ ] Store playlist structure in new `playlists` table `[1 hr]`
- [ ] Use playlist membership as additional implicit signal for recommender `[30 min]`

### YouTube Music (Secondary Source)
- [ ] Run `ytmusicapi browser` to generate `ytmusic_auth.json` `[30 min]`
- [ ] Fetch liked songs from YT Music `[30 min]`
- [ ] Fetch play history from YT Music `[45 min]`
- [ ] Fuzzy match YT songs → local songs using `rapidfuzz` `[2 hr]`
- [ ] For unmatched: store as `source='ytmusic_only'` `[30 min]`
- [ ] Store all YT Music data in unified tables `[1 hr]`

### Ingestion Pipeline
- [ ] Write `ingestion_pipeline.py`:
  - [ ] `upsert_songs()` — bulk insert/update with conflict handling `[1.5 hr]`
  - [ ] `insert_listening_history()` — deduplication on (song_id, played_at) `[1 hr]`
  - [ ] `run_local_ingestion()` — orchestrates local scan → DB `[1 hr]`
  - [ ] `run_ytmusic_ingestion()` — orchestrates YT Music → DB `[1 hr]`
- [ ] Write `run_ingestion.py` as CLI entry point `[30 min]`
- [ ] Verify: run ingestion, check DB counts `[30 min]`
 
---
 
## 🏷️ PHASE 2 — Genre Intelligence
 
- [ ] Download GTZAN dataset (1000 songs, 10 genres) `[30 min]`
- [ ] Write feature extraction script on GTZAN using `librosa` `[2 hr]`
- [ ] Train baseline XGBoost classifier on GTZAN features `[1 hr]`
- [ ] Evaluate accuracy — target >85% on test split `[30 min]`
- [ ] If accuracy <85%, build CNN on mel-spectrograms with PyTorch `[4 hr]`
- [ ] Map 10 GTZAN genres → 6 broad VibeFlow buckets: `[30 min]`
  - Pop · HipHop/Punjabi · Rock · Classical/Instrumental · Electronic · Other
- [ ] Run classifier on all 500–600 local songs `[1 hr]`
- [ ] Save genre label + confidence to `songs` table `[30 min]`
- [ ] Add `GET /library/genres` endpoint (genre distribution breakdown) `[30 min]`
- [ ] Add genre distribution pie chart in Streamlit dashboard `[1 hr]`
 
---
 
## 🔁 PHASE 3 — Long-Term Recommender
 
### Content-Based
 
- [ ] Build feature matrix: normalize all 13 audio features `[1 hr]`
- [ ] Implement cosine similarity recommender `[1 hr]`
- [ ] Write `get_similar_songs(song_id, top_n=10)` utility `[30 min]`
- [ ] Test: given a known song, verify top-10 are sensibly similar `[30 min]`
 
### Collaborative Filtering
 
- [ ] Build implicit feedback matrix from `listening_history` (weight = completion_pct; skip = 0 weight) `[2 hr]`
- [ ] Train ALS model using `implicit` library `[1 hr]`
- [ ] Implement `get_als_recommendations(user_id, top_n=20)` `[1 hr]`
- [ ] Serialize trained model to disk for reuse `[30 min]`
 
### Hybrid Blending
 
- [ ] Build score blending layer: `0.5 × content + 0.5 × ALS` (tune weights) `[1 hr]`
- [ ] Add fallback: if ALS has <200 interactions, use content-based only `[30 min]`
 
### Sequential Model
 
- [ ] Build session sequences from `listening_history` + `sessions` table `[2 hr]`
- [ ] Implement LSTM model in PyTorch (input: feature seq, output: next song) `[3 hr]`
- [ ] Train on historical sessions `[1 hr]`
- [ ] Integrate LSTM score into hybrid blend (`0.4 content + 0.3 ALS + 0.3 LSTM`) `[1 hr]`
 
### Daily Recommendation
 
- [ ] Implement `generate_daily_recommendation()` function `[1 hr]`
- [ ] Add APScheduler job: runs at 8:00 AM daily `[30 min]`
- [ ] Write result to `recommendations` table `[30 min]`
- [ ] Add `GET /recommend/daily` endpoint `[30 min]`
 
---
 
## ⚡ PHASE 4 — Contextual Bandit Agent (Real-Time)
 
### Session Tracking
 
- [ ] Implement `SessionTracker` class: `[2 hr]`
  - [ ] Groups songs by inactivity gap (>30 min = new session) `[1 hr]`
  - [ ] Tracks current session genre, energy, skip signals `[1 hr]`
  - [ ] Persists session to DB on close `[1 hr]`
 
### Context Builder
 
- [ ] Implement `build_context_vector(session)` function:
  - [ ] Genre embedding (one-hot over 6 VibeFlow genres) `[30 min]`
  - [ ] Skip rate of last 5 songs `[30 min]`
  - [ ] Average energy of session so far `[15 min]`
  - [ ] Hour of day (0–23, normalized) `[15 min]`
  - [ ] Day of week (0–6, normalized) `[15 min]`
  - [ ] Tempo variance of last 5 songs `[30 min]`
  - [ ] Completion rate of last 5 songs `[30 min]`
 
### LinUCB Implementation
 
- [ ] Implement `LinUCB` class in NumPy:
  - [ ] `__init__`: initialize A matrix and b vector per song/arm `[1 hr]`
  - [ ] `select_arm(context)`: UCB score + argmax `[1 hr]`
  - [ ] `update(arm, context, reward)`: online weight update `[1 hr]`
  - [ ] Unit test: verify reward causes expected weight shift `[30 min]`
- [ ] Implement bandit state persistence to `bandit_state` table `[1 hr]`
- [ ] Implement state reload on app startup `[30 min]`
- [ ] Cold start strategy: initialize new songs with content-based similarity score `[1 hr]`
 
### Feedback & Queue
 
- [ ] Implement skip signal detector: `[1 hr]`
  - `<15s = -1.0` · `15–40s = -0.5` · `>40s = +0.5` · `>80% = +1.0`
- [ ] Add `POST /session/feedback` endpoint (receives `song_id` + `play_duration`) `[1 hr]`
- [ ] Add `GET /session/next` endpoint (bandit selects next song) `[1 hr]`
- [ ] Implement queue manager: pre-fetches next 3 songs from bandit `[2 hr]`
 
---
 
## 🗓️ PHASE 5 — Weekend Playlist Generator
 
- [ ] Build weekly feature aggregator: collect all session vectors Mon–Fri `[1 hr]`
- [ ] Implement UMAP dimensionality reduction on weekly features `[1 hr]`
- [ ] Implement HDBSCAN clustering on UMAP output `[1 hr]`
- [ ] Implement proportional playlist sampler: aim for 25–30 songs across all clusters `[1 hr]`
- [ ] Write `generate_weekend_playlist()` function `[1 hr]`
- [ ] Add APScheduler job: runs Friday at 7:00 PM `[30 min]`
- [ ] Write result to `recommendations` table `[30 min]`
- [ ] Add `GET /recommend/weekend` endpoint `[30 min]`
 
---
 
## 🖥️ PHASE 6 — Dashboard & Notifications
 
### Streamlit Dashboard
 
- [ ] Set up base Streamlit app with sidebar navigation `[1 hr]`
- [ ] Page: **Today's Pick** — display daily song recommendation `[1 hr]`
- [ ] Page: **Weekend Playlist** — display current playlist as cards `[1 hr]`
- [ ] Page: **Taste Profile** — audio feature radar chart (energy, valence, etc.) `[2 hr]`
- [ ] Page: **Listening History** — table of recent sessions + skip heatmap `[2 hr]`
- [ ] Page: **Genre Breakdown** — pie chart of local library genres `[1 hr]`
- [ ] Add manual "Refresh Recommendation" button `[30 min]`
- [ ] Add manual "Regenerate Weekend Playlist" button `[30 min]`
 
### Telegram Bot
 
- [ ] Create Telegram Bot via BotFather, get API token `[15 min]`
- [ ] Implement daily 8 AM message: today's recommended song `[1 hr]`
- [ ] Implement Friday 7 PM message: weekend playlist as formatted list `[1 hr]`
- [ ] Add `/next` command: asks bandit for next song suggestion `[1 hr]`
- [ ] Add `/skip` command: sends skip signal to bandit `[1 hr]`
 
---
 
## 🐳 PHASE 7 — Containerization & Final Polish
 
- [ ] Write `Dockerfile` for FastAPI service `[1 hr]`
- [ ] Write `Dockerfile` for Streamlit service `[30 min]`
- [ ] Update `docker-compose.yml`:
  - [ ] PostgreSQL service with volume mount `[30 min]`
  - [ ] FastAPI service with `env_file` `[30 min]`
  - [ ] Streamlit service `[30 min]`
  - [ ] Telegram bot service `[30 min]`
- [ ] Add health checks to all services `[30 min]`
- [ ] Write `pytest` tests:
  - [ ] `test_linucb.py` — reward update correctness `[1 hr]`
  - [ ] `test_content_based.py` — cosine similarity sanity check `[30 min]`
  - [ ] `test_ingestion.py` — DB write/read roundtrip `[1 hr]`
- [ ] Set up `ruff` + `black` for linting `[30 min]`
- [ ] Update `README.md` with full setup guide + architecture diagram `[2 hr]`
- [ ] Record demo video for GitHub `[1 hr]`
 
---
 
## 📊 Effort Summary
 
| Phase                           | Estimated Time |
|---------------------------------|----------------|
| Phase 0 — Bootstrap             | ~2.5 hrs       |
| Phase 1 — Data Collection       | ~16 hrs        |
| Phase 2 — Genre Intelligence    | ~8 hrs         |
| Phase 3 — Long-Term Recommender | ~14 hrs        |
| Phase 4 — Contextual Bandit     | ~14 hrs        |
| Phase 5 — Weekend Playlist      | ~6 hrs         |
| Phase 6 — Dashboard + Bot       | ~12 hrs        |
| Phase 7 — Docker + Polish       | ~8 hrs         |
| **Total**                       | **~80 hrs**    |
 
--- 