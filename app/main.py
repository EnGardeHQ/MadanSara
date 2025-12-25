"""Madan Sara FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import logging

from app.routers import outreach, conversion, ab_tests, responses, website, social, integrations
from app.core.engarde_db import engine, Base, check_db_connection, get_db_stats
from app.core.zerodb_integration import get_zerodb
from app.core.service_mesh import get_service_mesh

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application readiness flag
app_ready = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan handler for startup/shutdown."""
    global app_ready
    logger.info("Starting Madan Sara microservice...")

    # Check database connection (non-blocking)
    try:
        db_healthy = check_db_connection()
        if db_healthy:
            logger.info("✓ Database connection established")
        else:
            logger.warning("✗ Database connection failed - continuing anyway")
    except Exception as e:
        logger.warning(f"✗ Database check failed: {e} - continuing anyway")

    # Initialize service mesh
    try:
        mesh = get_service_mesh()
        logger.info("✓ Service mesh initialized")
    except Exception as e:
        logger.warning(f"Service mesh initialization failed: {e}")

    # Initialize ZeroDB client
    try:
        zerodb = get_zerodb()
        logger.info("✓ ZeroDB client initialized")
    except Exception as e:
        logger.warning(f"ZeroDB initialization failed: {e}")

    app_ready = True
    logger.info("Madan Sara microservice ready")

    yield

    logger.info("Shutting down Madan Sara microservice...")

app = FastAPI(
    title="Madan Sara API",
    description="Unified audience conversion intelligence layer for En Garde",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(outreach.router, prefix="/api/v1/outreach", tags=["Outreach"])
app.include_router(conversion.router, prefix="/api/v1/conversion", tags=["Conversion"])
app.include_router(ab_tests.router, prefix="/api/v1/ab-tests", tags=["A/B Testing"])
app.include_router(responses.router, prefix="/api/v1/responses", tags=["Responses"])
app.include_router(website.router, prefix="/api/v1/website", tags=["Website"])
app.include_router(social.router, prefix="/api/v1/social", tags=["Social"])
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["Integrations"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Madan Sara API",
        "version": "0.1.0",
        "description": "Unified audience conversion intelligence layer",
        "status": "operational",
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response


@app.get("/health", tags=["Health"])
async def health_check():
    """Enhanced health check endpoint."""
    # Check database
    db_healthy = check_db_connection()

    # Get database stats
    db_stats = {}
    try:
        db_stats = get_db_stats()
    except Exception as e:
        logger.error(f"Failed to get DB stats: {e}")

    # Check service mesh
    mesh = get_service_mesh()
    service_status = mesh.get_service_status()

    health_status = {
        "status": "healthy" if db_healthy else "degraded",
        "service": "madan-sara",
        "version": "0.1.0",
        "components": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "pool_stats": db_stats,
            },
            "service_mesh": {
                "status": "healthy",
                "services": service_status,
            },
            "zerodb": {
                "status": "healthy",
                "configured": bool(os.getenv("ZERODB_URL")),
            }
        }
    }

    return health_status


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Kubernetes readiness probe."""
    db_healthy = check_db_connection()
    return {
        "ready": db_healthy,
        "service": "madan-sara",
    }


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Kubernetes liveness probe."""
    return {
        "alive": True,
        "service": "madan-sara",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8002))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
