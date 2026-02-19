"""
PharmaGuard Backend — FastAPI application entry point.

Primary color: #1E3A8A
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routers import upload, analyze, results, meta

app = FastAPI(
    title="PharmaGuard API",
    description="Pharmacogenomic Risk Prediction System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "error": str(exc)},
    )


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    await init_db()


# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(upload.router, prefix=PREFIX, tags=["Upload"])
app.include_router(analyze.router, prefix=PREFIX, tags=["Analyze"])
app.include_router(results.router, prefix=PREFIX, tags=["Results"])
app.include_router(meta.router, prefix=PREFIX, tags=["Meta"])


# ── Root ─────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "success": True,
        "data": {
            "name": "PharmaGuard API",
            "version": "1.0.0",
            "docs": "/docs",
        },
        "error": None,
    }
