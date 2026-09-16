import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, dashboards, dedup, exports, guests, hostels, pms, reports, tickets, users
from app.core.config import get_settings
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="HostelOps Ticketing API",
    version="1.0.0",
    description="Front-office-as-a-service ticketing system for multi-hostel operations.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(guests.router)
app.include_router(dedup.router)
app.include_router(hostels.router)
app.include_router(users.router)
app.include_router(dashboards.router)
app.include_router(exports.router)
app.include_router(pms.router)
app.include_router(reports.router)
