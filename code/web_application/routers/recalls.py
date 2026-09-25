"""Protected grocery-recall CRUD and N+1 demonstration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, joinedload

from code.web_application.db import get_db
from code.web_application.models import RecallEvent, RecallNotice, User
from code.web_application.query_counter import count_sql_queries
from code.web_application.routers.api_auth import require_user
from code.web_application.schemas import (
    RecallCreate,
    RecallEventResponse,
    RecallListResponse,
    RecallResponse,
    RecallUpdate,
)


router = APIRouter(prefix="/api/v1/recalls", tags=["hw4-recalls"])


def serialize_recall(
    row: RecallNotice,
    events: list[RecallEvent] | None = None,
) -> RecallResponse:
    event_rows = row.events if events is None else events
    return RecallResponse(
        id=row.id,
        product_name=row.product_name,
        brand_name=row.brand_name,
        submitter_email=row.submitter_email,
        category=row.category,
        recall_details=row.recall_details,
        terms_accepted=row.terms_accepted,
        created_at=row.created_at,
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
            payload.append(serialize_recall(recall, events))

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
            .options(joinedload(RecallNotice.events))
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
        .options(joinedload(RecallNotice.events))
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


@router.get("/{recall_id}", response_model=RecallResponse)
def get_recall(
    recall_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
) -> RecallResponse:
    row = db.execute(
        select(RecallNotice)
        .options(joinedload(RecallNotice.events))
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
    row = RecallNotice(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
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
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
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
