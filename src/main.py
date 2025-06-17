from fastapi import FastAPI
from src.routers.index import index_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(docs_url="/docs", openapi_url="/open-api-docs")

# 허용할 origin들 (배포 시엔 특정 도메인만)
origins = [
    "http://localhost:3000",     # 로컬 테스트용 프론트엔드
    "https://wodfit.netlify.app"  # 실제 배포 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,              # 어떤 origin 허용할지
    allow_credentials=True,
    allow_methods=["*"],                # GET, POST, OPTIONS, DELETE 등
    allow_headers=["*"],                # Authorization, Content-Type 등
)

app.include_router(index_router, prefix="")