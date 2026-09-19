from fastapi import FastAPI

app = FastAPI(
    title="FluffyHost API",
    description="Автоматизированная веб-платформа индивидуальной передержки домашних животных на основе услуг догситтеров",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Hello World"}


