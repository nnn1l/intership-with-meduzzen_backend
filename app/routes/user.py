import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import init_db
from ..services.user import UserService
from ..schemas.user import UserUpdate, UserSignUp, UserDetailResponse, UsersListResponse

logger = logging.getLogger("app.crud")
router = APIRouter(prefix="/users", tags=["Users"])


# CREATING USER ROUTE
@router.post("/", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserSignUp, db: AsyncSession = Depends(init_db)):
    logger.info(f"Attempting to create user with username: {user_data.username}")

    try:
        service = UserService(db)
        new_user = await service.create_user(user_data)
        return {"user": new_user}
    except Exception as e:
        logger.error(f"Error appeared during creating user {user_data.username}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user creation")

# GETTING USERS (LIMIT = 10)
@router.get("/", response_model=UsersListResponse)
async def get_users(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(init_db)
):
    service = UserService(db)
    users, total = await service.get_all_users(limit=limit, offset=offset)
    return {"users": users, "total": total}

# GETTING USER BY ID
@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(init_db)):
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    if not user:
        logger.warning(f"User with ID {user_id} not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"user": user}

# UPDATING USER INFO
@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(user_id: int, update_data: UserUpdate, db: AsyncSession = Depends(init_db)):
    logger.info(f"Modifying database: updating user ID {user_id}")
    service = UserService(db)
    updated_user = await service.user_update(user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or modification failed")
    logger.info(f"User ID {user_id} modified successfully")
    return {"user": updated_user}

# DELETING USER
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(init_db)):
    logger.info(f"Modifying database: deleting user ID {user_id}")
    service = UserService(db)
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.info(f"User ID {user_id} deleted successfully")
    return None
