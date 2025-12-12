"""
Main FastAPI application entry point
"""

import logging
import os
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference  # type: ignore[import-untyped]
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db

logger = logging.getLogger("uvicorn.error")
access_logger = logging.getLogger("uvicorn.access")

# Debug: Log loaded API keys at startup
__num_of_api_keys__ = len(settings.api_keys)
logger.info(f"Total API keys: {__num_of_api_keys__}")
logger.info(f"Loaded API keys: {list(settings.api_keys.values()) if __num_of_api_keys__ > 0 else []}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Aurorah API Server...")
    # Skip init_db if SKIP_DB_INIT is set (for multi-worker deployments where
    # migrations are run separately before starting workers)
    if not os.getenv("SKIP_DB_INIT"):
        await init_db()
        logger.info("Database initialized")
    else:
        logger.info("Skipping database initialization (SKIP_DB_INIT is set)")
    yield
    # Shutdown
    logger.info("Shutting down Aurorah API Server...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)


# Configure OpenAPI security schemes
def custom_openapi_for_api_key_auth():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
            "description": "API Key in x-api-key header. <p>ex) x-api-key: ...your-api-key... </p>",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "API Key in Authorization: Bearer header. <p>ex) Authorization: Bearer ...your-api-key... </p>",
        },
    }

    # Apply security globally to all endpoints
    openapi_schema["security"] = [{"APIKeyHeader": []}, {"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi_for_api_key_auth

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_guard(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """
    Enforce API key authentication for API routes.
    Exempt health, docs, and auth endpoints.
    """
    __func__ = "api_key_guard"
    path = request.url.path

    # Exemptions
    exempt_paths = {
        "/",  # root health
        "/health",
        "/api/latest/docs",  # Scalar API reference
        f"{settings.API_V1_STR}/openapi.json",
        f"{settings.API_V1_STR}/docs",
        f"{settings.API_V1_STR}/redoc",
        f"{settings.API_V1_STR}/auth/login",
        f"{settings.API_V1_STR}/auth/register",
    }

    exempt_start_with_paths = {
        f"{settings.API_V1_STR}/mq/channels",
    }

    should_enforce = not (
        path in exempt_paths or any(path.startswith(start_with_path) for start_with_path in exempt_start_with_paths)
    )

    if should_enforce:
        # API key check (if configured)
        if settings.api_keys:
            api_key = request.headers.get("x-api-key")
            if not api_key:
                # Optional: support Authorization: Bearer <key>
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    api_key = auth_header.split(" ", 1)[1].strip()

            # Check if key exists and is enabled
            if not api_key or api_key not in settings.api_keys:
                logger.warning(f"[{__name__}:{__func__}] Access denied: Invalid or missing API key")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Access denied (Invalid or missing API key)"},
                )

            key_info = settings.api_keys[api_key]
            if not key_info["enabled"]:
                logger.warning(f"[{__name__}:{__func__}] Access denied: API key '{key_info['name']}' is disabled")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Access denied (API key is disabled)"},
                )

            # Store key info in request state for endpoint use:
            #   - Check key type for authorization (user vs admin)
            #   - Log which key made the request
            #   - Audit API key usage
            #
            # Example usage in endpoint:
            #   @app.get("/api/v1/admin/something")
            #   async def admin_endpoint(request: Request):
            #       key_info = request.state.api_key_info
            #       if key_info["type"] != "admin":
            #           raise HTTPException(403, "Admin access required")
            #       # ... rest of logic
            request.state.api_key_info = key_info

    return await call_next(request)


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "connected",
        }
    )


@app.get("/api/latest/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn

    #
    # Use '$ python -m app.main' on the root directory of the project for development
    # Use '$ uvicorn app.main:app --host 0.0.0.0 --port 33001 --reload' for production deployment
    #
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=33001,
        reload=True,
        log_level="debug",
    )
