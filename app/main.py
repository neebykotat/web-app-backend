import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
import app.schemas as schemas
from app.services import get_pet_service
from app.exceptions import PetNotFoundError, PetAccessDeniedError, PetRestoreError

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "FluffyHost API"),
    description="Автоматизированная веб-платформа индивидуальной передержки домашних животных на основе услуг догситтеров",
    version="0.2.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FluffyHostAPI")

def log_deletion_activity(pet_id: int):
    logger.info(f" [BACKGROUND TASK] Запись питомца с ID {pet_id} была успешно удалена из базы данных.")

async def pet_service_factory(db: AsyncSession = Depends(get_db)):
    return get_pet_service(db)

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
async def create_pet(pet: schemas.PetCreate, service=Depends(pet_service_factory)):
    return await service.create_pet(pet)

# ПРАКТИЧЕСКАЯ №5 (ПЕРЕРАБОТАНА НА СЕРВИСЫ)
@app.put("/pets/{pet_id}", response_model=schemas.PetResponse, tags=["Pets"])
async def update_pet(pet_id: int, pet_data: schemas.PetUpdate, user_id: int, is_admin: bool = False, service=Depends(pet_service_factory)):
    try:
        return await service.update_pet(pet_id, pet_data, user_id, is_admin)
    except PetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except PetAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)

@app.patch("/pets/{pet_id}", response_model=schemas.PetResponse, tags=["Pets"])
async def partial_update_pet(pet_id: int, pet_data: schemas.PetPartialUpdate, user_id: int, is_admin: bool = False, service=Depends(pet_service_factory)):
    try:
        return await service.partial_update_pet(pet_id, pet_data, user_id, is_admin)
    except PetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except PetAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)

@app.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Pets"])
async def delete_pet(pet_id: int, user_id: int, is_admin: bool = False, background_tasks: BackgroundTasks = BackgroundTasks(), service=Depends(pet_service_factory)):
    try:
        await service.delete_pet(pet_id, user_id, is_admin)
        background_tasks.add_task(log_deletion_activity, pet_id)
        return None
    except PetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except PetAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)

@app.post("/pets/{pet_id}/restore", response_model=schemas.PetResponse, tags=["Pets"])
async def restore_pet(pet_id: int, is_admin: bool = False, service=Depends(pet_service_factory)):
    try:
        return await service.restore_pet(pet_id, is_admin)
    except PetAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Восстановление удаленных питомцев доступно только администратору."
        )
    except PetRestoreError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
