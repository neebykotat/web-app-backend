import pytest
import asyncio
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL

from app.main import app
from database import get_db

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "fluffyhost_db")

TEST_DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def ac():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

# прошлые

@pytest.mark.anyio
async def test_read_item_success(ac: AsyncClient):
    response = await ac.get("/items/15")
    assert response.status_code == 200
    assert response.json() == {"item_id": 15, "status": "found"}

@pytest.mark.anyio
async def test_read_item_validation_error(ac: AsyncClient):
    response = await ac.get("/items/fluffy-dog")
    assert response.status_code == 422


# самостоятельная 4

@pytest.mark.anyio
async def test_create_pet_success(ac: AsyncClient):
    payload = {
        "name": "Бобик",
        "type": "Собака",
        "breed": "Дворняга",
        "age": 4,
        "description": "Верный и послушный пес"
    }
    response = await ac.post("/pets/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Бобик"
    assert "id" in data
    assert data["owner_id"] == 1

@pytest.mark.anyio
async def test_create_pet_validation_error(ac: AsyncClient):
    payload = {
        "name": "Мурзик",
        "type": "Кошка",
        "age": "неизвестно"
    }
    response = await ac.post("/pets/", json=payload)
    assert response.status_code == 422

@pytest.mark.anyio
async def test_read_pets_with_filters(ac: AsyncClient):
    response = await ac.get("/pets/?search=Бобик&pet_type=Собака")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.anyio
async def test_read_pet_not_found(ac: AsyncClient):
    response = await ac.get("/pets/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Pet with id 99999 not found"
