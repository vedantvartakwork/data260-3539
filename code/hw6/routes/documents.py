"""FastAPI CRUD routes for the Part 1 MongoDB document collection."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status
from pymongo.errors import PyMongoError

from code.hw6.repositories import DocumentRepository
from code.hw6.schemas import RecallDocumentCreate, RecallDocumentOut, RecallDocumentUpdate


router = APIRouter(prefix="/api/v1/documents", tags=["HW6 documents"])


def repository() -> DocumentRepository:
    try:
        return DocumentRepository()
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from exc


@router.post("", response_model=RecallDocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(payload: RecallDocumentCreate) -> dict:
    return repository().create(payload.model_dump())


@router.get("", response_model=list[RecallDocumentOut])
def list_documents(
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> list[dict]:
    return repository().list(limit=limit, skip=skip)


@router.get("/{document_id}", response_model=RecallDocumentOut)
def get_document(document_id: str) -> dict:
    result = repository().get(document_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


def _update_document(document_id: str, payload: RecallDocumentUpdate) -> dict:
    result = repository().update(document_id, payload.model_dump(exclude_unset=True))
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.put("/{document_id}", response_model=RecallDocumentOut)
def replace_document(document_id: str, payload: RecallDocumentUpdate) -> dict:
    """Update a recall document through the assignment-required PUT route."""
    return _update_document(document_id, payload)


@router.patch("/{document_id}", response_model=RecallDocumentOut, include_in_schema=False)
def patch_document(document_id: str, payload: RecallDocumentUpdate) -> dict:
    """Keep PATCH as a backward-compatible alias for earlier clients."""
    return _update_document(document_id, payload)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str) -> Response:
    if not repository().delete(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
