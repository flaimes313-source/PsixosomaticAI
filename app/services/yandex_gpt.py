"""
Клиент YandexGPT API.

Этот модуль отвечает только за взаимодействие
с Yandex Cloud Foundation Models API.

Здесь НЕ должно быть Telegram-логики.
"""

import asyncio
from typing import Any, Optional

import httpx

from app.config import settings
from app.utils.logging import logger


class YandexGPTError(Exception):
    """Базовая ошибка YandexGPT."""


class YandexGPTClient:
    """
    Асинхронный клиент YandexGPT.

    Ответственность класса:

    - формирование HTTP-запроса;
    - авторизация;
    - отправка запроса;
    - обработка ошибок;
    - timeout;
    - retry.

    Telegram и FSM здесь отсутствуют специально.
    """

    API_URL = (
        "https://llm.api.cloud.yandex.net/"
        "foundationModels/v1/completion"
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        folder_id: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or settings.YANDEX_API_KEY
        self.folder_id = folder_id or settings.YANDEX_FOLDER_ID
        self.model = model or settings.YANDEX_MODEL
        self.timeout = timeout or settings.YANDEX_TIMEOUT
        self.max_retries = (
            max_retries
            if max_retries is not None
            else settings.YANDEX_MAX_RETRIES
        )

        if not self.api_key:
            raise ValueError(
                "YANDEX_API_KEY не задан в конфигурации."
            )

        if not self.folder_id:
            raise ValueError(
                "YANDEX_FOLDER_ID не задан в конфигурации."
            )

    @property
    def model_uri(self) -> str:
        """
        URI модели YandexGPT.

        Пример:

        gpt://folder_id/yandexgpt/latest
        """

        return (
            f"gpt://{self.folder_id}/{self.model}"
        )

    def _build_headers(self) -> dict[str, str]:
        """Формирует HTTP-заголовки."""

        return {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Формирует тело запроса."""

        return {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": 2000,
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt,
                },
                {
                    "role": "user",
                    "text": user_prompt,
                },
            ],
        }

    @staticmethod
    def _extract_text(response_data: dict[str, Any]) -> str:
        """
        Извлекает текст из ответа YandexGPT.

        Ожидаемая структура:

        result.alternatives[0].message.text
        """

        try:
            alternatives = (
                response_data
                .get("result", {})
                .get("alternatives", [])
            )

            if not alternatives:
                raise YandexGPTError(
                    "YandexGPT вернул пустой список alternatives."
                )

            message = alternatives[0].get("message", {})
            text = message.get("text")

            if not text:
                raise YandexGPTError(
                    "YandexGPT вернул пустой текст ответа."
                )

            return text.strip()

        except AttributeError as exc:
            raise YandexGPTError(
                "Не удалось разобрать ответ YandexGPT."
            ) from exc

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Отправляет запрос в YandexGPT и возвращает текст ответа.

        При временных ошибках выполняется retry.
        """

        payload = self._build_payload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        headers = self._build_headers()

        logger.info(
            "YandexGPT request started: "
            f"model={self.model}, "
            f"folder_id={self.folder_id}"
        )

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout
                ) as client:

                    response = await client.post(
                        self.API_URL,
                        headers=headers,
                        json=payload,
                    )

                if response.status_code == 200:
                    response_data = response.json()

                    text = self._extract_text(
                        response_data
                    )

                    logger.info(
                        "YandexGPT request completed successfully"
                    )

                    return text

                # Ошибки авторизации / конфигурации
                if response.status_code in (400, 401, 403):
                    error_text = response.text[:1000]

                    logger.error(
                        "YandexGPT API configuration/auth error: "
                        f"status={response.status_code}, "
                        f"response={error_text}"
                    )

                    raise YandexGPTError(
                        "Ошибка авторизации или конфигурации "
                        "YandexGPT API. "
                        f"HTTP {response.status_code}"
                    )

                # Временные ошибки сервера
                if response.status_code in (
                    429,
                    500,
                    502,
                    503,
                    504,
                ):
                    error_text = response.text[:1000]

                    last_error = YandexGPTError(
                        "Временная ошибка YandexGPT: "
                        f"HTTP {response.status_code}. "
                        f"{error_text}"
                    )

                    logger.warning(
                        "YandexGPT temporary error: "
                        f"attempt={attempt + 1}/"
                        f"{self.max_retries + 1}, "
                        f"status={response.status_code}"
                    )

                    if attempt < self.max_retries:
                        await asyncio.sleep(
                            2 ** attempt
                        )
                        continue

                    raise last_error

                # Остальные HTTP ошибки
                error_text = response.text[:1000]

                logger.error(
                    "YandexGPT unexpected HTTP error: "
                    f"status={response.status_code}, "
                    f"response={error_text}"
                )

                raise YandexGPTError(
                    "Неожиданная ошибка YandexGPT API: "
                    f"HTTP {response.status_code}"
                )

            except httpx.TimeoutException as exc:
                last_error = exc

                logger.warning(
                    "YandexGPT timeout: "
                    f"attempt={attempt + 1}/"
                    f"{self.max_retries + 1}"
                )

                if attempt < self.max_retries:
                    await asyncio.sleep(
                        2 ** attempt
                    )
                    continue

                raise YandexGPTError(
                    "YandexGPT не ответил вовремя."
                ) from exc

            except httpx.RequestError as exc:
                last_error = exc

                logger.warning(
                    "YandexGPT network error: "
                    f"attempt={attempt + 1}/"
                    f"{self.max_retries + 1}, "
                    f"error={type(exc).__name__}"
                )

                if attempt < self.max_retries:
                    await asyncio.sleep(
                        2 ** attempt
                    )
                    continue

                raise YandexGPTError(
                    "Не удалось подключиться "
                    "к YandexGPT API."
                ) from exc

        raise YandexGPTError(
            "Не удалось получить ответ YandexGPT."
        ) from last_error