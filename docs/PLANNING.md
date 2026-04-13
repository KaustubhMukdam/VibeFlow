# PLANNING.md
## VibeFlow — Adaptive Local Music Player

**Version:** 1.0  
**Last Updated:** April 2026

---

## Project Vision

Build a personal, offline-first music player that learns your taste from your local library (500–600 songs) and actively improves what you hear — eliminating dumb shuffle, enabling genre-aware listening, and auto-generating playlists you'll actually want to hear.

This is not a clone of Spotify. It's a smarter version of the music player you already use — tuned entirely to you.

---

## Core Principles

**1. Offline First**  
No internet dependency post-setup. All ML inference, recommendations, and playlist generation happen locally. Your music data never leaves your device.

**2. Behavior Over Preference Forms**  
No "rate this song 1–5 stars" onboarding. VibeFlow learns entirely from what you do: plays, skips, replays, session length. The model improves silently in the background.

**3. Reactive, Not Intrusive**  
The app updates the queue intelligently (mood shift detection, etc.) but never interrupts playback or forces changes. The user is always in control.

**4. Progressive Enhancement**  
Phase 1 works as a solid music player even without the ML features. Each phase adds intelligence on top of a stable foundation.

---

## Scope

### In Scope (v1.0)
- Local audio playback (MP3, FLAC, M4A, WAV)
- Samsung Music `.m3u` playlist import
- One-time audio feature indexing (Librosa)
- Content-based song similarity (KNN)
- Behavior tracking (play/skip/replay logging)
- Online preference learning (River)
- Mood-shift detection (3 consecutive skips → re-rank queue)
- Daily picks generation (5–10 songs, every morning)
- Weekend playlist generator (20–30 songs, every Friday)
- Genre-aware shuffle mode
- Android (primary) + Desktop (secondary)

### Out of Scope (v1.0)
- Spotify / YouTube Music integration
- Cloud sync
- Social features
- Lyrics
- Music download
- iOS / macOS builds
- Voice control
- Mood detection via microphone

---

## Technical Direction

### Architecture Pattern
**Local client-backend.** Flutter app on Android communicates with a FastAPI ML backend running as a background service on the same device. No network calls leave the device.

### ML Approach
**Hybrid recommender: content-based + behavioral.**

- **Content-based (cold start):** Extract audio features (MFCCs, chroma, tempo, energy) from every song using Librosa. Use KNN cosine similarity to find similar songs. Works on day 1 with zero listening history.
- **Behavioral layer (warm start):** Log every play/skip/replay event. Use River (online ML) to update per-song preference weights incrementally — no full retraining needed.
- **Final ranking:** `score = content_similarity × behavior_weight`. Re-rank queue after each significant signal.

### Agent vs Model Decision
No full LLM agent needed. Use a **lightweight rule-triggered inference loop**:
- Rule: 3 consecutive skips → trigger mood-shift → re-rank queue with different energy/genre profile.
- Rule: Song played >80% → boost similar songs in queue.
- Rule: Friday 6PM → generate weekend playlist job.
- Rule: Every morning 7AM → generate daily picks.

This is computationally cheap, fully offline, and highly predictable — the right call for a personal app on a mobile device.

---

## Technology Choices Summary

| Layer | Choice | Key Reason |
|---|---|---|
| Frontend | Flutter | Android + Desktop, `just_audio`, `on_audio_query` |
| Backend | FastAPI | Async, lightweight, you know it |
| Audio ML | Librosa | Industry standard for feature extraction |
| Similarity | Scikit-learn KNN | Simple, accurate, no GPU needed |
| Online learning | River | Incremental updates without retraining |
| Scheduling | APScheduler | Lightweight, embedded in FastAPI |
| Database | SQLite via SQLModel | Zero config, local, sufficient for scale |
| State (Flutter) | Riverpod | Scalable async state for audio |

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Librosa indexing too slow on Android | Medium | Run as background job, show progress UI; consider pre-indexing on desktop |
| FastAPI backend startup latency on Android | Medium | Start backend service on app launch, show loading state |
| `.m3u` import failures (encoding/path issues) | Low-Medium | Robust parser with fallback + user error messages |
| Behavior model overfits to a single mood | Low | Add diversity constraint in ranking (min 20% non-dominant genre) |
| SQLite contention (Flutter + Python on same file) | Low | Use WAL mode; Flutter writes to separate behavior DB, Python reads/merges |
| Cold start bad recommendations | Low | Audio features handle this well for day 1; improves fast |

---

## Development Phases Overview

| Phase | Focus | Duration (Est.) |
|---|---|---|
| Phase 1 | Music player core (Flutter) | 2–3 weeks |
| Phase 2 | Audio indexing pipeline (FastAPI + Librosa) | 1–2 weeks |
| Phase 3 | Content-based recommender | 1 week |
| Phase 4 | Behavior tracking + online learning | 1–2 weeks |
| Phase 5 | Daily picks + weekend playlist + scheduler | 1 week |
| Phase 6 | Polish, testing, optimization | 1–2 weeks |

**Total estimate:** 7–11 weeks solo, depending on pace.

---

## Success Criteria for v1.0

- [ ] Plays all local audio formats without crashes
- [ ] Imports `.m3u` from Samsung Music correctly
- [ ] Indexes 600 songs in under 3 minutes
- [ ] Recommendations have >60% acceptance rate (songs played >50%) by week 3
- [ ] Weekend playlist generation works reliably every Friday
- [ ] App runs fully offline
- [ ] No battery drain issues from background backend service
