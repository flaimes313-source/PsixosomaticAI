# PROJECT_CONTEXT.md

> Единый контекст проекта «Сома. Забота о себе».
> Вставлять в начало нового чата с AI-ассистентом.

---

## 1. О ПРОЕКТЕ

**Сома** — Telegram-бот, заботливый дневник-собеседник на базе YandexGPT.
Помогает пользователю замечать связи между телом, эмоциями, мыслями, сном, питанием, нагрузкой и событиями жизни.

**Ключевое:**
- Бот **не ставит диагнозы** и **не заменяет врача**.
- Не ищет «правильную» причину. Помогает **самому** замечать закономерности.
- Один основной сценарий — **«📝 Описать состояние»**.
- Опросы (утро/день/вечер) **удалены**.

**Стек:**
- Python 3.11, aiogram 3.x, SQLAlchemy 2.x (async), asyncpg
- PostgreSQL (BotHost), БЕЗ Alembic — миграции через Adminer
- YandexGPT (yandexgpt/latest)
- Хостинг: **BotHost** (Docker НЕ используется)

---

## 2. РЕПОЗИТОРИЙ И СРЕДА

- **Локально:** `C:\Users\Alexandr\Desktop\BOTS\psychosomatic_bot`
- **ОС разработки:** Windows 10, PowerShell (НЕ bash!)
- **Хостинг:** BotHost (botost.host), веб-панель + Adminer для БД
- **Деплой:** `git add` → `git commit` → `git push` → кнопка «Обновить из Git» на BotHost → «Перезапустить»
- **БД:** Adminer на `http://adminer.pghost.ru/` (доступ через панель BotHost)
- **В БД всегда нижний регистр для enum:** `active`, `expired`, `cancelled`, `pro_trial`, `free`, `pro`

**Важно про PowerShell:**
- `grep` НЕ работает → `Select-String`
- Python-код в терминале НЕ запускать (только `python -m py_compile file.py`)
- Для просмотра файлов: `Select-String -Path "app\..." -Pattern "..."`

---

## 3. АРХИТЕКТУРА БОТА (актуальная)

### Главное меню
📝 Описать состояние ← ОСНОВНОЙ сценарий
📔 Дневник
📋 История
📊 Моя динамика
📖 Как это работает?
👤 Профиль
⭐ Сома. PRO

### Основные сценарии

**1. «📝 Описать состояние»** (`describe_state.py`)
- Пользователь пишет свободный текст.
- AI отвечает в стиле Сомы.
- Продолжение — диалог (уточнения).
- Всё сохраняется в `diary_events` (`describe_user`, `describe_ai`, `analysis`, `clarification_*`).
- Кнопка «❌ Отмена» — просто выходит, БЕЗ AI и БЕЗ сохранений.

**2. Утреннее сообщение** (`reminder_service.py`)
- Каждый день в **9:00** по локальному времени пользователя (настраивается в профиле).
- Одно короткое сообщение (7 случайных вариантов) + одна кнопка «🌿 Описать состояние».
- Callback: `reminder_open_describe` → запускает `describe_state`.
- Флаг «сегодня отправлено» — `last_reminder_sent_at`.
- Whitelist-пользователи утреннее сообщение НЕ получают (`start_trial_if_needed` их пропускает).

**3. «📊 Моя динамика»** (`dynamics.py`)
- Периоды: 3, 7, 14, 30, 90 дней + свой период.
- **Доступна всем** (FREE, PRO, trial) — безлимит.
- AI получает **только записи пользователя** (`describe_user`) за период.
- Отвечает **текстом** (не JSON): 3 раздела — «Что повторялось», «Что изменилось», «Что понаблюдать».
- Заглушки:
  - **0 записей** → «Пока нечего анализировать» + [📝 Описать состояние]
  - **1-2 записи** → «Пока наблюдений немного» + [↩️ Назад]
  - **3+ записей** → обычный отчёт.

**4. Профиль** (`profile.py`)
- Показывает: подписка, утреннее сообщение, счётчик записей.
- Разделы: ⚙️ Настройки, 🔔 Утреннее сообщение, ⭐ PRO, 📋 История, 🔐 Конфиденциальность, ❓ Помощь.

**5. Напоминания** (`reminders.py` + `reminder_service.py`)
- Настройка: включить/выключить, время, дни недели.
- Default для новых: **enabled=True, time=09:00**.
- Можно изменить в профиле.

**6. PRO** (`pro.py`)
- **3 дня trial бесплатно** — стартует **автоматически** при первом «📝 Описать состояние».
- Тарифы: 1 мес / 490₽, 3 мес / 1290₽ (экономия 180₽), 6 мес / 2290₽ (экономия 650₽).
- Оплата: ЮKassa (тестовый магазин) — **не трогаем**.
- Whitelist (`pro_whitelist`) — работает как «PRO навсегда».

---

## 4. МОДЕЛЬ ПОДПИСКИ (новая)

### Статусы `SubscriptionStatus`
- `active` — платный PRO
- `expired` — истёк
- `cancelled` — отменён
- **`pro_trial`** — 3-дневный пробный PRO

### Логика доступа к «📝 Описать состояние»
    Первый вход → start_trial_if_needed() → 3 дня PRO_TRIAL

    Через 3 дня → TrialService переводит в EXPIRED

    После trial:

        1 бесплатный диалог (free_dialog_used=False → True)

        3 уточнения максимум (free_dialog_questions_count)

        После → PRO-предложение

    Whitelist → всегда PRO (trial не запускается)

    Платный PRO → безлимит

text


### Поля в `users`
- `trial_used` (bool) — был ли trial
- `trial_started_at`, `trial_ends_at` (timestamptz)
- `free_dialog_used` (bool)
- `free_dialog_questions_count` (int)

### Поля в `subscriptions`
- `plan` — `free` / `pro`
- `status` — `active` / `expired` / `cancelled` / `pro_trial`
- `expires_at` — конец периода

### Whitelist — `pro_whitelist`
- `user_id` (telegram_id)
- Даёт PRO навсегда, независимо от подписок.
- **Не трогать.**

---

## 5. БАЗА ДАННЫХ

### Основные таблицы
- `users` — пользователи (telegram_id, timezone, флаги trial/free_dialog, счётчики)
- `subscriptions` — подписки
- `pro_whitelist` — белый список PRO
- `diary_events` — **все** события (единая точка)
- `analyses` — анализы
- `clarifications` — уточнения
- `reminder_settings` — настройки утреннего сообщения
- `user_usage` — счётчики
- `payments` — платежи

### `diary_events` — ключевые поля
- `user_id` (внутренний ID из `users`)
- `event_type`: `describe_user`, `describe_ai`, `analysis`, `clarification_question`, `clarification_answer`, `dynamics_report`, `survey_*`
- `source`: `describe_state`, `dynamics`, `morning_survey` и т.д.
- `session_id` (uuid)
- `content` (text)
- `payload` (jsonb)
- `event_date` (**UTC!** — фильтр по датам делать через `created_at` + `timezone(user_tz)`)

### Enum-типы
- `subscriptionstatus`: `active`, `expired`, `cancelled`, `pro_trial` (нижний регистр)
- `plantype`: `free`, `pro`

⚠️ SQLAlchemy с `Enum` использует `.name` вместо `.value`. Решение: `values_callable=lambda x: [e.value for e in x]` в модели.

---

## 6. ОСНОВНЫЕ ФАЙЛЫ

app/
├── main.py # Запуск, регистрация роутеров, сервисы
├── config.py # settings (BOT_TOKEN, PRO_PRICE_RUB и т.д.)
├── db/
│ ├── models/
│ │ ├── user.py # User (с trial_used, free_dialog_*)
│ │ ├── subscription.py # Subscription (PRO_TRIAL, values_callable)
│ │ ├── diary_event.py # DiaryEvent
│ │ └── ...
│ └── repositories/
│ ├── diary_repository.py # get_events_by_date (с user_tz!)
│ ├── subscription.py # create_or_update_trial()
│ └── ...
├── services/
│ ├── ai_service.py # SOMA_BASE_PROMPT, DYNAMICS_PROMPT, describe_state()
│ ├── access_service.py # is_pro, start_trial_if_needed, can_start_new_describe_dialog
│ ├── reminder_service.py # Утреннее сообщение в 9:00
│ ├── trial_service.py # Перевод PRO_TRIAL → EXPIRED + напоминания 3/1/0
│ ├── payment_service.py # 3 тарифа, create_pro_payment(days, amount)
│ ├── dynamics_service.py # get_report() — текстовый отчёт
│ ├── dynamics_data_builder.py # build() + build_prompt() — только записи пользователя
│ ├── diary_event_service.py # record_event(), record_user_message(), record_ai_response()
│ └── ...
└── bot/
├── handlers/
│ ├── describe_state.py # ГЛАВНЫЙ сценарий + cancel_describe_state
│ ├── dynamics.py # «📊 Моя динамика»
│ ├── profile.py # Профиль
│ ├── reminders.py # Утреннее сообщение (настройки)
│ ├── pro.py # PRO (3 тарифа)
│ ├── menu.py # Кнопки главного меню
│ ├── how_it_works.py # «📖 Как это работает?»
│ ├── diary.py # «📔 Дневник» (за сегодня)
│ ├── history.py # «📋 История» (последние 50)
│ ├── survey_launcher.py # Обрабатывает старые callback'и (не используется)
│ └── ...
└── keyboards/
└── ...
text


---

## 7. ОСНОВНЫЕ ПРОМПТЫ (в `ai_service.py`)

- **`SOMA_BASE_PROMPT`** — базовый промпт Сомы. Ключевые правила:
  - Не додумывать за пользователя.
  - Не ставить диагнозы.
  - Не называть эмоции/причины, которые пользователь не называл.
  - Открытые вопросы без вариантов ответа.
  - Не начинать ответы с «Понимаю, что ты чувствуешь».
  - Не предлагать автоматически техники/упражнения.
  
- **`DYNAMICS_PROMPT`** — для динамики (текстовый, без JSON).
  - 3 раздела: «Что повторялось», «Что изменилось», «Что может быть интересно понаблюдать».
  - Без баллов, процентов, шкал, диагнозов, Синельникова.
  - Максимум 3-5 наблюдений.

- **`MORNING_SURVEY_PROMPT`, `DAY_SURVEY_PROMPT`, `EVENING_SURVEY_PROMPT`, `DESCRIBE_STATE_PROMPT`** — пустые заглушки (для совместимости).

---

## 8. АКТИВНЫЕ ФОНОВЫЕ СЕРВИСЫ (в `main.py`)

| Сервис | Что делает | Интервал |
|---|---|---|
| `ReminderService` | Утреннее сообщение в 9:00 | 10 сек |
| `PaymentReconciliationService` | Проверка «зависших» платежей | 60 сек |
| `TrialService` | PRO_TRIAL → EXPIRED, напоминания 3/1/0 дней | 60 сек |

**Отключены:**
- `SurveyScheduler` — опросы утро/день/вечер не используются.
- `morning/day/evening` роутеры — закомментированы в `handlers/__init__.py` и `main.py`.

---

## 9. КЛЮЧЕВЫЕ ПРАВИЛА ДЛЯ AI-АССИСТЕНТА

### ✅ Делаем:
- Даём **полный код файла** (не фрагменты), если нужно заменить.
- Комментируем изменения вверху кода.
- Учитываем, что ОС — **Windows + PowerShell**.
- Помним: **Alembic не используется**, миграции через **Adminer SQL**.
- Используем **`values_callable`** для enum в SQLAlchemy.
- При работе с датами всегда учитываем **timezone пользователя** (не UTC).

### ❌ НЕ делаем:
- **НЕ трогаем** `pro_whitelist` (whitelist).
- **НЕ трогаем** оплату ЮKassa (тестовый магазин) — работает как есть.
- **НЕ добавляем** функции, которых не просили.
- **НЕ возвращаем** опросы (утро/день/вечер).
- **НЕ используем** Синельникова или его подход.
- **НЕ делаем** динамику только для PRO — она для всех.
- **НЕ сохраняем** в БД при отмене диалога.
- **НЕ отправляем** запрос в AI, если пользователь нажал «❌ Отмена».
- **НЕ пишем** длинные промпты без необходимости.
- **НЕ даём** «диагнозы» и «причины».

---

## 10. ПРАВИЛА КОММУНИКАЦИИ С AI-АССИСТЕНТОМ

1. **Файлы** — присылаю **полным кодом**, если нужно заменить.
2. **Изменения** — даю **минимальные**, не переписываю всё.
3. **Логи** — присылаю **свежие**, с контекстом (5 строк до и 5 после ошибки).
4. **SQL** — выполняю **в Adminer**, присылаю скриншот результата.
5. **Деплой** — через **git + BotHost**.

---

## 11. ТЕКУЩИЙ СТАТУС (актуально на 26.09.2026)

### ✅ Работает:
- `describe_state` — с trial, free_dialog, cancel.
- Утреннее сообщение (9:00, 7 вариантов текста).
- PRO — 3 тарифа, trial 3 дня.
- Напоминания — настраиваемые через профиль.
- Динамика — текстовая, безлимит для всех.
- Whitelist — не даёт trial.
- Кнопка «❌ Отмена» — просто отмена.

### ⚠️ Известные нюансы:
- `edit_message_text failed` в `describe_state` — **норма**, fallback работает.
- `event_date` в `diary_events` — **в UTC**, фильтр по датам через `created_at` + `timezone()`.

### 🚫 Отключено (закомментировано):
- `SurveyScheduler`
- Роутеры `morning`, `day`, `evening`
- Промпты `MORNING_SURVEY_PROMPT` и др. — пустые заглушки

---

## 12. ЧАСТЫЕ ЗАДАЧИ

### Заменить промпт Сомы
- Файл: `app/services/ai_service.py`
- Заменить содержимое `SOMA_BASE_PROMPT`.
- Сохранить **другие** промпты без изменений.
- Задеплоить.

### Изменить тарифы PRO
- Файл: `app/bot/handlers/pro.py`
- Словарь `PRO_TARIFFS`.
- Кнопки в `get_pro_main_keyboard()`.
- Текст в `_get_pro_text()`.

### Изменить время утреннего сообщения
- Default — `app/db/repositories/reminder.py` → `get_or_create()`: `reminder_time=time(9, 0)`.
- Пользователь может изменить в профиле.

### Добавить новую функцию
- **Сначала спросить AI-ассистента** — куда встроить.
- Не ломать существующее.

---

**Версия:** 1.0 (26.09.2026)
**Контакт с AI-ассистентом:** прикрепляй этот файл в начале нового чата.

🎯 Как использовать

    Сохраните файл как PROJECT_CONTEXT.md в корне проекта.

    В новом чате — прикрепите его первым сообщением.

    Добавьте свой вопрос/задачу.

    AI-ассистент прочитает контекст и сразу поймёт проект.

Файл компактный (~500 строк), но покрывает всё ключевое. Если что-то забыли — скажите, добавлю. 🚀

### Поля в `users`
- `trial_used` (bool) — был ли trial
- `trial_started_at`, `trial_ends_at` (timestamptz)
- `free_dialog_used` (bool)
- `free_dialog_questions_count` (int)

### Поля в `subscriptions`
- `plan` — `free` / `pro`
- `status` — `active` / `expired` / `cancelled` / `pro_trial`
- `expires_at` — конец периода

### Whitelist — `pro_whitelist`
- `user_id` (telegram_id)
- Даёт PRO навсегда, независимо от подписок.
- **Не трогать.**

---

## 5. БАЗА ДАННЫХ

### Основные таблицы
- `users` — пользователи (telegram_id, timezone, флаги trial/free_dialog, счётчики)
- `subscriptions` — подписки
- `pro_whitelist` — белый список PRO
- `diary_events` — **все** события (единая точка)
- `analyses` — анализы
- `clarifications` — уточнения
- `reminder_settings` — настройки утреннего сообщения
- `user_usage` — счётчики
- `payments` — платежи

### `diary_events` — ключевые поля
- `user_id` (внутренний ID из `users`)
- `event_type`: `describe_user`, `describe_ai`, `analysis`, `clarification_question`, `clarification_answer`, `dynamics_report`, `survey_*`
- `source`: `describe_state`, `dynamics`, `morning_survey` и т.д.
- `session_id` (uuid)
- `content` (text)
- `payload` (jsonb)
- `event_date` (**UTC!** — фильтр по датам делать через `created_at` + `timezone(user_tz)`)

### Enum-типы
- `subscriptionstatus`: `active`, `expired`, `cancelled`, `pro_trial` (нижний регистр)
- `plantype`: `free`, `pro`

⚠️ SQLAlchemy с `Enum` использует `.name` вместо `.value`. Решение: `values_callable=lambda x: [e.value for e in x]` в модели.

---

## 6. ОСНОВНЫЕ ФАЙЛЫ
app/
├── main.py # Запуск, регистрация роутеров, сервисы
├── config.py # settings (BOT_TOKEN, PRO_PRICE_RUB и т.д.)
├── db/
│ ├── models/
│ │ ├── user.py # User (с trial_used, free_dialog_*)
│ │ ├── subscription.py # Subscription (PRO_TRIAL, values_callable)
│ │ ├── diary_event.py # DiaryEvent
│ │ └── ...
│ └── repositories/
│ ├── diary_repository.py # get_events_by_date (с user_tz!)
│ ├── subscription.py # create_or_update_trial()
│ └── ...
├── services/
│ ├── ai_service.py # SOMA_BASE_PROMPT, DYNAMICS_PROMPT, describe_state()
│ ├── access_service.py # is_pro, start_trial_if_needed, can_start_new_describe_dialog
│ ├── reminder_service.py # Утреннее сообщение в 9:00
│ ├── trial_service.py # Перевод PRO_TRIAL → EXPIRED + напоминания 3/1/0
│ ├── payment_service.py # 3 тарифа, create_pro_payment(days, amount)
│ ├── dynamics_service.py # get_report() — текстовый отчёт
│ ├── dynamics_data_builder.py # build() + build_prompt() — только записи пользователя
│ ├── diary_event_service.py # record_event(), record_user_message(), record_ai_response()
│ └── ...
└── bot/
├── handlers/
│ ├── describe_state.py # ГЛАВНЫЙ сценарий + cancel_describe_state
│ ├── dynamics.py # «📊 Моя динамика»
│ ├── profile.py # Профиль
│ ├── reminders.py # Утреннее сообщение (настройки)
│ ├── pro.py # PRO (3 тарифа)
│ ├── menu.py # Кнопки главного меню
│ ├── how_it_works.py # «📖 Как это работает?»
│ ├── diary.py # «📔 Дневник» (за сегодня)
│ ├── history.py # «📋 История» (последние 50)
│ ├── survey_launcher.py # Обрабатывает старые callback'и (не используется)
│ └── ...
└── keyboards/
└── ...
text


---

## 7. ОСНОВНЫЕ ПРОМПТЫ (в `ai_service.py`)

- **`SOMA_BASE_PROMPT`** — базовый промпт Сомы. Ключевые правила:
  - Не додумывать за пользователя.
  - Не ставить диагнозы.
  - Не называть эмоции/причины, которые пользователь не называл.
  - Открытые вопросы без вариантов ответа.
  - Не начинать ответы с «Понимаю, что ты чувствуешь».
  - Не предлагать автоматически техники/упражнения.
  
- **`DYNAMICS_PROMPT`** — для динамики (текстовый, без JSON).
  - 3 раздела: «Что повторялось», «Что изменилось», «Что может быть интересно понаблюдать».
  - Без баллов, процентов, шкал, диагнозов, Синельникова.
  - Максимум 3-5 наблюдений.

- **`MORNING_SURVEY_PROMPT`, `DAY_SURVEY_PROMPT`, `EVENING_SURVEY_PROMPT`, `DESCRIBE_STATE_PROMPT`** — пустые заглушки (для совместимости).

---

## 8. АКТИВНЫЕ ФОНОВЫЕ СЕРВИСЫ (в `main.py`)

| Сервис | Что делает | Интервал |
|---|---|---|
| `ReminderService` | Утреннее сообщение в 9:00 | 10 сек |
| `PaymentReconciliationService` | Проверка «зависших» платежей | 60 сек |
| `TrialService` | PRO_TRIAL → EXPIRED, напоминания 3/1/0 дней | 60 сек |

**Отключены:**
- `SurveyScheduler` — опросы утро/день/вечер не используются.
- `morning/day/evening` роутеры — закомментированы в `handlers/__init__.py` и `main.py`.

---

## 9. КЛЮЧЕВЫЕ ПРАВИЛА ДЛЯ AI-АССИСТЕНТА

### ✅ Делаем:
- Даём **полный код файла** (не фрагменты), если нужно заменить.
- Комментируем изменения вверху кода.
- Учитываем, что ОС — **Windows + PowerShell**.
- Помним: **Alembic не используется**, миграции через **Adminer SQL**.
- Используем **`values_callable`** для enum в SQLAlchemy.
- При работе с датами всегда учитываем **timezone пользователя** (не UTC).

### ❌ НЕ делаем:
- **НЕ трогаем** `pro_whitelist` (whitelist).
- **НЕ трогаем** оплату ЮKassa (тестовый магазин) — работает как есть.
- **НЕ добавляем** функции, которых не просили.
- **НЕ возвращаем** опросы (утро/день/вечер).
- **НЕ используем** Синельникова или его подход.
- **НЕ делаем** динамику только для PRO — она для всех.
- **НЕ сохраняем** в БД при отмене диалога.
- **НЕ отправляем** запрос в AI, если пользователь нажал «❌ Отмена».
- **НЕ пишем** длинные промпты без необходимости.
- **НЕ даём** «диагнозы» и «причины».

---

## 10. ПРАВИЛА КОММУНИКАЦИИ С AI-АССИСТЕНТОМ

1. **Файлы** — присылаю **полным кодом**, если нужно заменить.
2. **Изменения** — даю **минимальные**, не переписываю всё.
3. **Логи** — присылаю **свежие**, с контекстом (5 строк до и 5 после ошибки).
4. **SQL** — выполняю **в Adminer**, присылаю скриншот результата.
5. **Деплой** — через **git + BotHost**.

---

## 11. ТЕКУЩИЙ СТАТУС (актуально на 26.09.2026)

### ✅ Работает:
- `describe_state` — с trial, free_dialog, cancel.
- Утреннее сообщение (9:00, 7 вариантов текста).
- PRO — 3 тарифа, trial 3 дня.
- Напоминания — настраиваемые через профиль.
- Динамика — текстовая, безлимит для всех.
- Whitelist — не даёт trial.
- Кнопка «❌ Отмена» — просто отмена.

### ⚠️ Известные нюансы:
- `edit_message_text failed` в `describe_state` — **норма**, fallback работает.
- `event_date` в `diary_events` — **в UTC**, фильтр по датам через `created_at` + `timezone()`.

### 🚫 Отключено (закомментировано):
- `SurveyScheduler`
- Роутеры `morning`, `day`, `evening`
- Промпты `MORNING_SURVEY_PROMPT` и др. — пустые заглушки

---

## 12. ЧАСТЫЕ ЗАДАЧИ

### Заменить промпт Сомы
- Файл: `app/services/ai_service.py`
- Заменить содержимое `SOMA_BASE_PROMPT`.
- Сохранить **другие** промпты без изменений.
- Задеплоить.

### Изменить тарифы PRO
- Файл: `app/bot/handlers/pro.py`
- Словарь `PRO_TARIFFS`.
- Кнопки в `get_pro_main_keyboard()`.
- Текст в `_get_pro_text()`.

### Изменить время утреннего сообщения
- Default — `app/db/repositories/reminder.py` → `get_or_create()`: `reminder_time=time(9, 0)`.
- Пользователь может изменить в профиле.

### Добавить новую функцию
- **Сначала спросить AI-ассистента** — куда встроить.
- Не ломать существующее.

---

**Версия:** 1.0 (26.09.2026)
**Контакт с AI-ассистентом:** прикрепляй этот файл в начале нового чата.