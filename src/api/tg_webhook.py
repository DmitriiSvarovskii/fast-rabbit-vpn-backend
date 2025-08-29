import os
from fastapi import APIRouter, Request, HTTPException
from src.utils.tg_bot_api import tg_answer_pre_checkout_query
# from app.db import mark_paid, find_pending_by_payload ...  # твои функции

router = APIRouter()


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    # безопасность: проверяем секретный токен в заголовке
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != os.environ["WEBHOOK_SECRET"]:
        raise HTTPException(403, "bad secret")

    update = await request.json()

    # 1) pre_checkout_query
    pcq = update.get("pre_checkout_query")
    if pcq:
        qid = pcq["id"]
        payload = pcq.get("invoice_payload")
        # тут проверь, что payload существует и платёж ещё PENDING
        # ok = check_pending(payload)
        ok = True
        await tg_answer_pre_checkout_query(qid, ok=ok, error_message=None if ok else "Нельзя оплатить")
        return {"ok": True}

    # 2) успешная оплата (в message.successful_payment)
    msg = update.get("message") or {}
    sp = msg.get("successful_payment")
    if sp:
        payload = sp.get("invoice_payload")
        user_id = (msg.get("from") or {}).get("id")
        charge_id = sp.get("telegram_payment_charge_id")
        total_stars = sp.get("total_amount")
        # Найди PENDING по payload, проверь идемпотентность
        # Начисли пользователю баланс (сколько ₽ зачислять — по твоим правилам)
        # Сохрани charge_id, пометь платёж PAID
        # mark_paid(payload, user_id, total_stars, charge_id)
        return {"ok": True}

    # Можно игнорить остальные апдейты
    return {"ok": True}
