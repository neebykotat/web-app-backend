from pydantic import BaseModel, ConfigDict
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
