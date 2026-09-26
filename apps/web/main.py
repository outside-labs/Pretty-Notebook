import asyncio
from pathlib import Path

import fastapi
from api import auth_api, layout_api, publish_api
from starlette.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise
from views import home

WEB_ROOT = Path(__file__).resolve().parent
DEFAULT_DATABASE_URL = "sqlite://db.sqlite3"


def create_app(*, db_url: str = DEFAULT_DATABASE_URL) -> fastapi.FastAPI:
    """Create the web application with an explicit persistence boundary."""
    app = fastapi.FastAPI()
    app.state.bootstrap_lock = asyncio.Lock()
    app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")
    app.include_router(publish_api.router)
    app.include_router(auth_api.router)
    app.include_router(layout_api.router)
    # The public single-slug catch-all must remain after every API route.
    app.include_router(home.router)

    register_tortoise(
        app,
        db_url=db_url,
        modules={"models": ["api.auth_api"]},
        generate_schemas=True,
        add_exception_handlers=True,
    )
    return app


api = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api, port=8000, host="127.0.0.1")
