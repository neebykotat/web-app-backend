from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import models
import app.schemas as schemas
from app.exceptions import PetNotFoundError, PetAccessDeniedError, PetRestoreError


class PetService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pets(self, skip: int = 0, limit: int = 10, search: Optional[str] = None,
                       pet_type: Optional[str] = None) -> List[models.Pet]:
        query = select(models.Pet).where(models.Pet.is_active == True)
        if search:
            query = query.where(models.Pet.name.contains(search))
        if pet_type:
            query = query.where(models.Pet.type == pet_type)

        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_pet_by_id(self, pet_id: int) -> models.Pet:
        result = await self.session.execute(
            select(models.Pet).where(models.Pet.id == pet_id, models.Pet.is_active == True)
        )
        pet = result.scalar_one_or_none()
        if not pet:
            raise PetNotFoundError(pet_id)
        return pet

    async def create_pet(self, pet_data: schemas.PetCreate) -> models.Pet:
        user_result = await self.session.execute(select(models.User).where(models.User.id == 1))
        user_exists = user_result.scalar_one_or_none()

        if not user_exists:
            default_user = models.User(
                id=1,
                email="default@example.com",
                hashed_password="default_hash",
                full_name="Тестовый Хозяин",
                is_sitter=False
            )
            self.session.add(default_user)
            await self.session.flush()

        db_pet = models.Pet(**pet_data.model_dump(), owner_id=1)
        self.session.add(db_pet)
        await self.session.commit()
        await self.session.refresh(db_pet)
        return db_pet

    async def update_pet(self, pet_id: int, pet_data: schemas.PetUpdate, user_id: int,
                         is_admin: bool = False) -> models.Pet:
        result = await self.session.execute(select(models.Pet).where(models.Pet.id == pet_id))
        db_pet = result.scalar_one_or_none()
        if not db_pet:
            raise PetNotFoundError(pet_id)

        if db_pet.owner_id != user_id and not is_admin:
            raise PetAccessDeniedError(pet_id, user_id)

        for key, value in pet_data.model_dump().items():
            setattr(db_pet, key, value)

        await self.session.commit()
        await self.session.refresh(db_pet)
        return db_pet

    async def partial_update_pet(self, pet_id: int, pet_data: schemas.PetPartialUpdate, user_id: int,
                                 is_admin: bool = False) -> models.Pet:
        result = await self.session.execute(select(models.Pet).where(models.Pet.id == pet_id))
        db_pet = result.scalar_one_or_none()
        if not db_pet:
            raise PetNotFoundError(pet_id)

        if db_pet.owner_id != user_id and not is_admin:
            raise PetAccessDeniedError(pet_id, user_id)

        update_fields = pet_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(db_pet, key, value)

        await self.session.commit()
        await self.session.refresh(db_pet)
        return db_pet

    async def delete_pet(self, pet_id: int, user_id: int, is_admin: bool = False) -> None:
        result = await self.session.execute(
            select(models.Pet).where(models.Pet.id == pet_id, models.Pet.is_active == True)
        )
        db_pet = result.scalar_one_or_none()
        if not db_pet:
            raise PetNotFoundError(pet_id)

        if db_pet.owner_id != user_id and not is_admin:
            raise PetAccessDeniedError(pet_id, user_id)

        db_pet.is_active = False
        await self.session.commit()

    async def restore_pet(self, pet_id: int, is_admin: bool = False) -> models.Pet:
        if not is_admin:
            raise PetAccessDeniedError(pet_id, user_id=0)

        result = await self.session.execute(
            select(models.Pet).where(models.Pet.id == pet_id, models.Pet.is_active == False)
        )
        db_pet = result.scalar_one_or_none()
        if not db_pet:
            raise PetRestoreError(pet_id)

        db_pet.is_active = True
        await self.session.commit()
        await self.session.refresh(db_pet)
        return db_pet
