import logging
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import bacteria
from app.core.config import settings
from app.core.response import error_response, success_response
from app.db.session import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Bacteria Classification API using Machine Learning",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    bacteria.router,
    prefix=f"{settings.API_V1_STR}/bacteria",
    tags=["bacteria"]
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exc.errors():
        error_detail = {
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        }
        errors.append(error_detail)

    return error_response(
        message="Validation error",
        error_detail=errors,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return error_response(
        message=exc.detail,
        status_code=exc.status_code
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(f"Database error: {str(exc)}")
    return error_response(
        message="Database error occurred",
        error_detail=str(exc),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return error_response(
        message="Internal server error",
        error_detail=str(exc) if settings.ENVIRONMENT == "development" else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

@app.get("/")
def root() -> JSONResponse:
    return success_response(
        data={
            "api_name": settings.PROJECT_NAME,
            "version": "0.1.0",
            "documentation": "/docs",
            "environment": settings.ENVIRONMENT
        },
        message="Welcome to the Bacteria Classification API"
    )

@app.get("/healthcheck")
def healthcheck(db: Session = Depends(get_db)) -> JSONResponse:
    try:
        db.execute("SELECT 1")

        return success_response(
            data={
                "status": "healthy",
                "database": "connected",
                "environment": settings.ENVIRONMENT
            },
            message="Service is healthy"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return error_response(
            message="Health check failed",
            error_detail=str(e),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
