from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class SongFeature(SQLModel, table=True):
    __tablename__ = "song_features"
    
    song_id: str = Field(primary_key=True, foreign_key="songs.id")
    mfcc_vector: str  # JSON array
    chroma_vector: str  # JSON array
    contrast_vector: str  # JSON array
    tempo: float
    energy: float
    zcr: float
    valence_proxy: float
    full_vector: str  # JSON array
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
