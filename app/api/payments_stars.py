# app/api/payments_stars.py

from sqlalchemy import select
from app.core.models.payments import Payment
from app.core.models.users import User
from app.core.db.postgres import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from app.api.jwt_auth import require_jwt
import math
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Depends, status
from pydantic import BaseModel, Field

from aiogram import Bot
from aiogram.types import LabeledPrice

from app.utils.telegram_webapp import validate_webapp_init_data
from app.core.consts import LedgerType, PaymentStatus

router = APIRouter(prefix="/payments/stars", tags=["payments-stars"])

# Business rules / limits
XTR_PER_RUB = float(os.getenv("XTR_PER_RUB", "0.5"))   # e.g. 1₽ = 0.5⭐
MIN_RUB = int(os.getenv("MIN_TOPUP_RUB", "10"))
MAX_RUB = int(os.getenv("MAX_TOPUP_RUB", "50000"))


# ===== Schemas =====

class CreateInvoiceRequest(BaseModel):
    amount_rub: int = Field(..., ge=1, description="Top-up amount in RUB")


class CreateInvoiceResponse(BaseModel):
    invoice_link: str
    stars: int
    payload: str


# ===== Dependencies =====

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


@router.post("/invoice", response_model=CreateInvoiceResponse, status_code=status.HTTP_200_OK)
async def create_invoice(
    body: CreateInvoiceRequest,
    bot: Bot = Depends(get_bot),
    token: dict = Depends(require_jwt),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Создаёт Telegram Stars (XTR) инвойс и фиксирует PENDING-платёж в БД (идемпотентно по payload).
    Пользователь берётся из JWT (payload['sub'] = telegram_id).
    """
    # 1) Валидация суммы
    if body.amount_rub < MIN_RUB or body.amount_rub > MAX_RUB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Сумма должна быть от {MIN_RUB} до {MAX_RUB} ₽",
        )

    # 2) Пользователь по telegram_id из токена
    telegram_id = int(token["sub"])
    user = (
        await db.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # 3) Пересчёт в звёзды (целое, вверх)
    stars = int(math.ceil(Decimal(str(body.amount_rub)) * XTR_PER_RUB))
    if stars <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недопустимая сумма в звёздах")

    # 4) Идемпотентный payload (привязываем к tg_id и сумме)
    payload = f"topup:{telegram_id}:{body.amount_rub}:v1"

    # 5) Запись платежа PENDING (или переиспользуем, если уже есть)
    async with db.begin():
        payment = (
            await db.execute(select(Payment).where(Payment.payload == payload).with_for_update())
        ).scalar_one_or_none()

        if payment is None:
            payment = Payment(
                user_id=user.id,                 # внутренний id пользователя
                payload=payload,
                rub_amount=Decimal(str(body.amount_rub)),
                stars_amount=stars,
                status=PaymentStatus.PENDING,
                currency="XTR",
            )
            db.add(payment)
            # commit произойдёт по выходу из begin()

        else:
            # Если уже оплачен/завален — не даём повторить с тем же payload
            if payment.status == PaymentStatus.PAID:
                raise HTTPException(status.HTTP_409_CONFLICT, "Invoice already paid")
            if payment.status != PaymentStatus.PENDING:
                raise HTTPException(status.HTTP_409_CONFLICT, f"Invoice is {payment.status}")

            # На всякий случай обновим суммы, если логика пересчёта менялась
            payment.rub_amount = Decimal(str(body.amount_rub))
            payment.stars_amount = stars
            payment.currency = "XTR"

    # 6) Создание ссылки на оплату в Stars
    link = await bot.create_invoice_link(
        title="Пополнение баланса",
        description=f"Пополнение на {body.amount_rub} ₽ (~{stars} ⭐️)",
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label="Balance top-up", amount=stars)],
        # subscription_period=2592000,  # если когда-нибудь понадобятся подписки
    )

    return CreateInvoiceResponse(invoice_link=link, stars=stars, payload=payload)
# ===== Routes =====

# @router.post("/invoice", response_model=CreateInvoiceResponse)
# async def create_invoice(
#     body: CreateInvoiceRequest,
#     bot: Bot = Depends(get_bot),
#     # init_data: Optional[str] = Header(
#     #     default=None, alias="X-Telegram-Init-Data"),
#         token: dict = Depends(require_jwt),

# ):
#     """
#     Creates a Telegram Stars (XTR) invoice link for a WebApp user.
#     Frontend must pass WebApp initData in 'X-Telegram-Init-Data' header.
#     """
#     # Basic amount validation
#     if body.amount_rub < MIN_RUB or body.amount_rub > MAX_RUB:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Сумма должна быть от {MIN_RUB} до {MAX_RUB} ₽",
#         )

#     # if not init_data:
#     #     raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing init data")

#     # # Validate WebApp initData signature
#     # try:
#     #     parsed = validate_webapp_init_data(init_data, os.environ["BOT_TOKEN"])
#     # except Exception as e:
#     #     raise HTTPException(status.HTTP_401_UNAUTHORIZED,
#     #                         f"Bad init data: {e}")

#     # user = parsed.get("user_obj") or {}
#     # user_id = user.get("id")
#     # if not user_id:
#     #     raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No user id")
#     user_id = token.get('sub')
#     # Convert RUB -> Stars (integer, ceil to avoid undercharging)
#     stars = int(math.ceil(body.amount_rub * XTR_PER_RUB))
#     if stars <= 0:
#         raise HTTPException(status.HTTP_400_BAD_REQUEST,
#                             "Недопустимая сумма в звёздах")

#     # Idempotent payload – tie to user and amount
#     payload = f"topup:{user_id}:{body.amount_rub}:v1"

#     # TODO: persist a PENDING payment record in DB before creating invoice
#     # save_pending_payment(user_id=user_id, payload=payload, rub=body.amount_rub, stars=stars)

#     # Create invoice link in Stars (currency='XTR'; provider_token is NOT used for digital goods)
#     link = await bot.create_invoice_link(
#         title="Пополнение баланса",
#         description=f"Пополнение на {body.amount_rub} ₽ (~{stars} ⭐️)",
#         payload=payload,
#         currency="XTR",
#         prices=[LabeledPrice(label="Balance top-up", amount=stars)],
#         # subscription_period=2592000,  # uncomment if you need a 30-day subscription product
#     )

#     return CreateInvoiceResponse(invoice_link=link, stars=stars, payload=payload)


@router.get("/status")
async def status_endpoint(
    payload: str,
    init_data: Optional[str] = Header(
        default=None, alias="X-Telegram-Init-Data"),
):
    """
    Returns current status of the given payment payload for the authenticated WebApp user.
    """
    # Optional but recommended: verify init data to ensure the caller is legitimate
    try:
        validate_webapp_init_data(init_data or "", os.environ["BOT_TOKEN"])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad init data")

    # TODO: fetch payment record by payload from DB and return real status
    # rec = get_payment_by_payload(payload)
    # if not rec: raise HTTPException(404, "Payment not found")
    # return {"payload": payload, "status": rec.status, "rub": rec.rub, "stars": rec.stars}

    return {"payload": payload, "status": "UNKNOWN"}
