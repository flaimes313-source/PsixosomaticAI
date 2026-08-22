"""
Webhook для обработки уведомлений от ЮKassa.
"""
import json
from fastapi import APIRouter, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.services.payment_service import PaymentService
from app.utils.logging import logger

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/yookassa")
async def yookassa_webhook(request: Request):
    """
    Обработка webhook от ЮKassa.
    """
    try:
        # Получаем тело запроса
        body = await request.body()
        data = json.loads(body)
        
        logger.info(f"YooKassa webhook received: {data.get('event')}")
        
        # Проверяем событие
        event = data.get("event")
        if event != "payment.succeeded":
            logger.info(f"Ignoring event: {event}")
            return Response(status_code=200)
        
        # Получаем объект платежа
        payment_obj = data.get("object", {})
        provider_payment_id = payment_obj.get("id")
        
        if not provider_payment_id:
            logger.error("No payment id in webhook")
            return Response(status_code=400)
        
        # Обрабатываем платеж в БД
        async with AsyncSessionLocal() as db_session:
            payment_service = PaymentService(db_session)
            result = await payment_service.process_successful_webhook(
                provider_payment_id=provider_payment_id,
                event_data=data,
            )
            
            if result.get("success"):
                logger.info(f"Payment processed successfully: {provider_payment_id}")
                return Response(status_code=200)
            else:
                logger.error(f"Payment processing failed: {result.get('error')}")
                return Response(status_code=400)
                
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        return Response(status_code=400)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(status_code=500)