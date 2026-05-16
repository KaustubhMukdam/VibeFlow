# Tasks — VibeFlow

## In progress

- [ ] Finalize MVP scope and success criteria
- [ ] Decide first recommendation baseline and first genre-tagging baseline
- [ ] Design event schema for play, skip, replay, and session tracking

## Up next

- [ ] Create project repository and folder structure
- [ ] Prepare Python environment and requirements file
- [ ] Build local song ingestion script
- [ ] Create sample SQLite schema for songs and listening_events
- [ ] Extract audio features from a small subset of 25 songs
- [ ] Evaluate whether metadata tags are usable or need auto-labeling
- [ ] Build baseline genre classifier or clustering pipeline
- [ ] Build simple content-based recommender using audio similarity
- [ ] Add daily top-5 recommendation endpoint
- [ ] Add weekend playlist generator with diversity rules

## Done

- [x] Project idea refined
- [x] Initial architecture direction chosen
- [x] Documentation plan prepared

## Blocked

- [ ] Need a clear source of labels for supervised genre classification
- [ ] Need a realistic way to capture playback behavior from phone for MVP

## Ideas / backlog

- Recommendation explanation panel: "Suggested because you liked recent Punjabi tracks"
- Mood clusters from embeddings instead of explicit mood labels
- Time-aware recommendation profiles
- Duplicate-song detection
- Playlist export as `.m3u`
