import os
import httpx
from app.core.configs.bot import bot_settings

BOT_API = f"https://api.telegram.org/bot{bot_settings.BOT_TOKEN}"


async def tg_create_invoice_link(*, title, description, payload, stars: int):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{BOT_API}/createInvoiceLink", json={
            "title": title,
            "description": description,
            "payload": payload,
            "currency": "XTR",
            "prices": [{"label": title, "amount": stars}],
        })
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"createInvoiceLink error: {data}")
        return data["result"]


async def tg_answer_pre_checkout_query(query_id: str, ok: bool, error_message: str | None = None):
    async with httpx.AsyncClient(timeout=10) as client:
        payload = {"pre_checkout_query_id": query_id, "ok": ok}
        if not ok and error_message:
            payload["error_message"] = error_message
        r = await client.post(f"{BOT_API}/answerPreCheckoutQuery", json=payload)
        r.raise_for_status()
        return r.json()


# опционально для возвратов
async def tg_refund_star_payment(user_id: int, charge_id: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{BOT_API}/refundStarPayment", json={
            "user_id": user_id,
            "telegram_payment_charge_id": charge_id
        })
        r.raise_for_status()
        return r.json()
