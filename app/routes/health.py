from fastapi import APIRouter

router = APIRouter()

@router.get('/')
def read_root():
    return {
        "status_code": 200,
        "detail": "ok",
        "result": "working"
        }