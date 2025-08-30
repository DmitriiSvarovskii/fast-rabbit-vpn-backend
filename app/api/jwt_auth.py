# app/security/jwt_auth.py
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
import time
import os
import json
import base64
import jwt  # pip install PyJWT
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Tuple, Any
import base64
import hashlib
import hmac
import time
from typing import Dict, Tuple, Any
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from nacl.signing import VerifyKey
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.db.postgres import get_async_session
from app.core.models.users import User
from app.core.models.wallet_ledger import WalletEntry
from app.core.models.vpn_configs import VpnConfig
from app.core.schemas.user_full import UserFullInfo, TokenResponse
from app.core.schemas.user_balance import UserBalanceBase
from app.core.schemas.key import KeyBase
from app.core.configs.vpn_config import vpn_settings
from datetime import datetime
from app.core.configs.bot import bot_settings

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
JWT_ALG = "HS256"
JWT_TTL = 10 * 60  # 10 минут

router = APIRouter(prefix="/auth", tags=["auth"])


# Telegram Ed25519 public keys (hex)
TG_PUBKEY_TEST = "40055058a4ee38156a06562e52eece92a771bcd8346a8c4615cb7376eddf72ec"
TG_PUBKEY_PROD = "e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d"


# ---- Utility helpers ----

def parse_init_data(init_data: str) -> Dict[str, str]:
    """
    Parse query-string from Telegram.WebApp.initData into a dict (keeps last occurrence on duplicates).
    """
    return dict(parse_qsl(init_data, keep_blank_values=True))


def build_data_check_string(fields: Dict[str, str]) -> Tuple[str, str]:
    """
    Build data_check_string for server-side validation (HMAC path).
    Exclude only 'hash' field. Sort keys alphabetically.
    Returns (data_check_string, received_hash_hex)
    """
    received_hash = fields.get("hash") or ""
    items = [(k, v) for k, v in fields.items() if k != "hash"]
    items.sort(key=lambda kv: kv[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in items)
    return data_check_string, received_hash


def compute_secret_key(bot_token: str) -> bytes:
    """
    secret_key = HMAC_SHA256(message=bot_token, key="WebAppData")
    """
    return hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()


def verify_hmac(init_data: str, bot_token: str, max_age_sec: int = 24 * 3600000000000) -> Dict[str, Any]:
    """
    Server-side verification using 'hash' (HMAC-SHA256).
    Raises HTTPException on failure.
    Returns parsed fields.
    """
    fields = parse_init_data(init_data)
    data_check_string, received_hash = build_data_check_string(fields)

    if not received_hash:
        raise HTTPException(status_code=400, detail="Missing 'hash'")

    secret_key = compute_secret_key(bot_token)
    calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid hash")

    # freshness check
    try:
        auth_date = int(fields.get("auth_date", "0"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid 'auth_date'")

    now = int(time.time())
    delta = now - auth_date
    print(f"[tg-verify] now={now} auth_date={auth_date} delta={delta}s max_age_sec={max_age_sec}")
    if auth_date <= 0 or now - auth_date > max_age_sec:
        raise HTTPException(status_code=401, detail="Stale auth_date")

    return fields


def b64url_decode_nopad(s: str) -> bytes:
    """
    Base64url decode with optional missing padding.
    """
    s = s.replace("-", "+").replace("_", "/")
    pad = (-len(s)) % 4
    if pad:
        s += "=" * pad
    return base64.b64decode(s)


def build_third_party_dcs(fields: Dict[str, str], bot_id: str) -> Tuple[str, bytes]:
    """
    Build data_check_string for third-party validation (Ed25519 path).
    Exclude 'hash' and 'signature'. Sort keys alphabetically.
    Returns (data_check_string, signature_bytes)
    """
    signature_b64u = fields.get("signature") or ""
    if not signature_b64u:
        raise HTTPException(status_code=400, detail="Missing 'signature'")
    try:
        signature = b64url_decode_nopad(signature_b64u)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64url 'signature'")

    items = [(k, v) for k, v in fields.items() if k not in ("hash", "signature")]
    items.sort(key=lambda kv: kv[0])
    tail = "\n".join(f"{k}={v}" for k, v in items)
    dcs = f"{bot_id}:WebAppData\n{tail}"
    return dcs, signature


def verify_third_party(init_data: str, bot_id: str, env: str = "prod", max_age_sec: int = 24 * 360000) -> Dict[str, Any]:
    """
    Third-party validation using Ed25519 'signature' and Telegram public key.
    env: "prod" or "test"
    """
    fields = parse_init_data(init_data)
    dcs, signature = build_third_party_dcs(fields, bot_id)

    pub_hex = TG_PUBKEY_PROD if env == "prod" else TG_PUBKEY_TEST
    verify_key = VerifyKey(bytes.fromhex(pub_hex))
    try:
        # Ed25519 verify: raises BadSignatureError if invalid
        verify_key.verify(dcs.encode("utf-8"), signature)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Ed25519 signature")

    # freshness check
    try:
        auth_date = int(fields.get("auth_date", "0"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid 'auth_date'")

    now = int(time.time())
    if auth_date <= 0 or now - auth_date > max_age_sec:
        raise HTTPException(status_code=401, detail="Stale auth_date")

    return fields


# ---- Request/Response models ----

class VerifyRequest(BaseModel):
    init_data: str
    mode: str = "hmac"         # "hmac" | "third_party"
    env: str = "prod"          # "prod" | "test"
    max_age_sec: int = 24 * 3600000


class VerifyResponse(BaseModel):
    ok: bool
    fields: Dict[str, Any]


# ---- Dependencies you may wire from your settings/env ----

def get_bot_token() -> str:
    # В реальном проекте подтяни из ENV/Secret Manager
    # например: os.environ["TELEGRAM_BOT_TOKEN"]
    return bot_settings.BOT_TOKEN


def get_bot_id() -> str:
    # Целое число id бота без @. Можно хранить в настройках/ENV.
    return bot_settings.BOT_ID


def build_vless_link(cfg: VpnConfig) -> str:
    return (
        f"vless://{cfg.uuid}@{cfg.vpn_domain}:443"
        f"?flow={cfg.flow or 'xtls-rprx-vision'}&type=tcp&security=reality"
        f"&fp=random&sni={vpn_settings.SNI}&pbk={vpn_settings.PBK}"
        f"&sid={vpn_settings.SID}&spx=/#" + (cfg.email or "vpn-user")
    )


# class TokenResponse(BaseModel):
#     access_token: str
#     token_type: str = "bearer"
#     expires_in: int = JWT_TTL


@router.post("/telegram", response_model=UserFullInfo)
async def exchange_initdata_for_jwt(
    x_tg_init_data: str = Header(alias="X-Telegram-WebApp-InitData"),
    bot_token: str = Depends(get_bot_token),
    db: AsyncSession = Depends(get_async_session),

):
    fields = verify_hmac(x_tg_init_data, bot_token=bot_token, max_age_sec=10 * 6000000)

    user_raw = fields.get("user")
    user = json.loads(user_raw) if isinstance(user_raw, str) else (user_raw or {})
    if not user or "id" not in user:
        raise HTTPException(status_code=400, detail="user not found in init_data")

    now = int(time.time())
    claims = {
        "sub": user["id"],
        # "sub": str(user["id"]),
        # "username": user.get("username"),
        # "tg_user": user,            # опционально
        "iat": now,
        "exp": now + JWT_TTL,
        # "scopes": ["webapp"],       # опционально
    }
    token = jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALG)
    user = (
        await db.execute(select(User).where(User.telegram_id == user["id"]))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(404, detail="User not found")

    # 2. Баланс
    balance = (
        await db.execute(
            select(func.coalesce(func.sum(WalletEntry.amount_rub), 0))
            .where(WalletEntry.user_id == user.id)
        )
    ).scalar_one()

    # 3. VPN-конфиги
    configs = (
        await db.execute(
            select(VpnConfig)
            .where(VpnConfig.user_id == user.id, VpnConfig.is_active.is_(True))
        )
    ).scalars().all()

    return UserFullInfo(
        id=user.id,
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        balance=UserBalanceBase(balance=float(balance)),
        keys=[
            KeyBase(
                id=cfg.id,
                key=build_vless_link(cfg),         # ✅ готовая vless-ссылка
                # server=cfg.vpn_domain,
                country=cfg.country,
                created_at=dt_to_str(cfg.created_at),
            )
            for cfg in configs
        ],
        access_token=TokenResponse(access_token=token)
    )
# query_id=AAGVbSskAAAAAJVtKyTyM9DK&user=%7B%22id%22%3A606825877%2C%22first_name%22%3A%22%D0%94%D0%BC%D0%B8%D1%82%D1%80%D0%B8%D0%B9%22%2C%22last_name%22%3A%22%D0%A1%D0%B2%D0%B0%D1%80%D0%BE%D0%B2%D1%81%D0%BA%D0%B8%D0%B9%22%2C%22username%22%3A%22swarovskidima%22%2C%22language_code%22%3A%22ru%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FrSGM8ZYqLcQ8KuQ4MlqAXlf2OQLeJztVZpj5KBtpgno.svg%22%7D&auth_date=1756537058&signature=UnRiUVXuv_uXPDsMjOUoRB7I7tY3BUntxKcBmBH0hPGNRUYkUvBFjeUHwfiLWjoVNhZk90k3vl67IE4SUmDTCA&hash=5d75dc03be1851b905df2e9e1b30854738aafdd0020fe4cf9373b4fa30e56e15


def dt_to_str(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


# зависимость, которая требует Bearer JWT
bearer = HTTPBearer(auto_error=True)


def require_jwt(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")
