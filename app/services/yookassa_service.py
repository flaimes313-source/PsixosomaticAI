"""
Сервис для работы с API ЮKassa.
"""
import uuid
import json
from typing import Optional, Dict, Any
from decimal import Decimal
import httpx

from app.config import settings
from app.utils.logging import logger


class YooKassaService:
    """Сервис для взаимодействия с API ЮKassa."""

    def __init__(self):
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY
        self.api_url = "https://api.yookassa.ru/v3"
        self.return_url = settings.YOOKASSA_RETURN_URL
        
        # Basic auth
        import base64
        auth_str = f"{self.shop_id}:{self.secret_key}"
        self.auth_header = base64.b64encode(auth_str.encode()).decode()

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        return_url: str,
        metadata: Dict[str, str],
        idempotence_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Создать платеж в ЮKassa.
        """
        if not idempotence_key:
            idempotence_key = str(uuid.uuid4())

        payload = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": currency
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": description,
            "metadata": metadata,
        }

        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
            "Idempotence-Key": idempotence_key,
        }

        logger.info(f"Creating YooKassa payment: amount={amount}, currency={currency}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/payments",
                    json=payload,
                    headers=headers,
                )
                
                if response.status_code != 200:
                    logger.error(f"YooKassa API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                        "response": response.json() if response.text else None,
                    }
                
                data = response.json()
                logger.info(f"YooKassa payment created: {data.get('id')}")
                
                return {
                    "success": True,
                    "payment_id": data.get("id"),
                    "status": data.get("status"),
                    "confirmation_url": data.get("confirmation", {}).get("confirmation_url"),
                    "data": data,
                }

        except httpx.TimeoutException:
            logger.error("YooKassa API timeout")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"YooKassa API error: {e}")
            return {"success": False, "error": str(e)}

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Получить информацию о платеже.
        """
        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
        }

        logger.info(f"Getting YooKassa payment: {payment_id}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/payments/{payment_id}",
                    headers=headers,
                )
                
                if response.status_code != 200:
                    logger.error(f"YooKassa API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                    }
                
                data = response.json()
                logger.info(f"YooKassa payment retrieved: {data.get('id')}")
                
                return {
                    "success": True,
                    "data": data,
                }

        except httpx.TimeoutException:
            logger.error("YooKassa API timeout")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"YooKassa API error: {e}")
            return {"success": False, "error": str(e)}

    async def check_payment_status(self, payment_id: str) -> Optional[str]:
        """Проверить статус платежа."""
        result = await self.get_payment(payment_id)
        if not result.get("success"):
            return None
        return result.get("data", {}).get("status")