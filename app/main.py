import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import timedelta
from jose import jwt, JWTError

from database import get_db
import app.schemas as schemas
from app.services import get_pet_service
from app.exceptions import PetNotFoundError, PetAccessDeniedError, PetRestoreError, TagNotFoundError
from app.auth import hash_password, SECRET_KEY, ALGORITHM, verify_password, create_access_token, create_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES
from models import User

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "FluffyHost API"),
    description="Автоматизированная веб-платформа индивидуальной передержки домашних животных на основе услуг догситтеров",
    version="0.2.0"
)

raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5500"
)
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FluffyHostAPI")

def log_deletion_activity(pet_id: int):
    logger.info(f" [BACKGROUND TASK] Запись питомца с ID {pet_id} была успешно удалена из базы данных.")

async def pet_service_factory(db: AsyncSession = Depends(get_db)):
    return get_pet_service(db)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_sitter(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_sitter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ разрешен только для пользователей с ролью ситтера."
        )
    return current_user


#ПРАКТИЧЕСКАЯ №1
@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/about")
def read_about():
    return {
        "project": "FluffyHost",
        "description": "Платформа индивидуальной передержки домашних животных на основе услуг догситтеров",
        "team": {
            "name": "FluffyTeam",
            "members": [
                "Борисова Мария (Backend Developer)",
                "Миронов Ярослав (Backend Developer)"
            ]
        }
    }

#ПРАКТИЧЕСКАЯ №2
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id, "status": "found"}

@app.get("/users")
def read_users(name: str | None = None, age: int | None = None):
    return {
        "message": "Фильтрация пользователей",
        "filters": {
            "name": name,
            "age": age
        }
    }

#САМОСТОЯТЕЛЬНАЯ №2
@app.get("/status")
def get_status():
    return {
        "status": "working",
        "application_name": os.getenv("APP_NAME", "FluffyHost API")
    }

class Item(BaseModel):
    name: str
    price: float
    tax: float | None = None

@app.post("/items/")
def create_item(item: Item):
    item_tax = item.tax if item.tax is not None else 0.0
    total_price = item.price + item_tax
    return {
        "item": item,
        "total_price": total_price
    }

#ПРАКТИЧЕСКАЯ №4 (ПЕРЕРАБОТАНА НА СЕРВИСЫ)
@app.get("/pets/", response_model=List[schemas.PetResponse], tags=["Pets"])
async def read_pets(
        skip: int = 0,
        limit: int = 10,
        search: str | None = None,
        pet_type: str | None = None,
        service=Depends(pet_service_factory)
):
    return await service.get_pets(skip=skip, limit=limit, search=search, pet_type=pet_type)

@app.get("/pets/{pet_id}", response_model=schemas.PetResponse, tags=["Pets"])
async def read_pet(pet_id: int, service=Depends(pet_service_factory)):
    try:
        return await service.get_pet_by_id(pet_id)
    except PetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

@app.post("/pets/", response_model=schemas.PetResponse, status_code=status.HTTP_201_CREATED, tags=["Pets"])
async def create_pet(
        pet: schemas.PetCreate,
        current_user: User = Depends(get_current_user),
        service=Depends(pet_service_factory)):
    return await service.create_pet(pet, owner_id=current_user.id)

# ПРАКТИЧЕСКАЯ №5 (ПЕРЕРАБОТАНА НА СЕРВИСЫ)
@app.put("/pets/{pet_id}", response_model=schemas.PetResponse, tags=["Pets"])
async def update_pet(
        pet_id: int,
        pet_data: schemas.PetUpdate,
        current_user: User = Depends(get_current_user),
        service=Depends(pet_service_factory)
):
    try:
        is_admin = getattr(current_user, "is_admin", False)
        return await service.update_pet(pet_id, pet_data, user_id=current_user.id, is_admin=is_admin)
    except PetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except PetAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)

@app.patch("/pets/{pet_id}", response_model=schemas.PetResponse, tags=["Pets"])
async def partial_update_pet(
        pet_id: int,
        pet_data: schemas.PetPartialUpdate,
        current_user: User = Depends(get_current_user),
        service=Depends(pet_service_factory)
):
    try:
        is_admin = getattr(current_user, "is_admin", False)
        return await service.partial_update_pet(pet_id, pet_data, user_id=current_user.id, is_admin=is_admin)
    except PetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except PetAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)

@app.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Pets"])
async def delete_pet(
        pet_id: int,
        background_tasks: BackgroundTasks = BackgroundTasks(),
        current_user: User = Depends(get_current_user),
        service=Depends(pet_service_factory)
):
    try:
        is_admin = getattr(current_user, "is_admin", False)
        await service.delete_pet(pet_id, user_id=current_user.id, is_admin=is_admin)
        background_tasks.add_task(log_deletion_activity, pet_id)
        return None
    except PetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except PetAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)

@app.post("/pets/{pet_id}/restore", response_model=schemas.PetResponse, tags=["Pets"])
async def restore_pet(
        pet_id: int,
        current_user: User = Depends(get_current_user),
        service=Depends(pet_service_factory)
):
    try:
        is_admin = getattr(current_user, "is_admin", False)
        return await service.restore_pet(pet_id, is_admin=is_admin)
    except PetAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Восстановление удаленных питомцев доступно только администратору."
        )
    except PetRestoreError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

# ПРАКТИЧЕСКАЯ 6 + САМОСТОЯТЕЛЬНАЯ 6
@app.get("/users/{user_id}/pets", response_model=List[schemas.PetResponse], tags=["Relations"])
async def read_user_pets(user_id: int, service=Depends(pet_service_factory)):
    """Получить всех питомцев конкретного пользователя"""
    return await service.get_user_pets(user_id)


@app.get("/pets/{pet_id}/tags", response_model=List[schemas.TagResponse], tags=["Relations"])
async def read_pet_tags(pet_id: int, service=Depends(pet_service_factory)):
    """Получить теги конкретного питомца"""
    try:
        return await service.get_pet_tags(pet_id)
    except PetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@app.get("/tags/{tag_id}/pets", response_model=List[schemas.PetResponse], tags=["Relations"])
async def read_tag_pets(tag_id: int, service=Depends(pet_service_factory)):
    """Получить всех питомцев с указанным тегом"""
    try:
        return await service.get_pets_by_tag(tag_id)
    except TagNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ПРАКТИЧЕСКАЯ №7
@app.post("/api/v1/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED,
          tags=["Auth"])
async def register_user(user_data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя (клиента или ситтера в рамках гибридного аккаунта)"""
    existing_username = await db.execute(select(User).where(User.username == user_data.username))
    if existing_username.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует."
        )

    existing_email = await db.execute(select(User).where(User.email == user_data.email))
    if existing_email.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегистрирован."
        )

    hashed_pwd = hash_password(user_data.password)

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pwd,
        full_name=user_data.full_name,
        phone=user_data.phone,
        is_sitter=user_data.is_sitter
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@app.post("/api/v1/auth/login", response_model=schemas.Token, tags=["Auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Аутентификация пользователя и выдача JWT-токена)"""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "is_sitter": user.is_sitter},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.get("/api/v1/users/me", response_model=schemas.UserResponse, tags=["Auth"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем авторизованном пользователе"""
    return current_user


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/api/v1/auth/refresh", response_model=schemas.Token, tags=["Auth"])
async def refresh_access_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Получение нового access-токена по валидному refresh-токену"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный или просроченный refresh-токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "is_sitter": user.is_sitter},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "refresh_token": body.refresh_token,
        "token_type": "bearer"
    }