import asyncio
import math
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, root_validator, validator

from src.services.wodCluster import predictCluster

wod_cluster_router = router = APIRouter()


class WodClusterPostBodyDto(BaseModel):
    wods: List[str] = Field(..., min_items=1, description="List of workout descriptions")
    weights: List[float] = Field(..., min_items=1, description="List of weights corresponding to each workout")

    @validator("wods")
    def validate_wods(cls, value: List[str]) -> List[str]:
        cleaned: List[str] = []
        for idx, wod in enumerate(value):
            if not isinstance(wod, str):
                raise ValueError(f"wods[{idx}] must be a string.")
            stripped = wod.strip()
            if not stripped:
                raise ValueError("Workout descriptions cannot be empty strings.")
            cleaned.append(stripped)
        return cleaned

    @validator("weights")
    def validate_weights(cls, value: List[float]) -> List[float]:
        for idx, weight in enumerate(value):
            if weight is None:
                raise ValueError(f"weights[{idx}] cannot be null.")
            if not math.isfinite(weight):
                raise ValueError("Weights must be finite numbers.")
        return value

    @root_validator
    def validate_lengths(cls, values):
        wods = values.get("wods", [])
        weights = values.get("weights", [])
        if wods and weights and len(wods) != len(weights):
            raise ValueError("The number of wods must match the number of weights.")
        return values


@router.post("/cluster")
async def getWodClusterPrediction(body: WodClusterPostBodyDto):
    loop = asyncio.get_event_loop()
    try:
        clusters = await loop.run_in_executor(None, predictCluster, body.wods, body.weights)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cluster_labels = {
        0: "Endurance",
        1: "Cardio",
        2: "Strength",
        3: "Volume",
    }

    labels = [cluster_labels.get(c, "Unknown") for c in clusters]

    return {"labels": labels}
