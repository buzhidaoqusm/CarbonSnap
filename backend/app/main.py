"""The ASGI application: FastAPI in front, the Flask app behind it.

Routes move from Flask to FastAPI one module at a time (the strangler fig
pattern). FastAPI answers the paths it has routes for, including /docs and
/openapi.json; every other path falls through to the Flask app, which a2wsgi
runs on a thread pool. Run with:

    uvicorn --factory app.main:create_api
"""

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from flask import Flask

from app import create_app
from app.api import health
from app.api.errors import install_error_handlers
from app.api.forum import routes as forum
from app.api.ledger import routes as ledger
from app.api.market import routes as market
from app.api.notification import routes as notification
from app.api.profile import auth
from app.api.project import routes as project
from app.api.uploads import routes as uploads
from app.core.config import get_settings


def create_api(flask_app: Flask | None = None) -> FastAPI:
    api = FastAPI(title="CarbonSnap API", version="0.1.0")
    # Wraps the Flask fallback too; it answers preflights itself and its headers
    # replace the ones flask_cors adds, so each response carries one set.
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

    legacy = flask_app if flask_app is not None else create_app()
    # Flask is the router's default, not a mount at "/": a mount matches every
    # path, so a FastAPI path called with the wrong method went to Flask and
    # came back as its HTML 404. The router answers that case with a 405 before
    # it falls back to the default.
    # The WSGI/ASGI type stubs of Flask, a2wsgi and Starlette do not line up,
    # though the objects are compatible at runtime.
    wsgi = WSGIMiddleware(legacy, workers=get_settings().wsgi_threads)  # type: ignore[arg-type]
    api.router.default = wsgi  # type: ignore[assignment]
    return api
