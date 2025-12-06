import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import transfer_router, storage_router

app = FastAPI(title=settings.PROJECT_NAME, openapi_url="/api/v1/openapi.json")

# CORS: allow all for simplicity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transfer_router, prefix="/api/v1/transfer", tags=["transfer"])
app.include_router(storage_router, prefix="/api/v1/storage", tags=["storage"])


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
