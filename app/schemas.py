from pydantic import BaseModel, ConfigDict
from typing import Optional

class PetBase(BaseModel):
    name: str
    type: str  # Собака, кошка и т.д.
    breed: Optional[str] = None
    age: int
    description: Optional[str] = None

class PetCreate(PetBase):
    pass

class PetResponse(PetBase):
    id: int
    owner_id: int

    model_config = ConfigDict(from_attributes=True)
