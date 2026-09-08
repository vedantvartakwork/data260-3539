"""FastAPI backend for the DATA 260 grocery recall application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PORT_BASE = 8839
STATIC_DIR = Path(__file__).resolve().parent


class RecallFields(BaseModel):
    """Fields supplied by the recall form."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    product_name: str = Field(alias="productName", min_length=2, max_length=120)
    brand_name: str = Field(alias="brandName", min_length=2, max_length=120)
    submitter_email: EmailStr = Field(alias="submitterEmail")
    recall_details: str = Field(alias="recallDetails", min_length=26, max_length=2000)
    category: str
    terms_accepted: bool = Field(alias="termsAccepted")

    @field_validator("product_name", "brand_name", "recall_details", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        allowed = {"Produce", "Meat and Seafood", "Dairy and Refrigerated", "Packaged Foods"}
        if value not in allowed:
            raise ValueError("select a valid grocery category")
        return value

    @field_validator("terms_accepted")
    @classmethod
    def require_terms(cls, value: bool) -> bool:
        if not value:
            raise ValueError("terms and conditions must be accepted")
        return value


class RecallCreate(RecallFields):
    pass


class RecallUpdate(RecallFields):
    pass


class RecallRecord(RecallFields):
    id: int


INITIAL_RECALLS = [
    RecallRecord(id=1, productName="Garden Fresh Spinach 10 oz", brandName="Valley Harvest", submitterEmail="recalls@example.edu", recallDetails="Selected bags may contain undeclared almonds and should be returned for a refund.", category="Produce", termsAccepted=True),
    RecallRecord(id=2, productName="Creamy Farm Yogurt 6 oz", brandName="Creamy Farm", submitterEmail="safety@example.edu", recallDetails="Some cups may have an incorrect expiration date printed on the foil lid.", category="Dairy and Refrigerated", termsAccepted=True),
]
recalls: list[RecallRecord] = []


def reset_recalls() -> None:
    """Restore the deterministic starter data used by the app and tests."""
    recalls.clear()
    recalls.extend(record.model_copy(deep=True) for record in INITIAL_RECALLS)


reset_recalls()
app = FastAPI(title="Grocery Recall API", version="2.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/recalls", response_model=list[RecallRecord], response_model_by_alias=True)
def list_recalls(q: str = Query(default="", max_length=120)) -> list[RecallRecord]:
    needle = q.strip().casefold()
    if not needle:
        return recalls
    return [record for record in recalls if needle in record.product_name.casefold() or needle in record.brand_name.casefold()]


@app.post("/api/recalls", response_model=RecallRecord, response_model_by_alias=True, status_code=201)
def create_recall(payload: RecallCreate) -> RecallRecord:
    next_id = max((record.id for record in recalls), default=0) + 1
    record = RecallRecord(id=next_id, **payload.model_dump(by_alias=True))
    recalls.append(record)
    return record


@app.put("/api/recalls/1", response_model=RecallRecord, response_model_by_alias=True)
def update_first_recall(payload: RecallUpdate) -> RecallRecord:
    for index, record in enumerate(recalls):
        if record.id == 1:
            updated = RecallRecord(id=1, **payload.model_dump(by_alias=True))
            recalls[index] = updated
            return updated
    raise HTTPException(status_code=404, detail="Recall ID 1 was not found")


@app.delete("/api/recalls/highest")
def delete_highest_recall() -> dict[str, object]:
    if not recalls:
        raise HTTPException(status_code=404, detail="There are no recalls to delete")
    highest = max(recalls, key=lambda record: record.id)
    recalls.remove(highest)
    return {"deleted": highest.model_dump(by_alias=True)}
