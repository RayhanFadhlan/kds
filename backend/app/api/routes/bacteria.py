from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api import deps
from app.models.bacteria import Bacteria
from app.schemas.bacteria import BacteriaCreate, BacteriaResponse, BacteriaUpdate
from app.core.response import success_response, error_response, paginated_response

router = APIRouter()

@router.get("/")
def get_bacteria(
    db: Session = Depends(deps.get_db_dependency),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_pathogen: Optional[bool] = None,
    name: Optional[str] = None,
    gram_stain: Optional[str] = None,
    phylum: Optional[str] = None
) -> Any:
    query = db.query(Bacteria)

    if is_pathogen is not None:
        query = query.filter(Bacteria.is_pathogen == is_pathogen)

    if name:
        query = query.filter(Bacteria.name.ilike(f"%{name}%"))

    if gram_stain:
        query = query.filter(Bacteria.gram_stain == gram_stain)

    if phylum:
        query = query.filter(Bacteria.phylum == phylum)

    total_items = query.count()

    skip = (page - 1) * page_size
    bacteria = query.offset(skip).limit(page_size).all()

    bacteria_data = [
        BacteriaResponse.from_orm(b)
        for b in bacteria
    ]

    return paginated_response(
        data=bacteria_data,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Bacteria retrieved successfully"
    )


@router.get("/{bacteria_id}")
def get_bacteria_by_id(
    bacteria_id: str,
    db: Session = Depends(deps.get_db_dependency)
) -> Any:
    bacteria = db.query(Bacteria).filter(Bacteria.bacteria_id == bacteria_id).first()

    if not bacteria:
        return error_response(
            message=f"Bacteria with ID {bacteria_id} not found",
            status_code=404
        )

    bacteria_data = BacteriaResponse.from_orm(bacteria)
    return success_response(
        data=bacteria_data,
        message=f"Bacteria {bacteria_id} retrieved successfully"
    )


@router.post("/")
def create_bacteria(
    *,
    db: Session = Depends(deps.get_db_dependency),
    bacteria_in: BacteriaCreate
) -> Any:
    existing = db.query(Bacteria).filter(Bacteria.bacteria_id == bacteria_in.bacteria_id).first()
    if existing:
        return error_response(
            message=f"Bacteria with ID {bacteria_in.bacteria_id} already exists",
            status_code=400
        )

    bacteria = Bacteria(**bacteria_in.dict())
    db.add(bacteria)
    db.commit()
    db.refresh(bacteria)

    bacteria_data = BacteriaResponse.from_orm(bacteria)
    return success_response(
        data=bacteria_data,
        message="Bacteria created successfully",
        status_code=201
    )


@router.put("/{bacteria_id}")
def update_bacteria(
    *,
    db: Session = Depends(deps.get_db_dependency),
    bacteria_id: str,
    bacteria_in: BacteriaUpdate
) -> Any:
    bacteria = db.query(Bacteria).filter(Bacteria.bacteria_id == bacteria_id).first()
    if not bacteria:
        return error_response(
            message=f"Bacteria with ID {bacteria_id} not found",
            status_code=404
        )

    update_data = bacteria_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bacteria, field, value)

    db.add(bacteria)
    db.commit()
    db.refresh(bacteria)

    bacteria_data = BacteriaResponse.from_orm(bacteria)
    return success_response(
        data=bacteria_data,
        message=f"Bacteria {bacteria_id} updated successfully"
    )


@router.delete("/{bacteria_id}")
def delete_bacteria(
    *,
    db: Session = Depends(deps.get_db_dependency),
    bacteria_id: str
) -> Any:
    bacteria = db.query(Bacteria).filter(Bacteria.bacteria_id == bacteria_id).first()
    if not bacteria:
        return error_response(
            message=f"Bacteria with ID {bacteria_id} not found",
            status_code=404
        )

    db.delete(bacteria)
    db.commit()

    return success_response(
        message=f"Bacteria {bacteria_id} deleted successfully"
    )


@router.get("/stats/counts")
def get_bacteria_stats(
    db: Session = Depends(deps.get_db_dependency)
) -> Any:
    total_count = db.query(func.count(Bacteria.id)).scalar()
    pathogen_count = db.query(func.count(Bacteria.id)).filter(Bacteria.is_pathogen == True).scalar()
    non_pathogen_count = db.query(func.count(Bacteria.id)).filter(Bacteria.is_pathogen == False).scalar()

    gram_positive = db.query(func.count(Bacteria.id)).filter(Bacteria.gram_stain == "Positive").scalar()
    gram_negative = db.query(func.count(Bacteria.id)).filter(Bacteria.gram_stain == "Negative").scalar()

    stats_data = {
        "total": total_count,
        "pathogenic": pathogen_count,
        "non_pathogenic": non_pathogen_count,
        "gram_positive": gram_positive,
        "gram_negative": gram_negative
    }

    return success_response(
        data=stats_data,
        message="Bacteria statistics retrieved successfully"
    )
