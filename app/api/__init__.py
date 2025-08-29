from app.api import xray
from app.api import user
from app.api import payment
from app.api import server
from app.api import key
from app.api import payments_stars
from app.api import tg_webhook

routers = (
    xray.router,
    user.router,
    payment.router,
    server.router,
    key.router,
    payments_stars.router,
    tg_webhook.router,
)
