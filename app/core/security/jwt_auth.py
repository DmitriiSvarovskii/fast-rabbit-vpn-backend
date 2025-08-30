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
from app.miniapp.verify import verify_hmac, get_bot_token

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
JWT_ALG = "HS256"
JWT_TTL = 10 * 60  # 10 минут

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_TTL


@auth_router.post("/telegram", response_model=TokenResponse)
def exchange_initdata_for_jwt(
    x_tg_init_data: str = Header(alias="X-Telegram-WebApp-InitData"),
    bot_token: str = Depends(get_bot_token),
):
    fields = verify_hmac(x_tg_init_data, bot_token=bot_token, max_age_sec=10 * 60)

    user_raw = fields.get("user")
    user = json.loads(user_raw) if isinstance(user_raw, str) else (user_raw or {})
    if not user or "id" not in user:
        raise HTTPException(status_code=400, detail="user not found in init_data")

    now = int(time.time())
    claims = {
        "sub": str(user["id"]),
        "username": user.get("username"),
        "tg_user": user,            # опционально
        "iat": now,
        "exp": now + JWT_TTL,
        "scopes": ["webapp"],       # опционально
    }
    token = jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALG)
    return TokenResponse(access_token=token)


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
