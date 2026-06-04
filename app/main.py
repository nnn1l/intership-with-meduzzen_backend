from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from app.routes import api_router
from app.database import engine
from app.redis_client import redis_pool

@asynccontextmanager
async def lifespan(app:FastAPI):
    yield
    await engine.dispose()
    await redis_pool.disconnect()

app = FastAPI(
    debug=True,
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix='')



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
