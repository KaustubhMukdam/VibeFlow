from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class Song(SQLModel, table=True):
    __tablename__ = "songs"
    
    id: str = Field(primary_key=True)
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    file_path: str = Field(unique=True, index=True)
    duration_ms: Optional[int] = None
    genre_tag: Optional[str] = None
    indexed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
