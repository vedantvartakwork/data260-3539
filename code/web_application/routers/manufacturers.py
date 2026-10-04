"""Protected CRUD endpoints for grocery-product manufacturers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from code.web_application.db import get_db
from code.web_application.models import Manufacturer, RecallNotice, User
from code.web_application.routers.api_auth import require_user
from code.web_application.schemas import (
    ManufacturerCreate,
    ManufacturerResponse,
    ManufacturerUpdate,
)


router = APIRouter(prefix="/api/v1/manufacturers", tags=["hw5-manufacturers"])


def get_or_404(db: Session, manufacturer_id: int) -> Manufacturer:
    row = db.get(Manufacturer, manufacturer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    return row


@router.post("", response_model=ManufacturerResponse, status_code=201)
def create_manufacturer(
    payload: ManufacturerCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> Manufacturer:
    row = Manufacturer(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Manufacturer contact email must be unique"
        ) from exc
    return row


@router.get("", response_model=list[ManufacturerResponse])
def list_manufacturers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> list[Manufacturer]:
    return list(
        db.scalars(select(Manufacturer).order_by(Manufacturer.id).offset(skip).limit(limit))
    )


@router.get("/{manufacturer_id}", response_model=ManufacturerResponse)
def get_manufacturer(
    manufacturer_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> Manufacturer:
    return get_or_404(db, manufacturer_id)


@router.put("/{manufacturer_id}", response_model=ManufacturerResponse)
def update_manufacturer(
    manufacturer_id: int,
    payload: ManufacturerUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> Manufacturer:
    row = get_or_404(db, manufacturer_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Manufacturer contact email must be unique"
        ) from exc
    return row


@router.delete("/{manufacturer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manufacturer(
    manufacturer_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> None:
    row = get_or_404(db, manufacturer_id)
    recall_count = db.scalar(
        select(func.count(RecallNotice.id)).where(
            RecallNotice.manufacturer_id == manufacturer_id
        )
    )
    if recall_count:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a manufacturer that still has recall notices",
        )
    db.delete(row)
    db.commit()
