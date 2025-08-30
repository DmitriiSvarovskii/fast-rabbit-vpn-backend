# app/miniapp/verify.py
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Dict, Tuple, Any
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from nacl.signing import VerifyKey  # pip install pynacl
from app.core.configs.bot import bot_settings
router = APIRouter(prefix="/miniapp", tags=["miniapp"])

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


def verify_hmac(init_data: str, bot_token: str, max_age_sec: int = 24 * 3600) -> Dict[str, Any]:
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


def verify_third_party(init_data: str, bot_id: str, env: str = "prod", max_age_sec: int = 24 * 3600) -> Dict[str, Any]:
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
    max_age_sec: int = 24 * 3600


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


# ---- FastAPI endpoint ----

@router.post("/verify", response_model=VerifyResponse)
def verify_init_data(
    payload: VerifyRequest,
    bot_token: str = Depends(get_bot_token),
    bot_id: str = Depends(get_bot_id),
    x_tg_init_data: str | None = Header(default=None, alias="X-Telegram-WebApp-InitData"),
):
    """
    Accepts:
    - JSON body with 'init_data' or
    - optional header X-Telegram-WebApp-InitData (takes precedence if provided).

    mode:
      - "hmac"        -> server-side verification (requires bot_token)
      - "third_party" -> Ed25519 verification (requires bot_id, uses Telegram public keys)
    """
    init_data = x_tg_init_data or payload.init_data
    if not init_data:
        raise HTTPException(status_code=400, detail="init_data is required (body or X-Telegram-WebApp-InitData)")

    if payload.mode == "hmac":
        fields = verify_hmac(init_data, bot_token=bot_token, max_age_sec=payload.max_age_sec)
    elif payload.mode == "third_party":
        env = "prod" if payload.env.lower() in ("prod", "production") else "test"
        fields = verify_third_party(init_data, bot_id=bot_id, env=env, max_age_sec=payload.max_age_sec)
    else:
        raise HTTPException(status_code=400, detail="Unsupported mode. Use 'hmac' or 'third_party'.")

    return VerifyResponse(ok=True, fields=fields)
