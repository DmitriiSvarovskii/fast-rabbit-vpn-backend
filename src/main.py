import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import routers
from src.configs import app_settings


app = FastAPI(
    title="Fast-Rabbit-VPN-Backend",
    version="0.0.1a",
    debug=app_settings.DEBUG,
)


app.add_middleware(
    CORSMiddleware,
    allow_credentials=app_settings.ALLOW_CREDENTIALS,
    allow_origins=app_settings.ALLOW_ORIGINS,
    allow_methods=app_settings.ALLOW_METHODS,
    allow_headers=app_settings.ALLOW_HEADERS,
)


for router in routers:
    app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=app_settings.SERVICE_HOST,
        port=app_settings.SERVICE_PORT,
        reload=app_settings.DEBUG,
    )
