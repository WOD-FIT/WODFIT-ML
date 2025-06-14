from fastapi import APIRouter
from src.routers.wodCluster import wod_cluster_router

index_router = router = APIRouter()

router.include_router(wod_cluster_router, prefix="/wod")

