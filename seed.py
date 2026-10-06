import asyncio
from datetime import datetime, timedelta
from database import AsyncSessionLocal
from models import User, Pet, Booking


async def seed():
    print("Начинаем наполнение базы данных тестовыми записями...")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            owner = User(
                email="owner@example.com",
                hashed_password="password_hash_123",
                full_name="Иван Иванов",
                phone="+79991112233",
                is_sitter=False
            )
            sitter = User(
                email="sitter@example.com",
                hashed_password="password_hash_456",
                full_name="Анна Петрова",
                phone="+79994445566",
                is_sitter=True
            )
            session.add_all([owner, sitter])
            await session.flush()

            pet1 = Pet(
                owner_id=owner.id,
                name="Шарик",
                type="Собака",
                breed="Корги",
                age=2,
                description="Очень дружелюбный пес. Любит педигри."
            )
            session.add(booking := Booking(
                user_id=owner.id,
                pet_id=1,
                start_date=datetime.now() + timedelta(days=2),
                end_date=datetime.now() + timedelta(days=7),
                status="confirmed",
                total_price=5000
            ))
            session.add(pet1)
            await session.flush()

            booking.pet_id = pet1.id

        print("База данных успешно наполнена тестовыми записями!")


if __name__ == "__main__":
    asyncio.run(seed())
