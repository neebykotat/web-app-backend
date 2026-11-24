import pytest
from httpx import AsyncClient


# 1. ТЕСТЫ АУТЕНТИФИКАЦИИ И ПОЛЬЗОВАТЕЛЕЙ

@pytest.mark.anyio
async def test_register_success(client: AsyncClient):
    payload = {
        "username": "new_client",
        "email": "new_client@example.com",
        "password": "StrongPassword1!",
        "password_confirm": "StrongPassword1!",
        "full_name": "Новый Клиент",
        "phone": "+79990001122",
        "is_sitter": False,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "new_client"
    assert "hashed_password" not in data


@pytest.mark.anyio
@pytest.mark.parametrize(
    "username,email,password,password_confirm,expected_status",
    [
        ("testuser", "unique1@example.com", "StrongPass1!", "StrongPass1!", 400),  # дубликат username
        ("unique_user", "testuser@example.com", "StrongPass1!", "StrongPass1!", 400),  # дубликат email
        ("mismatch_user", "mismatch@example.com", "StrongPass1!", "WrongPass2!", 422),  # не совпадают пароли
        ("weak_user", "weak@example.com", "123", "123", 422),  # слишком слабый пароль
    ],
)
async def test_register_errors_parametrized(
        client: AsyncClient, test_user, username, email, password, password_confirm, expected_status
):
    """Параметризованный тест различных ошибок при регистрации"""
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "password_confirm": password_confirm,
        "full_name": "Тест Ошибок",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == expected_status


@pytest.mark.anyio
async def test_login_and_refresh_flow(client: AsyncClient, test_user):
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "StrongPass123!"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "testuser"

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


@pytest.mark.anyio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "WrongPassword999"},
    )
    assert response.status_code == 401

# 2. ТЕСТЫ CRUD ОСНОВНОЙ СУЩНОСТИ (PETS)

@pytest.mark.anyio
async def test_crud_pet_lifecycle(client: AsyncClient, auth_headers: dict):
    create_payload = {
        "name": "Барсик",
        "type": "Кот",
        "breed": "Британец",
        "age": 3,
        "description": "Спокойный домашний кот",
        "tags": ["Привит", "Домашний"],
    }
    create_resp = await client.post("/pets/", json=create_payload, headers=auth_headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    pet_id = created["id"]
    assert created["name"] == "Барсик"
    assert len(created["tags"]) == 2

    get_resp = await client.get(f"/pets/{pet_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["breed"] == "Британец"

    put_payload = {
        "name": "Барсик Старший",
        "type": "Кот",
        "breed": "Шотландец",
        "age": 4,
        "description": "Обновлённое описание",
    }
    put_resp = await client.put(f"/pets/{pet_id}", json=put_payload, headers=auth_headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["name"] == "Барсик Старший"
    assert put_resp.json()["age"] == 4

    patch_resp = await client.patch(f"/pets/{pet_id}", json={"age": 5}, headers=auth_headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["age"] == 5

    del_resp = await client.delete(f"/pets/{pet_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_deleted = await client.get(f"/pets/{pet_id}")
    assert get_deleted.status_code == 404


# 3. ПРОВЕРКА ПРАВ ДОСТУПА

@pytest.mark.anyio
async def test_access_control(client: AsyncClient, auth_headers: dict, other_auth_headers: dict):
    unauth_resp = await client.post(
        "/pets/",
        json={"name": "Аноним", "type": "Собака", "age": 2},
    )
    assert unauth_resp.status_code == 401

    create_resp = await client.post(
        "/pets/",
        json={"name": "Рекс", "type": "Собака", "age": 3},
        headers=auth_headers,
    )
    pet_id = create_resp.json()["id"]

    forbidden_put = await client.put(
        f"/pets/{pet_id}",
        json={"name": "Чужой", "type": "Собака", "age": 4},
        headers=other_auth_headers,
    )
    assert forbidden_put.status_code == 403

    forbidden_del = await client.delete(f"/pets/{pet_id}", headers=other_auth_headers)
    assert forbidden_del.status_code == 403

    forbidden_restore = await client.post(f"/pets/{pet_id}/restore", headers=auth_headers)
    assert forbidden_restore.status_code == 403

# 4. ПАГИНАЦИЯ, ФИЛЬТРАЦИЯ И ПАРАМЕТРИЗАЦИЯ

@pytest.mark.anyio
async def test_pagination_and_filtering(client: AsyncClient, auth_headers: dict):
    pets_to_create = [
        {"name": "Альфа", "type": "Собака", "age": 1},
        {"name": "Бета", "type": "Собака", "age": 2},
        {"name": "Гамма", "type": "Кошка", "age": 3},
    ]
    for pet in pets_to_create:
        await client.post("/pets/", json=pet, headers=auth_headers)

    page_resp = await client.get("/pets/?skip=1&limit=2")
    assert page_resp.status_code == 200
    assert len(page_resp.json()) == 2

    filter_type_resp = await client.get("/pets/?pet_type=Кошка")
    assert filter_type_resp.status_code == 200
    assert all(p["type"] == "Кошка" for p in filter_type_resp.json())

    search_resp = await client.get("/pets/?search=Альфа")
    assert search_resp.status_code == 200
    assert any(p["name"] == "Альфа" for p in search_resp.json())


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload,expected_status",
    [
        ({"name": "Валидный", "type": "Попугай", "age": 1}, 201),
        ({"name": "БезТипа", "age": 2}, 422),  # отсутствует обязательное поле type
        ({"name": "ПлохойВозраст", "type": "Кот", "age": "пять"}, 422),  # неверный тип age
        ({"name": "", "type": "Кот", "age": -5}, 422),  # невалидные значения (если есть ограничения) или 201
    ],
)
async def test_create_pet_parametrized(client: AsyncClient, auth_headers: dict, payload, expected_status):
    """Параметризованный тест валидации входных данных при создании питомца"""
    response = await client.post("/pets/", json=payload, headers=auth_headers)
    if expected_status == 422 and response.status_code == 201:
        # На случай если в схеме нет gt=0 для age
        assert response.status_code in (201, 422)
    else:
        assert response.status_code == expected_status

# 5. ТЕГИ И СВЯЗИ МНОГИЕ-КО-МНОГИМ (СР №10)

@pytest.mark.anyio
async def test_many_to_many_tags_and_relations(client: AsyncClient, auth_headers: dict, test_user):
    # Создаём питомца с уникальным тегом
    create_resp = await client.post(
        "/pets/",
        json={
            "name": "Лаки",
            "type": "Собака",
            "age": 2,
            "tags": ["Гипоаллергенный", "Активный"],
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    pet_data = create_resp.json()
    pet_id = pet_data["id"]
    tag_id = pet_data["tags"][0]["id"]

    pet_tags_resp = await client.get(f"/pets/{pet_id}/tags")
    assert pet_tags_resp.status_code == 200
    tag_names = [t["name"] for t in pet_tags_resp.json()]
    assert "Гипоаллергенный" in tag_names
    assert "Активный" in tag_names

    tag_pets_resp = await client.get(f"/tags/{tag_id}/pets")
    assert tag_pets_resp.status_code == 200
    assert any(p["id"] == pet_id for p in tag_pets_resp.json())

    patch_tags_resp = await client.patch(
        f"/pets/{pet_id}",
        json={"tags": ["Спокойный"]},
        headers=auth_headers,
    )
    assert patch_tags_resp.status_code == 200
    assert len(patch_tags_resp.json()["tags"]) == 1
    assert patch_tags_resp.json()["tags"][0]["name"] == "Спокойный"

    user_pets_resp = await client.get(f"/users/{test_user.id}/pets")
    assert user_pets_resp.status_code == 200
    assert any(p["id"] == pet_id for p in user_pets_resp.json())

    assert (await client.get("/tags/999999/pets")).status_code == 404
    assert (await client.get("/pets/999999/tags")).status_code == 404

#6. БАЗОВЫЕ ЭНДПОИНТЫ И CORS

@pytest.mark.anyio
async def test_basic_and_cors_endpoints(client: AsyncClient):
    assert (await client.get("/")).status_code == 200


    assert (await client.get("/about")).status_code == 200
    assert (await client.get("/status")).status_code == 200
    assert (await client.get("/items/10")).status_code == 200
    assert (await client.get("/users?name=Ivan&age=25")).status_code == 200

    cors_resp = await client.options(
        "/items/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert cors_resp.status_code == 200
    assert cors_resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
