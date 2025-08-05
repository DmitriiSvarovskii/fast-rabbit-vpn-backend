from src.api import xray
from src.api import user
from src.api import payment
from src.api import server
from src.api import key

routers = (
    xray.router,
    user.router,
    payment.router,
    server.router,
    key.router,
)
