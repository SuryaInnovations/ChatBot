"""
Health and Readiness check endpoints for monitoring, load balancers, and container probes.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from sqlalchemy import text

from db.session import get_db_session
from core.redis_client import redis_manager
from core.provider_status import get_provider_status
from core.providers import PROVIDER_REGISTRY
from api.schemas import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", summary="Liveness probe")
async def liveness():
    """Returns 200 OK immediately if the service process is alive."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready", response_model=HealthCheckResponse, summary="Readiness probe")
async def readiness():
    """
    Checks database connection, Redis connectivity, and configured AI providers.
    Returns status 200 if ready or 503 if critical dependencies are down.
    """
    db_status = {"healthy": False, "message": "untested"}
    redis_status = {"healthy": False, "message": "untested"}
    overall_healthy = True

    # 1. Test Database
    try:
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
            db_status = {"healthy": True, "message": "Connected and responsive"}
    except Exception as e:
        db_status = {"healthy": False, "message": str(e)}
        overall_healthy = False

    # 2. Test Redis
    try:
        client = await redis_manager.get_client()
        pong = await client.ping()
        redis_status = {"healthy": bool(pong), "message": "Connected" if pong else "No pong"}
    except Exception as e:
        redis_status = {"healthy": False, "message": str(e)}

    # 3. Check Providers
    providers_info = {}
    for code, adapter_cls in PROVIDER_REGISTRY.items():
        adapter = adapter_cls()
        is_cfg = adapter.is_configured()
        st_info = get_provider_status(code, is_cfg)
        providers_info[code] = {
            "name": adapter.name,
            "configured": is_cfg,
            "status": st_info.get("status"),
            "display": st_info.get("display")
        }

    status_str = "healthy" if overall_healthy else "degraded"
    http_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    response_data = HealthCheckResponse(
        status=status_str,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=db_status,
        redis=redis_status,
        providers=providers_info
    )

    return JSONResponse(status_code=http_code, content=response_data.model_dump())
