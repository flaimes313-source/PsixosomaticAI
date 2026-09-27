# PROJECT_FULL.md

> Единый файл: архитектура + полный код ключевых модулей проекта «Сома. Забота о себе».
> Сгенерирован автоматически через build_context.ps1.
> Вставлять в новый чат с AI для быстрого погружения.

---

## 1. О ПРОЕКТЕ

**Сома** — Telegram-бот, заботливый дневник-собеседник на базе YandexGPT.
Помогает замечать связи между телом, эмоциями, мыслями, сном, питанием, нагрузкой и событиями.

**Ключевое:**
- Не ставит диагнозы, не заменяет врача.
- Один основной сценарий: «Описать состояние».
- Опросы (утро/день/вечер) удалены.
- Динамика — текстовая, доступна всем (FREE, PRO, trial).

**Стек:**
- Python 3.11, aiogram 3.x, SQLAlchemy 2.x (async), asyncpg
- PostgreSQL (BotHost), БЕЗ Alembic
- YandexGPT (yandexgpt/latest)
- Хостинг: BotHost (Docker НЕ используется)

**Среда:** Windows 10, PowerShell (НЕ bash), VS Code.
**Путь:** C:\Users\Alexandr\Desktop\BOTS\psychosomatic_bot
**Деплой:** git push -> BotHost «Обновить из Git» -> «Перезапустить».

---

## 2. АРХИТЕКТУРА

### Главное меню
📝 Описать состояние ← ОСНОВНОЙ сценарий
📔 Дневник
📋 История
📊 Моя динамика
📖 Как это работает?
👤 Профиль
⭐ Сома. PRO

### Сценарии

**1. «📝 Описать состояние»** (describe_state.py)
- Пользователь пишет свободный текст.
- AI отвечает в стиле Сомы.
- Диалог с уточнениями.
- Сохранение в diary_events.
- Кнопка «❌ Отмена» — без AI, без сохранений.

**2. Утреннее сообщение** (reminder_service.py)
- Каждый день в 9:00 по локальному времени.
- 7 случайных вариантов текста.
- Одна кнопка «🌿 Описать состояние».
- Whitelist-пользователи не получают.

**3. «📊 Моя динамика»** (dynamics.py)
- Периоды: 3, 7, 14, 30, 90 дней + свой.
- Доступна всем (FREE, PRO, trial).
- AI получает только describe_user записи.
- Текст: «Что повторялось / Что изменилось / Что понаблюдать».
- Заглушки: 0 записей, 1-2 записи.

**4. Профиль** (profile.py) — создаёт reminder_settings с дефолтами.

**5. Напоминания** (reminders.py) — вкл/выкл, время, дни.

**6. PRO** (pro.py) — 3 дня trial, тарифы 490/1290/2290 руб.

**7. «🗑 Удалить все данные»** (settings.py)
- Удаляет: diary_events, clarifications, analyses, reminder_settings, subscriptions.
- НЕ трогает: users, payments, pro_whitelist, support_requests.

---

## 3. ПОДПИСКА

**Статусы:** active, expired, cancelled, pro_trial.

**Поля users:** trial_used, trial_started_at, trial_ends_at, free_dialog_used, free_dialog_questions_count.

**Enum в БД — нижний регистр!** SQLAlchemy фикс: values_callable=lambda x: [e.value for e in x].

---

## 4. БАЗА ДАННЫХ

**Таблицы:** users, subscriptions, pro_whitelist, diary_events, analyses, clarifications, reminder_settings, payments, support_requests, broadcasts.

**diary_events:** user_id, event_type, source, session_id, content, payload, event_date (UTC).

---

## 5. ПРАВИЛА ДЛЯ AI-АССИСТЕНТА

### ✅ ДЕЛАЕМ
- Полный код файла при замене.
- Учитываем Windows + PowerShell.
- Alembic не используется — миграции через Adminer SQL.
- values_callable для enum.
- Даты с timezone пользователя.

### ❌ НЕ ДЕЛАЕМ
- НЕ трогаем pro_whitelist.
- НЕ трогаем оплату (тестовый магазин).
- НЕ возвращаем опросы.
- НЕ используем Синельникова.
- НЕ делаем динамику PRO-only.
- НЕ сохраняем при отмене диалога.

---

## 6. СТАТУС

**Работает:** describe_state (trial, free_dialog, cancel), утреннее сообщение, PRO (3 тарифа), напоминания, динамика (текст), whitelist, «Удалить все данные».

**Отключено:** SurveyScheduler, роутеры morning/day/evening, старые промпты опросов.

---

## 7. ПОЛНЫЙ КОД ФАЙЛОВ

Ниже — полный код ключевых модулей.