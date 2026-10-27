class DomainException(Exception):
    """Базовое исключение для бизнес-логики приложения"""
    message: str = "Произошла ошибка бизнес-логики"


class PetNotFoundError(DomainException):
    """Исключение, если питомец не найден"""
    def __init__(self, pet_id: int):
        self.pet_id = pet_id
        self.message = f"Питомец с ID {pet_id} не найден."


class PetAccessDeniedError(DomainException):
    """Исключение при попытке изменить чужого питомца"""
    def __init__(self, pet_id: int, user_id: int):
        self.pet_id = pet_id
        self.user_id = user_id
        self.message = f"Пользователь {user_id} не имеет прав на управление питомцем {pet_id}."


class PetRestoreError(DomainException):
    """Исключение, если питомец активен или не может быть восстановлен"""
    def __init__(self, pet_id: int):
        self.pet_id = pet_id
        self.message = f"Удаленный питомец с ID {pet_id} не найден или уже активен."
