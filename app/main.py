"""
AutoDocs AI - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import close_db
from app.api import auth, users, workspaces, datasources, templates, jobs, outputs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    yield
    # Shutdown
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Automated Data Processing + Template Generation Platform",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# Custom validation error handler to log details
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import logging
    logger = logging.getLogger("uvicorn.error")
    logger.error(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["Data Sources"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(outputs.router, prefix="/api/outputs", tags=["Outputs"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return JSONResponse(
        content={
            "message": f"Welcome to {settings.app_name}",
            "docs": "/api/docs",
            "health": "/health",
        }
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns service status and basic info.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env,
    }


@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """API health check with more details."""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Add actual DB check
        "redis": "connected",  # TODO: Add actual Redis check
        "storage": "connected",  # TODO: Add actual S3 check
    }
