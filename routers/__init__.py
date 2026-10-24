from routers.jobs import router as jobs_router
from routers.workers import router as workers_router
from routers.offers import router as offers_router
from routers.reviews import router as reviews_router
from routers.sos import router as sos_router

__all__ = [
    "jobs_router",
    "workers_router",
    "offers_router",
    "reviews_router",
    "sos_router"
]
