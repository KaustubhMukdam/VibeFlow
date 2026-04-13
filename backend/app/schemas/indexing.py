from pydantic import BaseModel
from typing import List, Optional

class IndexStartRequest(BaseModel):
    file_paths: List[str]

class IndexSingleRequest(BaseModel):
    file_path: str

class IndexStatusResponse(BaseModel):
    total: int
    completed: int
    current_file: Optional[str] = None
    eta_seconds: Optional[int] = None
    status: str
