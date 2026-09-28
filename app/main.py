import os
from fastapi import FastAPI
from dotenv import load_dotenv

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