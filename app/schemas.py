import re
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing import Optional, List

#Схемы тегов
class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

#Схемы питомцев
class PetBase(BaseModel):
    name: str
    type: str
    breed: Optional[str] = None
    age: int
    description: Optional[str] = None

class PetCreate(PetBase):
    tags: Optional[List[str]] = []

class PetResponse(PetBase):
    id: int
    owner_id: int
    tags: List[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)

class PetUpdate(BaseModel):
    name: str
    type: str
    breed: Optional[str] = None
    age: int
    description: Optional[str] = None

class PetPartialUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    breed: Optional[str] = None
    age: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

# Схемы пользователей
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="Уникальный логин пользователя")
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=6, description="Пароль")
    password_confirm: str = Field(..., description="Подтверждение пароля")
    full_name: str = Field(..., max_length=255, description="ФИО пользователя")
    phone: Optional[str] = Field(None, max_length=50, description="Телефон для связи")
    is_sitter: bool = Field(False, description="Флаг роли ситтера (по умолчанию клиент)")

    @model_validator(mode='after')
    def validate_passwords(self) -> 'UserCreate':
        if self.password != self.password_confirm:
            raise ValueError("Пароли не совпадают")

        pwd = self.password
        if not re.search(r"[A-Z]", pwd):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву (A-Z)")
        if not re.search(r"\d", pwd):
            raise ValueError("Пароль должен содержать хотя бы одну цифру (0-9)")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd):
            raise ValueError("Пароль должен содержать хотя бы один специальный символ (!@#$%^&*...)")

        return self

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    is_sitter: bool

    model_config = ConfigDict(from_attributes=True)