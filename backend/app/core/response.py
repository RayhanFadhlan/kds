from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar('T')

class PaginationMeta(BaseModel):
    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_previous: bool
    has_next: bool

class StandardResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    meta: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

def success_response(
    data: Any = None,
    message: str = "Operation successful",
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data,
            "meta": meta,
            "error": None
        }
    )

def error_response(
    message: str = "An error occurred",
    error_detail: Any = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    error_info = {"detail": error_detail} if error_detail else None

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "data": None,
            "meta": None,
            "error": error_info
        }
    )

def paginated_response(
    data: List[Any],
    total_items: int,
    page: int,
    page_size: int,
    message: str = "Data retrieved successfully",
    additional_meta: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0

    pagination_meta = {
        "current_page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_previous": page > 1,
        "has_next": page < total_pages
    }

    meta = {**pagination_meta}
    if additional_meta:
        meta.update(additional_meta)

    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data,
            "meta": meta,
            "error": None
        }
    )
