import logging
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from app.security.auth import require_bearer
from app.tools.gmail import GmailAdapter
from app.tools.weather import WeatherAdapter
from app.tools.vdb import VDBAdapter
from app.schemas.models import (
    GmailSummaryRequest,
    WeatherRequest,
    VDBQueryRequest,
    VDBDocumentsResponse,
    VDBIngestResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_gmail = GmailAdapter()
_weather = WeatherAdapter()
_vdb = VDBAdapter()

@router.post("/gmail/summary")
async def gmail_summary(req: GmailSummaryRequest, user=Depends(require_bearer)):
    try:
        emails = _gmail.list_recent(limit=req.limit, query=req.filter)
        return {"emails": emails, "count": len(emails)}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/weather/current")
async def weather_current(req: WeatherRequest, user=Depends(require_bearer)):
    return _weather.current(city=req.city, lat=req.lat, lon=req.lon)

@router.post("/vdb/query")
async def vdb_query(req: VDBQueryRequest, user=Depends(require_bearer)):
    return {"results": _vdb.query(req.query, req.top_k)}

@router.post("/vdb/ingest", response_model=VDBIngestResponse)
async def vdb_ingest(
    file: UploadFile = File(...),
    user=Depends(require_bearer),
):
    try:
        file_bytes = await file.read()
        result = _vdb.ingest_file(file.filename, file_bytes)
        return {"ok": True, **result}
    except ValueError as exc:
        logger.warning("Ingestion rejected for %s: %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected ingestion failure for %s", file.filename)
        raise HTTPException(status_code=500, detail="Failed to ingest document") from exc


@router.get("/vdb/documents", response_model=VDBDocumentsResponse)
async def vdb_list_documents(user=Depends(require_bearer)):
    documents = _vdb.list_documents()
    return {"documents": documents}


@router.delete("/vdb/document/{doc_id}")
async def vdb_delete_document(doc_id: str, user=Depends(require_bearer)):
    deleted = _vdb.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True, "doc_id": doc_id}
