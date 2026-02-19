"""
PharmaGuard Backend — FastAPI application entry point.

Primary color: #1E3A8A

Routes:
  POST /api/v1/analyze   → Upload VCF + run full pipeline → return results
  GET  /api/v1/results/{patient_id} → Fetch results by patient ID or code
  GET  /api/v1/supported-drugs      → List supported drugs
  GET  /api/v1/health               → Health check
"""
import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routers import analyze, results, meta

logger = logging.getLogger(__name__)

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
    # 1. Init database tables
    await init_db()

    # 2. Ingest CPIC guidelines into ChromaDB for RAG (non-blocking background task)
    asyncio.create_task(_run_cpic_ingestion())


async def _run_cpic_ingestion():
    """
    Background task: fetch CPIC data from the live API, embed it, and
    upsert into ChromaDB.  Errors are logged but never crash the server.
    """
    try:
        from app.services.cpic_ingestion import ingest_cpic_guidelines
        await ingest_cpic_guidelines()
    except Exception as exc:
        logger.error("CPIC RAG ingestion failed (non-fatal): %s", exc)


# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

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
            "routes": {
                "analyze": "POST /api/v1/analyze  (multipart/form-data: vcf_file, patient_code, drugs, concurrent_medications)",
                "results": "GET  /api/v1/results/{patient_id}",
                "supported_drugs": "GET /api/v1/supported-drugs",
                "health": "GET /api/v1/health",
            },
        },
        "error": None,
    }
