import logging
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings
from routers.jobs import router as jobs_router
from routers.workers import router as workers_router
from routers.offers import router as offers_router
from routers.reviews import router as reviews_router
from routers.sos import router as sos_router
from routers.reports import router as reports_router
from routers.admin import router as admin_router
from routers.route import router as route_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler: Pre-load the OSM graph and auto-seed if empty."""
    if settings.USE_MOCK_FIREBASE and getattr(settings, "AUTO_SEED", True):
        try:
            from seed import auto_seed_if_empty
            auto_seed_if_empty()
        except Exception as exc:  # pragma: no cover
            logger.warning("startup: auto-seed failed: %s", exc)

    try:
        from services.routing import load_graph
        load_graph()
    except Exception as exc:  # pragma: no cover
        logger.warning("startup: graph preload failed: %s", exc)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Repair Buddy",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS middleware for React frontend (localhost:5173) and production / preview origins
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
if isinstance(settings.CORS_ORIGINS, list):
    for o in settings.CORS_ORIGINS:
        if o not in origins:
            origins.append(o)

cors_kwargs = {
    "allow_origins": origins,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if getattr(settings, "CORS_ORIGIN_REGEX", None):
    cors_kwargs["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX

app.add_middleware(
    CORSMiddleware,
    **cors_kwargs,
)

# Status code constant to avoid deprecation warnings across Starlette versions
UNPROCESSABLE_CODE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


@app.middleware("http")
async def live_activity_logger(request: Request, call_next):
    """
    Prints high-visibility, human-readable terminal logs for every
    customer and worker action in real-time.
    """
    method = request.method
    path = request.url.path

    action_label = None
    if method == "POST" and path in ["/jobs", "/api/jobs"]:
        action_label = "📦 [CUSTOMER] Placed a New Job Request"
    elif method == "GET" and path in ["/workers/match", "/api/workers/match"]:
        action_label = "🔍 [MATCHING] Customer searching for nearby verified workers"
    elif method == "POST" and path in ["/workers/register", "/api/workers/register"]:
        action_label = "👷 [WORKER] New Worker Registered & Verified"
    elif method == "POST" and "/offers" in path and "/accept" in path:
        action_label = "🤝 [DEAL ACCEPTED] Offer Accepted! Booking Confirmed"
    elif method == "POST" and "/offers" in path and "/counter" in path:
        action_label = "💬 [NEGOTIATION] Counter-Offer Submitted"
    elif method == "POST" and path in ["/offers", "/api/offers"]:
        action_label = "💰 [OFFER SENT] New Price Proposal Sent"
    elif method == "POST" and "/start" in path:
        action_label = "🚀 [WORKER] Worker Started the Job (In Progress)"
    elif method == "POST" and "/complete" in path:
        action_label = "✅ [WORKER] Worker Completed the Job!"
    elif method == "POST" and path in ["/reviews", "/api/reviews"]:
        action_label = "⭐ [REVIEW] Customer Submitted a Rating & Review"
    elif method == "POST" and path in ["/sos", "/api/sos"]:
        action_label = "🚨 [SAFETY ALERT] Emergency SOS Triggered!"

    response = await call_next(request)

    if action_label:
        print(f"\n=======================================================")
        print(f"{action_label}")
        print(f"--> {method} {path} (HTTP {response.status_code})")
        print(f"=======================================================\n", flush=True)

    return response


# Exception handler to format validation errors cleanly as {"detail": "..."}
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    loc = " -> ".join([str(x) for x in first_error.get("loc", []) if x != "body"])
    msg = first_error.get("msg", "Invalid request body")
    detail_str = f"{loc}: {msg}" if loc else msg
    return JSONResponse(
        status_code=UNPROCESSABLE_CODE,
        content={"detail": detail_str}
    )


# System health check router mounted on both "" and "/api"
health_router = APIRouter(tags=["System"])


@health_router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "mock_mode": settings.USE_MOCK_FIREBASE,
        "transit_speed_kmh": settings.TRANSIT_SPEED_KMH
    }


# Include routers both at root level and under /api for full specification compatibility
for prefix in ["", "/api"]:
    app.include_router(health_router, prefix=prefix)
    app.include_router(jobs_router, prefix=prefix)
    app.include_router(workers_router, prefix=prefix)
    app.include_router(offers_router, prefix=prefix)
    app.include_router(reviews_router, prefix=prefix)
    app.include_router(sos_router, prefix=prefix)
    app.include_router(reports_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)
    app.include_router(route_router, prefix=prefix)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
