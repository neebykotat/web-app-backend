from sqlalchemy.ext.asyncio import AsyncSession
from .pet_service import PetService

def get_pet_service(session: AsyncSession) -> PetService:
    """Фабрика сервиса: создает экземпляр PetService с текущей сессией БД"""
    return PetService(session=session)
