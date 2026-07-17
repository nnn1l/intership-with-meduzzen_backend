import asyncio
from contextlib import asynccontextmanager

from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from starlette.middleware.cors import CORSMiddleware

from app.routes import api_router
from app.database import engine, AsyncSessionLocal
from app.redis_client import redis_pool
from app.services.quiz_checker import QuizReminderService


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

def run_reminder_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        async with AsyncSessionLocal() as db:
            service = QuizReminderService(db)
            await service.check_and_remind_users()

    loop.run_until_complete(run())
    loop.close()

scheduler = BackgroundScheduler()
scheduler.add_job(run_reminder_sync, CronTrigger(hour=0, minute=0))
scheduler.start()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
