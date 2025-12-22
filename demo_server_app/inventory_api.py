"""unified demo server for pharmacy system - inventory and medication data"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

INVENTORY_PATH = os.getenv("INVENTORY_PATH", os.path.join(os.path.dirname(__file__), "data", "inventory.json"))
MEDICATIONS_PATH = os.getenv("MEDICATIONS_PATH", os.path.join(os.path.dirname(__file__), "data", "medications.json"))

app = FastAPI(title="Pharmacy Demo Server", version="0.1.0")


def _utc_now_iso() -> str:
    """
    get current utc time in iso format

    returns:
        iso formatted timestamp string
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_inventory() -> Dict[str, Dict[str, Any]]:
    """
    load inventory data from json file and validate structure

    returns:
        dictionary mapping medication ids to stock data

    raises:
        ValueError: if inventory data structure is invalid
    """
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("inventory.json must be an object keyed by medication id")

    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, dict) or "stock_quantity" not in v:
            raise ValueError(f"invalid inventory entry for {k!r}: {v!r}")

    return data


def load_medications() -> List[Dict[str, Any]]:
    """
    load medication data from json file and validate structure

    returns:
        list of medication dictionaries

    raises:
        ValueError: if medication data structure is invalid
    """
    with open(MEDICATIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("medications.json must be an array of medication objects")

    for med in data:
        if not isinstance(med, dict) or "id" not in med or "names" not in med:
            raise ValueError(f"invalid medication entry: {med!r}")

    return data


INVENTORY: Dict[str, Dict[str, Any]] = load_inventory()
MEDICATIONS: List[Dict[str, Any]] = load_medications()


class StockResponse(BaseModel):
    """stock information response model"""
    id: str
    stock_quantity: int = Field(ge=0)
    updated_at: str


class BatchRequest(BaseModel):
    """batch stock query request model"""
    ids: List[str] = Field(min_length=1, max_length=100)


class BatchResponse(BaseModel):
    """batch stock query response model"""
    items: List[StockResponse]


class CheckStockResponse(BaseModel):
    """boolean stock availability response model"""
    id: str
    in_stock: bool


class CheckInventoryResponse(BaseModel):
    """inventory quantity response model"""
    id: str
    quantity: int = Field(ge=0)


class MedicationResponse(BaseModel):
    """full medication information response model"""
    id: str
    names: Dict[str, str]
    active_ingredient: Dict[str, str]
    dosage: str
    prescription_required: bool
    usage_instructions: Dict[str, str]
    warnings: Dict[str, str]
    category: Dict[str, str]
    price_usd: float


class SimplifiedMedicationResponse(BaseModel):
    """simplified medication response for list views"""
    id: str
    name: str
    active_ingredient: str
    category: str
    prescription_required: bool


class MedicationBatchRequest(BaseModel):
    """batch medication query request model"""
    ids: List[str] = Field(min_length=1, max_length=100)


class MedicationBatchResponse(BaseModel):
    """batch medication query response model"""
    items: List[MedicationResponse]


@app.get("/health")
def health() -> Dict[str, Any]:
    """
    health check endpoint

    returns:
        status, counts, and current timestamp
    """
    return {
        "status": "ok",
        "time": _utc_now_iso(),
        "inventory_items": len(INVENTORY),
        "medications_count": len(MEDICATIONS)
    }


@app.get("/stock/{med_id}", response_model=StockResponse)
def get_stock(med_id: str) -> StockResponse:
    """
    get detailed stock information for a medication

    args:
        med_id: medication identifier

    returns:
        stock response with quantity and timestamp

    raises:
        HTTPException: 404 if medication not found
    """
    item = INVENTORY.get(med_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"unknown medication id: {med_id}"}
        )
    return StockResponse(
        id=med_id,
        stock_quantity=int(item["stock_quantity"]),
        updated_at=str(item.get("updated_at") or _utc_now_iso())
    )


@app.post("/stock/batch", response_model=BatchResponse)
def batch_stock(req: BatchRequest) -> BatchResponse:
    """
    get stock information for multiple medications

    args:
        req: batch request with list of medication ids

    returns:
        batch response with stock info for found medications
    """
    out: List[StockResponse] = []
    for med_id in req.ids:
        item = INVENTORY.get(med_id)
        if item is None:
            continue
        out.append(
            StockResponse(
                id=med_id,
                stock_quantity=int(item["stock_quantity"]),
                updated_at=str(item.get("updated_at") or _utc_now_iso())
            )
        )
    return BatchResponse(items=out)


@app.get("/check_stock/{med_id}", response_model=CheckStockResponse)
def check_stock(med_id: str) -> CheckStockResponse:
    """
    check if medication is in stock (boolean response)

    args:
        med_id: medication identifier

    returns:
        boolean stock availability status

    raises:
        HTTPException: 404 if medication not found
    """
    item = INVENTORY.get(med_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"unknown medication id: {med_id}"}
        )
    in_stock = int(item["stock_quantity"]) > 0
    return CheckStockResponse(id=med_id, in_stock=in_stock)


@app.get("/check_inventory/{med_id}", response_model=CheckInventoryResponse)
def check_inventory(med_id: str) -> CheckInventoryResponse:
    """
    check inventory quantity for a medication (integer response)

    note: this endpoint is deprecated - use check_stock for boolean availability

    args:
        med_id: medication identifier

    returns:
        exact inventory quantity

    raises:
        HTTPException: 404 if medication not found
    """
    item = INVENTORY.get(med_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"unknown medication id: {med_id}"}
        )
    return CheckInventoryResponse(id=med_id, quantity=int(item["stock_quantity"]))


@app.get("/medications", response_model=List[SimplifiedMedicationResponse])
def get_all_medications(
    language: str = Query(default="en", pattern="^(en|he|ru|ar)$")
) -> List[SimplifiedMedicationResponse]:
    """
    get all medications in simplified format

    args:
        language: language code for names and ingredients (en, he, ru, ar)

    returns:
        list of simplified medication objects
    """
    result = []
    for med in MEDICATIONS:
        result.append(
            SimplifiedMedicationResponse(
                id=med["id"],
                name=med["names"].get(language, med["names"]["en"]),
                active_ingredient=med["active_ingredient"].get(language, med["active_ingredient"]["en"]),
                category=med["category"].get(language, med["category"]["en"]),
                prescription_required=med.get("prescription_required", False)
            )
        )
    return result


@app.get("/medications/{med_id}", response_model=MedicationResponse)
def get_medication_by_id(med_id: str) -> MedicationResponse:
    """
    get full medication information by id

    args:
        med_id: medication identifier

    returns:
        full medication object

    raises:
        HTTPException: 404 if medication not found
    """
    for med in MEDICATIONS:
        if med["id"] == med_id:
            return MedicationResponse(**med)

    raise HTTPException(
        status_code=404,
        detail={"code": "NOT_FOUND", "message": f"unknown medication id: {med_id}"}
    )


@app.get("/medications/by-name/{name}", response_model=MedicationResponse)
def get_medication_by_name(
    name: str,
    language: str = Query(default="en", pattern="^(en|he|ru|ar)$")
) -> MedicationResponse:
    """
    get medication by name using case-insensitive match

    args:
        name: medication name to search for
        language: language code (en, he, ru, ar)

    returns:
        full medication object

    raises:
        HTTPException: 404 if medication not found
    """
    name_lower = name.lower().strip()

    for med in MEDICATIONS:
        med_name = med.get("names", {}).get(language, "")
        if med_name.lower().strip() == name_lower:
            return MedicationResponse(**med)

    raise HTTPException(
        status_code=404,
        detail={"code": "NOT_FOUND", "message": f"medication '{name}' not found in {language}"}
    )


@app.get("/medications/by-ingredient/{ingredient}", response_model=List[MedicationResponse])
def search_by_ingredient(
    ingredient: str,
    language: str = Query(default="en", pattern="^(en|he|ru|ar)$")
) -> List[MedicationResponse]:
    """
    search medications by active ingredient using exact case-insensitive match

    args:
        ingredient: active ingredient name to search
        language: language code (en, he, ru, ar)

    returns:
        list of medication objects matching the ingredient
    """
    results = []
    ingredient_lower = ingredient.lower().strip()

    for med in MEDICATIONS:
        active_ing = med.get("active_ingredient", {}).get(language, "")
        if active_ing.lower().strip() == ingredient_lower:
            results.append(MedicationResponse(**med))

    return results


@app.post("/medications/batch", response_model=MedicationBatchResponse)
def batch_medications(req: MedicationBatchRequest) -> MedicationBatchResponse:
    """
    get medication information for multiple ids

    args:
        req: batch request with list of medication ids

    returns:
        batch response with medication info for found medications
    """
    out: List[MedicationResponse] = []
    for med_id in req.ids:
        for med in MEDICATIONS:
            if med["id"] == med_id:
                out.append(MedicationResponse(**med))
                break

    return MedicationBatchResponse(items=out)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
