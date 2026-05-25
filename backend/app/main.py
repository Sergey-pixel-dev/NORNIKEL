from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="Nornikel OKR AI Agent",
    description="ИИ-ассистент для валидации, декомпозиции и назначения OKR",
    version="0.1.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "okr-ai-agent"}


@app.get("/")
async def root():
    return {
        "message": "Nornikel OKR AI Agent API",
        "endpoints": {
            "validate": "/api/validate — проверка цели на SMART",
            "decompose": "/api/decompose — декомпозиция цели",
            "match": "/api/match — матчинг сотрудников и задач"
        }
    }
