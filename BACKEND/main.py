import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure .env is loaded regardless of current working directory
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")
load_dotenv()

from app.routes.gnews import router as news_router
from app.routes.earthquakes import router as earthquakes_router
from app.routes.sachet import router as sachet_router

app = FastAPI(
    title="DISHA Backend API",
    description="Disaster Intelligence and Situational Hazard Awareness Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow CORS for frontend integration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(news_router)
app.include_router(earthquakes_router)
app.include_router(sachet_router)


@app.get("/", tags=["General"])
async def root():
    return {
        "message": "DISHA Platform API is running",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "service": "DISHA Backend",
    }


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("ENV", "development").lower() == "development"

    print(f"Starting DISHA Backend server at http://{host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
    )