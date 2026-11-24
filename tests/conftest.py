import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.future import select

from app.main import app
from database import Base, get_db
from app.auth import hash_password
from models import User, Pet, Tag, Booking

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    """Создаёт все таблицы в тестовой SQLite перед запуском тестов и очищает после"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
async def client():
    """Фикстура асинхронного тестового клиента"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(prepare_database):
    """Создаёт или возвращает основного тестового пользователя в SQLite"""
    async with TestingSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "testuser"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                username="testuser",
                email="testuser@example.com",
                hashed_password=hash_password("StrongPass123!"),
                full_name="Тестовый Пользователь",
                phone="+79991112233",
                is_sitter=False,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


@pytest.fixture
async def other_user(prepare_database):
    """Создаёт или возвращает второго пользователя для проверки прав доступа"""
    async with TestingSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "otheruser"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                username="otheruser",
                email="otheruser@example.com",
                hashed_password=hash_password("OtherPass123!"),
                full_name="Чужой Пользователь",
                is_sitter=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "StrongPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def other_auth_headers(client: AsyncClient, other_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "otheruser", "password": "OtherPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
