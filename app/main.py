from fastapi import FastAPI

app = FastAPI(
    title="FluffyHost API",
    description="Автоматизированная веб-платформа индивидуальной передержки домашних животных на основе услуг догситтеров",
    version="0.1.0"
)

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
