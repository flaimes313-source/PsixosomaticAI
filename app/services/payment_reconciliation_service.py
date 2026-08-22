"""
Сервис для сверки зависших платежей.
"""
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.repositories.payment import PaymentRepository
from app.services.yookassa_service import YooKassaService
from app.services.payment_service import PaymentService
from app.utils.logging import logger


class PaymentReconciliationService:
    """Сервис для проверки зависших платежей."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.running = False
        self.task = None

    async def start(self):
        """Запускает шедулер сверки."""
        if self.running:
            logger.warning("PaymentReconciliationService already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._reconciliation_loop())
        logger.info("✅ PaymentReconciliationService started")

    async def stop(self):
        """Останавливает шедулер."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        logger.info("PaymentReconciliationService stopped")

    async def _reconciliation_loop(self):
        """Основной цикл сверки."""
        logger.info("🔄 Payment reconciliation loop started")
        while self.running:
            try:
                await self._check_pending_payments()
                await asyncio.sleep(300)  # Проверяем каждые 5 минут
            except Exception as e:
                logger.error(f"Error in payment reconciliation loop: {e}")
                await asyncio.sleep(300)

    async def _check_pending_payments(self):
        """Проверяет зависшие платежи."""
        async with self.session_factory() as session:
            payment_repo = PaymentRepository(session)
            
            # Находим платежи в статусе PENDING старше 5 минут
            pending_payments = await payment_repo.get_pending_payments(older_than_minutes=5)
            
            if not pending_payments:
                return
            
            logger.info(f"🔍 Checking {len(pending_payments)} pending payments")
            
            yookassa = YooKassaService()
            
            for payment in pending_payments:
                if not payment.provider_payment_id:
                    continue
                
                # Проверяем статус в ЮKassa
                status = await yookassa.check_payment_status(payment.provider_payment_id)
                
                if status == "succeeded":
                    # Платёж успешен — обрабатываем
                    logger.info(f"✅ Found succeeded payment: {payment.provider_payment_id}")
                    payment_service = PaymentService(session)
                    await payment_service.process_successful_webhook(
                        payment.provider_payment_id,
                        {}
                    )
                elif status == "canceled":
                    # Платёж отменён
                    logger.info(f"❌ Payment cancelled: {payment.provider_payment_id}")
                    await payment_repo.mark_cancelled(payment.id)
                elif status == "pending":
                    # Всё ещё в обработке
                    logger.info(f"⏳ Payment still pending: {payment.provider_payment_id}")
                else:
                    logger.warning(f"⚠️ Unknown status {status} for payment {payment.provider_payment_id}")