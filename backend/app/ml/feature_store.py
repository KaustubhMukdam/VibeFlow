from typing import List, Optional
from sqlmodel import Session, select
from app.models.song_feature import SongFeature
from app.models.song import Song

class FeatureStore:
    def __init__(self, session: Session):
        self.session = session
        
    def save_features(self, song_id: str, features_dict: dict) -> SongFeature:
        existing = self.session.get(SongFeature, song_id)
        
        if existing:
            for key, value in features_dict.items():
                setattr(existing, key, value)
            song_feature = existing
        else:
            song_feature = SongFeature(song_id=song_id, **features_dict)
            self.session.add(song_feature)
            
        self.session.commit()
        self.session.refresh(song_feature)
        return song_feature

    def has_features(self, song_id: str) -> bool:
        return self.session.get(SongFeature, song_id) is not None

    def get_all_features(self) -> List[SongFeature]:
        return self.session.exec(select(SongFeature)).all()
