from fastapi import APIRouter, Depends, HTTPException
from app.schemas.indexing import IndexStartRequest, IndexStatusResponse, IndexSingleRequest
from app.services.indexing_service import IndexingService

router = APIRouter()
service = IndexingService()

@router.post("/start")
def start_indexing(request: IndexStartRequest):
    status = service.get_status()
    if status.get("is_running"):
        raise HTTPException(status_code=400, detail="Indexing already in progress")
        
    res = service.start_indexing(request.file_paths)
    return res

@router.get("/status", response_model=IndexStatusResponse)
def get_indexing_status():
    status = service.get_status()
    
    # Calculate ETA (mocked approximation based on 2s per song)
    remaining = status["total"] - status["completed"]
    eta = remaining * 2 if status["is_running"] else 0
    
    return IndexStatusResponse(
        total=status["total"],
        completed=status["completed"],
        current_file=status["current_file"],
        eta_seconds=eta,
        status="running" if status["is_running"] else "idle"
    )

@router.post("/single")
def index_single(request: IndexSingleRequest):
    res = service.index_single(request.file_path)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res
