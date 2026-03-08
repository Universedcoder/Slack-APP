from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from DataBot.core.config import settings
from DataBot.routers.slack import router as slack_router


app = FastAPI(
    title="DataBot",
    description="Slack slash command backend for natural-language analytics queries",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(slack_router, tags=["slack"])


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "DataBot",
        "version": "2.0.0",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "DataBot.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
