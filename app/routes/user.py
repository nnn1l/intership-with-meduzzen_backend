from fastapi import Query
from ..services.user import UserService
from ..schemas.user import UserUpdate, UserSignUp, UserDetailResponse, UsersListResponse, UserSignIn
from ..utils.dependencies import get_user_service, get_current_user, validate_profile_owner
from fastapi.security import OAuth2PasswordBearer
from fastapi import APIRouter, Depends, HTTPException, status
from ..services.auth import AuthService
from ..models.user import User

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/signin")

# CREATING USER ROUTE
@router.post("/", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserSignUp, service: UserService = Depends(get_user_service)):
    new_user = await service.create_user(user_data)

    return UserDetailResponse.model_validate(new_user)


# GETTING USERS (LIMIT = 10)
@router.get("/", response_model=UsersListResponse)
async def get_users(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: UserService = Depends(get_user_service)
):
    users, total = await service.get_all_users(limit=limit, offset=offset)
    return UsersListResponse(users=users, total=total)

# GETTING USER BY ID
@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: int, service: UserService = Depends(get_user_service)):
    user = await service.get_user_by_id(user_id)

    return UserDetailResponse.model_validate(user)

# UPDATING USER INFO
@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user(
        user_id: int,
        update_data: UserUpdate,
        service: UserService = Depends(get_user_service),
        _ = Depends(validate_profile_owner)):

    updated_user = await service.user_update(user_id, update_data)

    return UserDetailResponse.model_validate(updated_user)

# DELETING USER
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
        user_id: int,
        service: UserService = Depends(get_user_service),
        _ = Depends(validate_profile_owner)):

    await service.delete_user(user_id)

# SIGN IN
@router.post("/signin")
async def sign_in(user_data: UserSignIn, service: UserService = Depends(get_user_service)):
    user = await service.get_user_by_email(user_data.email)

    if not AuthService.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    access_token = AuthService.create_access_token(data={"sub": user.username, "email": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# GETTING USER BY TOKEN
@router.get("/me", response_model=UserDetailResponse)
async def get_me(current_user: User = Depends(get_current_user)):

    return UserDetailResponse(user=current_user)
