from fastapi import FastAPI
import uvicorn
from app.routes import api_router

app = FastAPI(debug=True)

app = FastAPI(
    debug=True,
)
app.include_router(api_router, prefix='')


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
