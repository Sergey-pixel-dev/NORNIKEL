from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.database import create_tables
from app.db.seed import seed_data

app = FastAPI(
    title="Nornikel OKR AI Agent",
    description="ИИ-ассистент для валидации, декомпозиции и назначения OKR",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def on_startup():
    await create_tables()
    await seed_data()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "okr-ai-agent", "version": "0.2.0"}


@app.get("/")
async def root():
    return {
        "message": "Nornikel OKR AI Agent API",
        "version": "0.2.0",
        "endpoints": {
            "validate": "POST /api/validate — проверка + сохранение цели",
            "goals": "GET /api/goals — список целей",
            "goal_detail": "GET /api/goals/{id} — цель с декомпозицией",
            "decompose": "POST /api/goals/{id}/decompose — декомпозиция",
            "match": "POST /api/goals/{id}/match — матчинг",
        }
    }
