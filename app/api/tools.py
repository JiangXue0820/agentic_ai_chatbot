from fastapi import APIRouter, Depends
from app.security.auth import require_bearer
from app.tools.gmail import GmailAdapter
from app.tools.weather import WeatherAdapter
from app.tools.vdb import VDBAdapter
from app.schemas.models import GmailSummaryRequest, WeatherRequest, VDBQueryRequest, VDBIngestRequest

router = APIRouter()

_gmail = GmailAdapter()
_weather = WeatherAdapter()
_vdb = VDBAdapter()

@router.post("/gmail/summary")
async def gmail_summary(req: GmailSummaryRequest, user=Depends(require_bearer)):
    emails = _gmail.list_recent(limit=req.limit)
    return {"emails": emails}

@router.post("/weather/current")
async def weather_current(req: WeatherRequest, user=Depends(require_bearer)):
    return _weather.current(city=req.city, lat=req.lat, lon=req.lon)

@router.post("/vdb/query")
async def vdb_query(req: VDBQueryRequest, user=Depends(require_bearer)):
    return {"results": _vdb.query(req.query, req.top_k)}

@router.post("/vdb/ingest")
async def vdb_ingest(req: VDBIngestRequest, user=Depends(require_bearer)):
    _vdb.ingest_texts(req.items)
    return {"ingested": len(req.items)}
