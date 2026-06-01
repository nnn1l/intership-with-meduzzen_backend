from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api_router
from app.database import engine
from app.redis_client import redis_pool

@asynccontextmanager
async def lifespan(app:FastAPI):
    yield
    await engine.dispose()
    await redis_pool.disconnect()

def get_application():
    application = FastAPI(
        debug=True,
        lifespan=lifespan
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix='')

    return application

app = get_application()



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
