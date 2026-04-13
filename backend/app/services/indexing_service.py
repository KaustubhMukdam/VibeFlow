import os
import uuid
import datetime
import threading
from typing import List, Dict
from sqlmodel import Session, select
from app.db.database import engine
from app.models.song import Song
from app.ml.audio_analyzer import AudioAnalyzer
from app.ml.feature_store import FeatureStore

# In-memory status 
_status = {
    "total": 0,
    "completed": 0,
    "current_file": None,
    "is_running": False
}

class IndexingService:
    def __init__(self):
        self.analyzer = AudioAnalyzer()

    def get_status(self) -> dict:
        return _status.copy()

    def index_single(self, file_path: str) -> dict:
        if not os.path.exists(file_path):
            return {"error": "File not found"}
            
        with Session(engine) as session:
            store = FeatureStore(session)
            
            # Upsert song metadata if not exist
            # Uses hash of path temporarily if ID not provided
            song = session.exec(select(Song).where(Song.file_path == file_path)).first()
            if not song:
                song_id = uuid.uuid4().hex
                song = Song(
                    id=song_id,
                    title=os.path.basename(file_path),
                    file_path=file_path
                )
                session.add(song)
                session.commit()
            
            if store.has_features(song.id):
                return {"song_id": song.id, "features_extracted": False, "message": "Already indexed"}
                
            try:
                features = self.analyzer.analyze(file_path)
                
                # Rule based genre tag (Mocked for now, enhance later)
                if features['energy'] > 0.15 and features['tempo'] > 110:
                    genre = "Energetic"
                else:
                    genre = "Calm"
                
                song.genre_tag = genre
                song.indexed_at = datetime.datetime.utcnow()
                session.add(song)
                
                store.save_features(song.id, features)
                return {"song_id": song.id, "features_extracted": True}
            except Exception as e:
                return {"song_id": song.id, "features_extracted": False, "error": str(e)}

    def start_indexing(self, file_paths: List[str]):
        global _status
        if _status["is_running"]:
            return {"message": "Job already running"}
            
        _status["total"] = len(file_paths)
        _status["completed"] = 0
        _status["is_running"] = True
        
        thread = threading.Thread(target=self._process_batch, args=(file_paths,))
        thread.start()
        
        return {"message": "Indexing started in background"}

    def _process_batch(self, file_paths: List[str]):
        global _status
        
        for path in file_paths:
            _status["current_file"] = path
            
            try:
                self.index_single(path)
            except Exception as e:
                print(f"Failed indexing {path}: {e}")
                
            _status["completed"] += 1
            
        _status["is_running"] = False
        _status["current_file"] = None
