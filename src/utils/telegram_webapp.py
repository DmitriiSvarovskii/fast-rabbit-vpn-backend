import hmac
import hashlib
import urllib.parse
from typing import Dict


def parse_webapp_init_data(raw: str) -> Dict:
    """
    Разбирает initData из WebApp (query string). Возвращает dict ключей.
    """
    if not raw:
        return {}
    # initData может приходить как строка query-параметров
    pairs = urllib.parse.parse_qsl(raw, keep_blank_values=True)
    return {k: v for k, v in pairs}


def validate_webapp_init_data(raw: str, bot_token: str) -> Dict:
    """
    Проверка подписи WebApp initData по алгоритму Telegram.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    data = parse_webapp_init_data(raw)
    if not data:
        raise ValueError("empty init data")

    recv_hash = data.pop('hash', None)
    if not recv_hash:
        raise ValueError("hash missing")

    # формируем строку data_check_string
    check_kv = []
    for k in sorted(data.keys()):
        check_kv.append(f"{k}={data[k]}")
    data_check_string = "\n".join(check_kv).encode()

    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string,
                         hashlib.sha256).hexdigest()

    if calc_hash != recv_hash:
        raise ValueError("invalid hash")

    # полезное: user лежит в поле 'user' в JSON-строке
    user_json = data.get('user')
    import json
    user = json.loads(user_json) if user_json else {}
    data['user_obj'] = user
    return data
