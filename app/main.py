import os
from fastapi import FastAPI, Depends, HTTPException, status
from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from database import get_db
import models
import app.schemas as schemas

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "FluffyHost API"),
    description="Автоматизированная веб-платформа индивидуальной передержки домашних животных на основе услуг догситтеров",
    version="0.2.0"
)

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
    total_price = item.price + item.tax
    return {
        "item": item,
        "total_price": total_price
    }

#ПРАКТИЧЕСКАЯ №4
@app.get("/pets/", response_model=List[schemas.PetResponse], tags=["Pets"])
async def read_pets(
        skip: int = 0,
        limit: int = 10,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(models.Pet).offset(skip).limit(limit))
    pets = result.scalars().all()
    return pets

@app.get("/pets/{pet_id}", response_model=schemas.PetResponse, tags=["Pets"])
async def read_pet(pet_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Pet).where(models.Pet.id == pet_id))
    pet = result.scalar_one_or_none()

    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pet with id {pet_id} not found"
        )
    return pet

@app.post("/pets/", response_model=schemas.PetResponse, status_code=status.HTTP_201_CREATED, tags=["Pets"])
async def create_pet(pet: schemas.PetCreate, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(models.User).where(models.User.id == 1))
    user_exists = user_result.scalar_one_or_none()

    if not user_exists:
        default_user = models.User(
            id=1,
            email="default@example.com",
            hashed_password="default_hash",
            full_name="Тестовый Хозяин",
            is_sitter=False
        )
        db.add(default_user)
        await db.flush()

    db_pet = models.Pet(**pet.model_dump(), owner_id=1)
    db.add(db_pet)
    await db.commit()
    await db.refresh(db_pet)
    return db_pet