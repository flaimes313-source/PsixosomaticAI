"""
Тесты для работы с пользователями.
"""
import pytest
import asyncio
from datetime import datetime

from app.db.models.user import User
from app.db.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_create_user(db_session):
    """Тест создания нового пользователя"""
    repo = UserRepository(db_session)
    
    user = await repo.create(
        telegram_id=123456789,
        username="test_user",
        first_name="Ivan",
        last_name="Test",
        language_code="ru",
    )
    
    assert user.id is not None
    assert user.telegram_id == 123456789
    assert user.username == "test_user"
    assert user.first_name == "Ivan"
    assert user.last_name == "Test"
    assert user.language_code == "ru"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.last_seen_at is not None


@pytest.mark.asyncio
async def test_get_by_telegram_id(db_session):
    """Тест получения пользователя по telegram_id"""
    repo = UserRepository(db_session)
    
    await repo.create(
        telegram_id=123456789,
        username="test_user",
    )
    
    user = await repo.get_by_telegram_id(123456789)
    
    assert user is not None
    assert user.telegram_id == 123456789
    assert user.username == "test_user"


@pytest.mark.asyncio
async def test_get_or_create_does_not_duplicate(db_session):
    """Тест: get_or_create не создает дубликаты"""
    repo = UserRepository(db_session)
    
    user1 = await repo.get_or_create(
        telegram_id=123456789,
        username="test_user",
    )
    
    user2 = await repo.get_or_create(
        telegram_id=123456789,
        username="test_user",
    )
    
    assert user1.id == user2.id
    assert user1.telegram_id == user2.telegram_id


@pytest.mark.asyncio
async def test_update_last_seen(db_session):
    """Тест обновления времени последнего визита"""
    repo = UserRepository(db_session)
    
    user = await repo.create(
        telegram_id=123456789,
        username="test_user",
    )
    
    old_last_seen = user.last_seen_at
    
    # Ждем немного
    await asyncio.sleep(0.1)
    
    updated = await repo.update_last_seen(123456789)
    
    assert updated is not None
    assert updated.last_seen_at >= old_last_seen


@pytest.mark.asyncio
async def test_get_or_create_updates_last_seen(db_session):
    """Тест: get_or_create обновляет last_seen_at для существующего пользователя"""
    repo = UserRepository(db_session)
    
    # Создаем пользователя
    user1 = await repo.create(
        telegram_id=123456789,
        username="test_user",
    )
    
    old_last_seen = user1.last_seen_at
    
    # Ждем немного
    await asyncio.sleep(0.1)
    
    # Получаем существующего пользователя
    user2 = await repo.get_or_create(
        telegram_id=123456789,
        username="updated_user",
    )
    
    assert user2.id == user1.id
    assert user2.last_seen_at > old_last_seen


@pytest.mark.asyncio
async def test_update_profile(db_session):
    """Тест обновления профиля пользователя"""
    repo = UserRepository(db_session)
    
    # Создаем пользователя
    await repo.create(
        telegram_id=123456789,
        username="old_name",
        first_name="Old",
    )
    
    # Обновляем профиль
    updated_user = await repo.update_profile(
        telegram_id=123456789,
        username="new_name",
        first_name="New",
        language_code="ru",
    )
    
    assert updated_user is not None
    assert updated_user.username == "new_name"
    assert updated_user.first_name == "New"
    assert updated_user.language_code == "ru"