from src.api import xray
from src.api import user
from src.api import payment
from src.api import server
from src.api import key
from src.api import payments_stars
from src.api import tg_webhook

routers = (
    xray.router,
    user.router,
    payment.router,
    server.router,
    key.router,
    payments_stars.router,
    tg_webhook.router,
)
