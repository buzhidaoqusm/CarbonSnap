"""The ASGI application. Run with:

    uvicorn --factory app.main:create_api

Every route is FastAPI's: the Flask app the routes moved off (the strangler
fig pattern) no longer sits behind it, so an unknown path is a 404 envelope
from the error handlers.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.ai import conversations as ai_conversations
from app.api.ai import memory as ai_memory
from app.api.ai import streams as ai_streams
from app.api.errors import install_error_handlers
from app.api.forum import routes as forum
from app.api.ledger import routes as ledger
from app.api.market import routes as market
from app.api.notification import routes as notification
from app.api.profile import auth
from app.api.project import routes as project
from app.api.uploads import routes as uploads


def _log_app_info() -> None:
    # uvicorn configures only its own loggers, and the root logger's default
    # (WARNING) would drop the app's INFO lines, the LLM usage records among
    # them. Records still propagate, so pytest's caplog sees them too.
    logger = logging.getLogger("app")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


def create_api() -> FastAPI:
    _log_app_info()
    api = FastAPI(title="CarbonSnap API", version="0.1.0")
    api.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    install_error_handlers(api)
    api.include_router(health.router)
    api.include_router(notification.router)
    api.include_router(auth.router)
    api.include_router(ledger.router)
    api.include_router(market.router)
    api.include_router(forum.router)
    api.include_router(project.router)
    api.include_router(uploads.router)
    api.include_router(ai_memory.router)
    api.include_router(ai_conversations.router)
    api.include_router(ai_streams.router)

    return api
