import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_login_success(client: AsyncClient, test_user):
    """Успешный вход в систему"""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Вход с неверным паролем"""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_login_user_not_found(client: AsyncClient):
    """Вход несуществующего пользователя"""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistentuser", "password": "somepassword"},
    )
    assert response.status_code == 401
