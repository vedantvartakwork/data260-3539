"""Protected grocery-recall CRUD and N+1 demonstration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from code.web_application.db import get_db
from code.web_application.models import Manufacturer, RecallEvent, RecallNotice, User
from code.web_application.query_counter import count_sql_queries
from code.web_application.routers.api_auth import require_user
from code.web_application.schemas import (
    RecallCreate,
    RecallEventResponse,
    RecallListResponse,
    RecallResponse,
    RecallUpdate,
)


router = APIRouter(prefix="/api/v1/recalls", tags=["hw5-recalls"])


def serialize_recall(
    row: RecallNotice,
    events: list[RecallEvent] | None = None,
    *,
    include_manufacturer: bool = True,
) -> RecallResponse:
    event_rows = row.events if events is None else events
    return RecallResponse(
        id=row.id,
        product_name=row.product_name,
        recall_code=row.recall_code,
        units_affected=row.units_affected,
        manufacturer_id=row.manufacturer_id,
        brand_name=row.brand_name,
        submitter_email=row.submitter_email,
        category=row.category,
        recall_details=row.recall_details,
        terms_accepted=row.terms_accepted,
        created_at=row.created_at,
        updated_at=row.updated_at,
        manufacturer=row.manufacturer if include_manufacturer else None,
        events=[RecallEventResponse.model_validate(event) for event in event_rows],
    )


@router.get("/naive", response_model=RecallListResponse)
def list_recalls_naive(
    response: Response,
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> RecallListResponse:
    with count_sql_queries() as counter:
        recalls = list(
            db.scalars(
                select(RecallNotice)
                .order_by(RecallNotice.id)
                .limit(page_size)
            )
        )
        payload = []
        for recall in recalls:
            events = list(
                db.scalars(
                    select(RecallEvent)
                    .where(RecallEvent.recall_id == recall.id)
                    .order_by(RecallEvent.id)
                )
            )
            payload.append(
                serialize_recall(recall, events, include_manufacturer=False)
            )

    response.headers["X-SQL-Query-Count"] = str(counter[0])
    return RecallListResponse(
        implementation="naive",
        page_size=page_size,
        sql_queries=counter[0],
        records=payload,
    )


@router.get("/fixed", response_model=RecallListResponse)
def list_recalls_fixed(
    response: Response,
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> RecallListResponse:
    with count_sql_queries() as counter:
        result = db.execute(
            select(RecallNotice)
            .options(joinedload(RecallNotice.events), joinedload(RecallNotice.manufacturer))
            .order_by(RecallNotice.id)
            .limit(page_size)
        )
        recalls = list(result.unique().scalars())
        payload = [serialize_recall(recall) for recall in recalls]

    response.headers["X-SQL-Query-Count"] = str(counter[0])
    return RecallListResponse(
        implementation="fixed",
        page_size=page_size,
        sql_queries=counter[0],
        records=payload,
    )


@router.get("", response_model=RecallListResponse)
def list_recalls(
    response: Response,
    q: str = Query(default="", max_length=160),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> RecallListResponse:
    statement = (
        select(RecallNotice)
        .options(joinedload(RecallNotice.events), joinedload(RecallNotice.manufacturer))
        .order_by(RecallNotice.id)
        .limit(page_size)
    )
    needle = q.strip()
    if needle:
        pattern = f"%{needle}%"
        statement = statement.where(
            or_(
                RecallNotice.product_name.like(pattern),
                RecallNotice.brand_name.like(pattern),
                RecallNotice.recall_code.like(pattern),
            )
        )

    with count_sql_queries() as counter:
        recalls = list(db.execute(statement).unique().scalars())
        payload = [serialize_recall(recall) for recall in recalls]
    response.headers["X-SQL-Query-Count"] = str(counter[0])
    return RecallListResponse(
        implementation="fixed",
        page_size=page_size,
        sql_queries=counter[0],
        records=payload,
    )


@router.get("/by-manufacturer/{manufacturer_id}", response_model=list[RecallResponse])
def recalls_by_manufacturer(
    manufacturer_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> list[RecallResponse]:
    if db.get(Manufacturer, manufacturer_id) is None:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    rows = list(
        db.execute(
            select(RecallNotice)
            .options(joinedload(RecallNotice.events), joinedload(RecallNotice.manufacturer))
            .where(RecallNotice.manufacturer_id == manufacturer_id)
            .order_by(RecallNotice.id)
        ).unique().scalars()
    )
    return [serialize_recall(row) for row in rows]


@router.get("/{recall_id}", response_model=RecallResponse)
def get_recall(
    recall_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> RecallResponse:
    row = db.execute(
        select(RecallNotice)
        .options(joinedload(RecallNotice.events), joinedload(RecallNotice.manufacturer))
        .where(RecallNotice.id == recall_id)
    ).unique().scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Recall notice not found")
    return serialize_recall(row)


@router.post("", response_model=RecallResponse, status_code=201)
def create_recall(
    payload: RecallCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> RecallResponse:
    if db.get(Manufacturer, payload.manufacturer_id) is None:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    row = RecallNotice(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Recall code must be unique") from exc
    return serialize_recall(row, [])


@router.put("/{recall_id}", response_model=RecallResponse)
def update_recall(
    recall_id: int,
    payload: RecallUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> RecallResponse:
    row = db.get(RecallNotice, recall_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recall notice not found")
    if db.get(Manufacturer, payload.manufacturer_id) is None:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Recall code must be unique") from exc
    events = list(
        db.scalars(
            select(RecallEvent)
            .where(RecallEvent.recall_id == recall_id)
            .order_by(RecallEvent.id)
        )
    )
    return serialize_recall(row, events)


@router.delete("/{recall_id}", status_code=204)
def delete_recall(
    recall_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> None:
    deleted = db.execute(
        delete(RecallNotice).where(RecallNotice.id == recall_id)
    )
    if deleted.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Recall notice not found")
    db.commit()
