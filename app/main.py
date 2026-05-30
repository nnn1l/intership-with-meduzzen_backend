from fastapi import FastAPI
import uvicorn

from app.routes import api_router


def get_application():
    application = FastAPI(
        debug=True,
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
