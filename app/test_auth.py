import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_login_success(ac: AsyncClient):
    """Успешный вход в систему"""
    response = await ac.post(
        "/api/v1/auth/login",
        data={"username": "testlogin", "password": "123456"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.anyio
async def test_login_wrong_password(ac: AsyncClient):
    """Вход с неверным паролем"""
    response = await ac.post(
        "/api/v1/auth/login",
        data={"username": "testlogin", "password": "wrongpassword"}
    )
    assert response.status_code == 401

@pytest.mark.anyio
async def test_login_user_not_found(ac: AsyncClient):
    """Вход несуществующего пользователя"""
    response = await ac.post(
        "/api/v1/auth/login",
        data={"username": "nonexistentuser", "password": "somepassword"}
    )
    assert response.status_code == 401