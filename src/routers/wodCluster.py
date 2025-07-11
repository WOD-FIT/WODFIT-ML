from fastapi import APIRouter
from pydantic import BaseModel
import asyncio
from typing import List
from src.services.wodCluster import predictCluster

wod_cluster_router = router = APIRouter()

class WodClusterPostBodyDto(BaseModel):
    wods: List[str]
    weights: List[float]

@router.post("/cluster")
async def getWodClusterPrediction(body: WodClusterPostBodyDto):
    loop = asyncio.get_event_loop()
    clusters = await loop.run_in_executor(None, predictCluster, body.wods, body.weights)

    cluster_labels = {
        0: "Endurance",
        1: "Cardio",
        2: "Strength",
        3: "Volume"
    }

    labels = [cluster_labels.get(c, "Unknown") for c in clusters]

    return {"labels": labels}