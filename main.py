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
    """Lifespan event handler: Pre-load the OSM graph at startup."""
    try:
        from services.routing import load_graph
        load_graph()
    except Exception as exc:  # pragma: no cover
        logger.warning("startup: graph preload failed: %s", exc)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hyperlocal On-Demand Blue-Collar Services API (RepairBuddy)",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS middleware for React frontend (localhost:5173)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
if isinstance(settings.CORS_ORIGINS, list):
    for o in settings.CORS_ORIGINS:
        if o not in origins:
            origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Status code constant to avoid deprecation warnings across Starlette versions
UNPROCESSABLE_CODE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


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
