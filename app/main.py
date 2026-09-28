import os
from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel

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