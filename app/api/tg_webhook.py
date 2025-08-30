from aiogram import Bot
import os
from fastapi import APIRouter, Request, HTTPException
from app.utils.tg_bot_api import tg_answer_pre_checkout_query
# from app.db import mark_paid, find_pending_by_payload ...  # твои функции
from app.core.models.wallet_ledger import WalletEntry
import os
from decimal import Decimal
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Depends, status
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db.postgres import get_async_session
from app.core.consts import LedgerType, PaymentStatus
from app.core.configs.bot import bot_settings
from app.core.models.payments import Payment
from app.core.models.users import User
router = APIRouter()
from uuid import uuid4


async def get_bot() -> Bot:
    """
    Minimal Bot instance provider.
    NOTE: In production, consider a singleton Bot shared in app state to avoid
    creating a new session per request.
    """
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")
    return Bot(token=token)


# ===== Routes =====
def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _credit_if_absent(
    db: AsyncSession,
    *,
    user_id: int,
    payment_id: int,
    amount_rub: Decimal,
    comment: str | None = None,
):
    """Создаёт строку в кошельке, если её ещё нет для этого платежа (идемпотентно)."""
    already = (await db.execute(
        select(exists().where(WalletEntry.payment_id == payment_id))
    )).scalar()
    if already:
        return
    db.add(WalletEntry(
        user_id=user_id,
        payment_id=payment_id,
        entry_type=LedgerType.TOPUP,   # твой enum
        amount_rub=Decimal(amount_rub),  # >0
        comment=comment,
    ))


def get_bot_token() -> str:
    # В реальном проекте подтяни из ENV/Secret Manager
    # например: os.environ["TELEGRAM_BOT_TOKEN"]
    return bot_settings.BOT_TOKEN


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    bot: Bot = Depends(get_bot),
):
    # 0) Безопасность вебхука
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != os.environ.get("WEBHOOK_SECRET"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "bad secret")

    update = await request.json()

    # 1) pre_checkout_query — подтверждаем только PENDING-инвойсы
    pcq = update.get("pre_checkout_query")
    if pcq:
        qid = pcq["id"]
        payload = pcq.get("invoice_payload")
        ok = False
        if payload:
            status_ = (await db.execute(
                select(Payment.status).where(Payment.payload == payload)
            )).scalar_one_or_none()
            ok = status_ == PaymentStatus.PENDING
        await tg_answer_pre_checkout_query(qid, ok=ok, error_message=None if ok else "Invoice is not available")
        return {"ok": True}

    # 2) успешная оплата
    msg = update.get("message") or {}
    sp = msg.get("successful_payment")
    if sp:
        payload = sp.get("invoice_payload")
        telegram_id = (msg.get("from") or {}).get("id")  # ← telegram_id пользователя
        charge_id = sp.get("telegram_payment_charge_id")
        total_stars = sp.get("total_amount")            # Stars (XTR), int
        currency = sp.get("currency")                   # "XTR"

        # базовая валидация входа
        if not payload or telegram_id is None or total_stars is None:
            return {"ok": True}  # игнорируем кривые апдейты без 500

        # транзакция: фиксируем платёж и создаём запись в кошельке
        async with db.begin():
            # Находим пользователя по telegram_id (BIGINT)
            user = (await db.execute(
                select(User).where(User.telegram_id == int(telegram_id))
            )).scalar_one_or_none()
            if not user:
                # если такого юзера нет — безопасно выходим
                return {"ok": True}

            # Лочим платёж по payload (FOR UPDATE), убеждаемся, что он принадлежит этому юзеру
            payment = (await db.execute(
                select(Payment).where(Payment.payload == payload).with_for_update()
            )).scalar_one_or_none()
            if payment is None:
                return {"ok": True}
            if payment.user_id != user.id:
                # чужой payload — не трогаем
                return {"ok": True}

            # Идемпотентность: повторные апдейты
            if payment.status == PaymentStatus.PAID:
                await _credit_if_absent(
                    db,
                    user_id=user.id,
                    payment_id=payment.id,
                    amount_rub=payment.rub_amount,
                    comment=f"Top-up via Stars (idemp)",
                )
                return {"ok": True}
            if payment.status != PaymentStatus.PENDING:
                # FAILED/CANCELED — ничего не делаем
                return {"ok": True}

            # Доп.проверка суммы в звёздах (учти, что на создании мог быть ceil)
            if isinstance(payment.stars_amount, int) and total_stars < payment.stars_amount:
                payment.status = PaymentStatus.FAILED
                payment.failed_reason = f"Stars mismatch: expected {payment.stars_amount}, got {total_stars}"
                payment.telegram_charge_id = charge_id
                payment.paid_at = None
                payment.canceled_at = None
                return {"ok": True}

            # Обновляем платёж → PAID
            payment.status = PaymentStatus.PAID
            payment.telegram_charge_id = charge_id
            payment.paid_at = _utcnow()
            payment.failed_reason = None
            payment.canceled_at = None

            # Начисляем в кошелёк (рубли берём из payment.rub_amount, НЕ пересчитываем)
            await _credit_if_absent(
                db,
                user_id=user.id,
                payment_id=payment.id,
                amount_rub=payment.rub_amount,
                comment=f"Top-up via Stars #{payment.id}",
            )

        # commit произойдёт по выходу из with
        return {"ok": True}

    # Остальные апдейты игнорим
    return {"ok": True}

# @router.post("/telegram/webhook")
# async def telegram_webhook(request: Request):
#     # безопасность: проверяем секретный токен в заголовке
#     secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
#     if secret != os.environ["WEBHOOK_SECRET"]:
#         raise HTTPException(403, "bad secret")

#     update = await request.json()

#     # 1) pre_checkout_query
#     pcq = update.get("pre_checkout_query")
#     if pcq:
#         qid = pcq["id"]
#         payload = pcq.get("invoice_payload")
#         # тут проверь, что payload существует и платёж ещё PENDING
#         # ok = check_pending(payload)
#         ok = True
#         await tg_answer_pre_checkout_query(qid, ok=ok, error_message=None if ok else "Нельзя оплатить")
#         return {"ok": True}

#     # 2) успешная оплата (в message.successful_payment)
#     msg = update.get("message") or {}
#     sp = msg.get("successful_payment")
#     if sp:
#         payload = sp.get("invoice_payload")
#         user_id = (msg.get("from") or {}).get("id")
#         charge_id = sp.get("telegram_payment_charge_id")
#         total_stars = sp.get("total_amount")
#         # Найди PENDING по payload, проверь идемпотентность
#         # Начисли пользователю баланс (сколько ₽ зачислять — по твоим правилам)
#         # Сохрани charge_id, пометь платёж PAID
#         # mark_paid(payload, user_id, total_stars, charge_id)
#         return {"ok": True}

#     # Можно игнорить остальные апдейты
#     return {"ok": True}
