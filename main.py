from fastapi import FastAPI, Request, status
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

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hyperlocal On-Demand Blue-Collar Services API (RepairBuddy / KaamSetu)",
    version="1.1.0"
)


@app.on_event("startup")
def _preload_graph():
    """Pre-load the OSM graph at startup so the first request isn't slow."""
    try:
        from services.routing import load_graph
        load_graph()
    except Exception as exc:  # pragma: no cover
        import logging
        logging.getLogger(__name__).warning("startup: graph preload failed: %s", exc)

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


# Exception handler to format validation errors cleanly as {"detail": "..."}
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    loc = " -> ".join([str(x) for x in first_error.get("loc", []) if x != "body"])
    msg = first_error.get("msg", "Invalid request body")
    detail_str = f"{loc}: {msg}" if loc else msg
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail_str}
    )


# Health check endpoint
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "mock_mode": settings.USE_MOCK_FIREBASE,
        "transit_speed_kmh": settings.TRANSIT_SPEED_KMH
    }


# Include routers both at root level and under /api for full specification compatibility
for prefix in ["", "/api"]:
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
