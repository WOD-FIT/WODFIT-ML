from fastapi import FastAPI
from src.routers.index import index_router

app = FastAPI(docs_url="/docs", openapi_url="/open-api-docs")


app.include_router(index_router, prefix="")