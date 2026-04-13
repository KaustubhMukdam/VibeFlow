# TASKS.md
## VibeFlow — Adaptive Local Music Player

**Version:** 1.0  
**Last Updated:** April 2026  
**Legend:** `[ ]` To Do | `[~]` In Progress | `[x]` Done | `[!]` Blocked

---

## Phase 1 — Music Player Core (Flutter)

**Goal:** A fully functional local music player. No ML yet. Just plays music reliably.

### 1.1 Project Setup
- [x] Initialize Flutter project (`flutter create vibeflow`)
- [x] Add dependencies to `pubspec.yaml`: `just_audio`, `audio_service`, `on_audio_query`, `riverpod`, `go_router`, `dio`, `sqflite`, `flutter_animate`, `phosphor_flutter`
- [x] Set up folder structure as per `FOLDER_STRUCTURE.md`
- [x] Configure Android permissions in `AndroidManifest.xml` (READ_EXTERNAL_STORAGE, FOREGROUND_SERVICE, WAKE_LOCK)
- [x] Set up Material 3 theme with dark color scheme

### 1.2 Local Library
- [x] Implement `AudioQueryService` using `on_audio_query` to fetch all device songs
- [x] Build `Song` data model (id, title, artist, album, filePath, duration, albumArt)
- [x] Implement `SongRepository` with local DB (sqflite)
- [x] Build `LibraryScreen` — song list with album art, title, artist, duration
- [x] Add tab bar: All Songs | Albums | Artists | Playlists
- [x] Add genre filter chips (Punjabi | Hindi | English | All)
- [x] Implement search across song/artist/album

### 1.3 Playlist Import
- [x] Write `.m3u` parser (`m3u_parser.dart`) — handle both relative and absolute paths
- [x] Build `PlaylistImportService` — file picker → parse → save to DB
- [ ] Test with actual Samsung Music `.m3u` exports
- [ ] Handle encoding edge cases (UTF-8 vs Windows-1252)

### 1.4 Audio Playback Engine
- [x] Set up `AudioHandler` extending `audio_service` `BaseAudioHandler`
- [x] Implement `AudioPlayerManager` wrapping `just_audio` `AudioPlayer`
- [x] Connect audio handler to `just_audio` for local file playback
- [x] Implement: play, pause, skip next, skip previous, seek, set volume
- [x] Enable background playback (foreground service on Android)
- [x] Set up lock screen / notification controls (title, artist, art, play/skip buttons)

### 1.5 Queue Manager
- [x] Build `QueueManager` — ordered list of songs with position tracking
- [x] Implement shuffle (Fisher-Yates) and un-shuffle
- [x] Implement repeat modes: off / repeat one / repeat all
- [x] Add "Add to queue" and "Play next" actions

### 1.6 Now Playing Screen
- [x] Build `NowPlayingScreen` with full-screen blurred album art background
- [x] Album art widget with rounded corners and glow shadow
- [x] Custom seek bar (progress scrubber with elapsed / total time labels)
- [x] Playback control row (shuffle, prev, play/pause, next, repeat)
- [x] Secondary action row (heart, add to playlist, queue)
- [x] Animated waveform widget (32 bars, orange, interpolated)
- [x] "Up Next" bottom peek with drag-up queue sheet
- [x] Shared element hero transition from library list to now playing

### 1.7 Mini Player
- [x] Build persistent `MiniPlayer` widget (bottom bar)
- [x] Show: album art, title, artist, play/pause, skip
- [x] Tap to expand to NowPlayingScreen
- [x] Animate in on first song play, persist across all screens

### 1.8 Home Screen
- [x] Build `HomeScreen` skeleton with greeting + time context
- [x] "Recently Played" section (2-column album art grid)
- [x] Placeholder sections for Daily Picks and Weekend Playlist (Phase 5)
- [x] Riverpod providers: `playerProvider`, `libraryProvider`, `queueProvider`

**Phase 1 Exit Criteria:** App plays any local song, imports a `.m3u` playlist, persists queue, works in background, shows mini player.

---

## Phase 2 — Audio Indexing Pipeline (FastAPI + Librosa)

**Goal:** Analyze every song's audio and store feature vectors in SQLite.

### 2.1 Backend Setup
- [ ] Initialize FastAPI project in `backend/`
- [ ] Configure `pyproject.toml` with Poetry
- [ ] Set up SQLModel + Alembic + SQLite
- [ ] Write initial Alembic migration: `songs`, `song_features`, `behavior_logs`, `sessions`, `playlists`, `preference_weights`
- [ ] Implement `GET /health` endpoint
- [ ] Set up structured logging (`logger.py`)

### 2.2 Audio Analyzer
- [ ] Implement `AudioAnalyzer` class in `ml/audio_analyzer.py`
  - [ ] Load audio file via librosa (handle MP3, FLAC, M4A via pydub conversion)
  - [ ] Extract: MFCCs (20 coefficients, mean + std), chroma (12 bins, mean), tempo (BPM), spectral contrast (7 bands), RMS energy, zero crossing rate
  - [ ] Normalize feature vector to unit length
  - [ ] Assign genre tag via rule-based classifier (language detection from filename/metadata + energy/tempo profile)
- [ ] Implement `FeatureStore` in `ml/feature_store.py` — CRUD for feature vectors in SQLite

### 2.3 Indexing API
- [ ] `POST /index/start` — accepts list of file paths, spawns background indexing task
- [ ] `GET /index/status` — returns: total, completed, current_file, eta_seconds
- [ ] `POST /index/single` — index one song (for newly added tracks)
- [ ] Implement idempotency: skip already-indexed songs unless forced
- [ ] Write `tests/test_indexing.py`

### 2.4 Flutter Integration
- [ ] Implement `IndexingApiClient` in Flutter (`datasources/remote/indexing_api.dart`)
- [ ] Build `IndexingScreen` — progress indicator, current song, stats
- [ ] Trigger indexing job on first launch (after library scan)
- [ ] Show indexing status in Settings screen

**Phase 2 Exit Criteria:** All 600 songs indexed with feature vectors in SQLite. Status visible in app.

---

## Phase 3 — Content-Based Recommender

**Goal:** Recommend similar songs based on audio features. Works with zero listening history.

### 3.1 Similarity Engine
- [ ] Implement `SimilarityEngine` in `ml/similarity_engine.py`
  - [ ] Load all feature vectors from SQLite into numpy array
  - [ ] Build KNN index (K=15, cosine metric, scikit-learn `NearestNeighbors`)
  - [ ] `get_similar(song_id, n=10)` → returns ranked list of song IDs
  - [ ] Cache KNN index in memory after first load
  - [ ] Rebuild index when new songs are indexed

### 3.2 Recommendation API
- [ ] `GET /recommend/similar?song_id=X&n=10` — returns similar songs
- [ ] `GET /recommend/queue?current_song_id=X&genre_context=punjabi&n=20` — builds a context-aware queue
- [ ] Implement genre context filtering (restrict candidates to genre before KNN)
- [ ] Write `tests/test_recommendations.py`

### 3.3 Flutter Integration
- [ ] Implement `RecommendationApiClient` in Flutter
- [ ] Update `QueueManager` — after a song starts playing, fetch next 10 recommendations and pre-load them
- [ ] Add "Similar Songs" section on now playing screen (horizontal scroll)
- [ ] Add genre context selector in shuffle mode

**Phase 3 Exit Criteria:** Queue is continuously populated with similar songs. Genre-aware shuffle works.

---

## Phase 4 — Behavior Tracking + Online Learning

**Goal:** Learn from play/skip signals and update recommendations in real time.

### 4.1 Behavior Tracker (Flutter)
- [ ] Implement `BehaviorTracker` in Flutter
  - [ ] Hook into `AudioHandler`: intercept play start, skip, replay events
  - [ ] Capture: song_id, event_type, skip_position_pct, session_id, timestamp
  - [ ] Write to local sqflite behavior table
  - [ ] Batch-sync to FastAPI backend every 30 seconds (or on app backgrounding)

### 4.2 Behavior API
- [ ] `POST /behavior/log` — accepts batch of behavior events
- [ ] `POST /behavior/session/end` — marks session end, stores dominant genre + avg energy

### 4.3 Behavior Learner (Online ML)
- [ ] Implement `BehaviorLearner` in `ml/behavior_learner.py`
  - [ ] Use River `SGDClassifier` or `LogisticRegression` (online learning)
  - [ ] Features: audio features of song + time of day + session energy context
  - [ ] Label: 1 = played >80%, 0 = skipped <20% (ignore in-between)
  - [ ] `update(song_id, label)` — incremental model update
  - [ ] `get_preference_score(song_id)` → float 0–1
- [ ] Persist model state to SQLite `preference_weights` table
- [ ] Write `tests/test_behavior.py`

### 4.4 Mood Shift Detection
- [ ] Implement `MoodDetector` in `services/mood_detector.py`
  - [ ] Rule: 3 consecutive skips within 60 seconds → mood shift event
  - [ ] On mood shift: compute new target energy/genre profile from last 10 non-skipped songs
  - [ ] Trigger queue re-rank via `RecommendationService`
- [ ] `POST /behavior/mood_shift` — Flutter calls this when 3 consecutive skips detected (client-side pre-detection)

### 4.5 Ranker Update
- [ ] Update `Ranker` in `ml/ranker.py`: `final_score = content_similarity × (1 + behavior_weight)`
- [ ] Add diversity constraint: ensure minimum 20% of recommended songs differ from dominant session genre
- [ ] Re-expose updated `GET /recommend/queue` with ranker integrated

**Phase 4 Exit Criteria:** Recommendations improve measurably over 2–3 listening sessions. Mood shift re-ranking works.

---

## Phase 5 — Daily Picks + Weekend Playlist + Scheduler

**Goal:** Auto-generate picks and playlists without user action.

### 5.1 Daily Picks Generator
- [ ] Implement `PlaylistService.generate_daily_picks()` in `services/playlist_service.py`
  - [ ] Candidates: songs not played in last 3 days, preference_weight > 0.4
  - [ ] Score by: preference weight × recency penalty × time-of-day energy match
  - [ ] Return top 8 songs
- [ ] `GET /playlist/daily` — returns today's picks (cached, regenerated if stale)
- [ ] Store in `daily_picks` table

### 5.2 Weekend Playlist Generator
- [ ] Implement `PlaylistService.generate_weekend_playlist()`
  - [ ] Pull last 7 days of behavior logs
  - [ ] Cluster session songs using KMeans (k=5) on audio features
  - [ ] Sample 5–6 songs per cluster (weighted by preference score)
  - [ ] Add 10% "discovery" songs — high audio similarity but never played
  - [ ] Return 25-song playlist
- [ ] `GET /playlist/weekend` — returns this week's playlist
- [ ] Write `tests/test_playlist_generation.py`

### 5.3 Scheduler
- [ ] Set up APScheduler in `tasks/scheduler.py`
  - [ ] Daily picks job: every day at 7:00 AM
  - [ ] Weekend playlist job: every Friday at 6:00 PM
- [ ] Start scheduler on FastAPI app startup

### 5.4 Flutter Integration
- [ ] Fetch and display Daily Picks on HomeScreen card strip
- [ ] Build `WeekendPlaylistScreen` — song list, genre distribution bar, regenerate + save buttons
- [ ] Local notification on Friday evening: "Your weekend playlist is ready"
- [ ] Save generated playlist to local DB, playable offline

**Phase 5 Exit Criteria:** Daily picks appear on home screen every morning. Weekend playlist appears on Fridays. Both are playable.

---

## Phase 6 — Polish, Testing, Optimization

### 6.1 Performance
- [ ] Profile Librosa indexing on Android — optimize if >3 min for 600 songs (consider chunked processing)
- [ ] Ensure FastAPI startup time < 3 seconds on Android
- [ ] Implement SQLite WAL mode to prevent read/write contention
- [ ] Lazy-load album art in list views (avoid memory spikes)

### 6.2 Testing
- [ ] Python: full test coverage for `indexing`, `recommendations`, `behavior`, `playlist` services
- [ ] Flutter: widget tests for `NowPlayingScreen`, `MiniPlayer`, `QueueManager`
- [ ] Integration: end-to-end test of full recommendation loop (index → play → skip → re-rank)
- [ ] Manual: test `.m3u` import with actual Samsung Music export

### 6.3 Error Handling & Edge Cases
- [ ] Handle missing audio files gracefully (file moved/deleted)
- [ ] Handle corrupted audio files in indexing pipeline (try/catch per file)
- [ ] Handle empty library state (onboarding prompt)
- [ ] Handle backend unreachable (fallback to random queue)

### 6.4 UX Polish
- [ ] Finalize all animations (shared element transitions, waveform, queue sheet spring physics)
- [ ] Empty state screens for all list views
- [ ] Settings screen: re-index library, reset behavior data, view indexing stats
- [ ] Onboarding flow (first launch: scan library → import playlists → start indexing)
- [ ] App icon + splash screen

### 6.5 Documentation
- [ ] Update README with setup instructions
- [ ] Document FastAPI endpoints in README or separate API_DOCS.md
- [ ] Add inline code comments for ML pipeline

**Phase 6 Exit Criteria:** App is stable, tested, and presentable. Ready for daily personal use.
