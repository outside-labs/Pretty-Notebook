import asyncio
from os import chmod

import fastapi
import web_config
from api import auth_api, layout_api, publish_api
from api import forms as forms_api
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles
from tortoise import connections
from tortoise.contrib.fastapi import register_tortoise
from views import forms, home

DEFAULT_DATABASE_URL = web_config.DATABASE_URL


def prepare_storage() -> None:
    """Create the private persistent-data layout without overwriting state."""
    for directory in {
        publish_api.PUB_PATH,
        publish_api.IMG_PATH,
        layout_api.WEB_SETTINGS_PATH.parent,
    }:
        if not directory.exists():
            directory.mkdir(parents=True, mode=0o700)

    if not layout_api.WEB_SETTINGS_PATH.exists():
        defaults = web_config.DEFAULT_SETTINGS_PATH.read_text(encoding="utf-8")
        try:
            with layout_api.WEB_SETTINGS_PATH.open("x", encoding="utf-8") as output:
                output.write(defaults)
        except FileExistsError:
            pass
        else:
            chmod(layout_api.WEB_SETTINGS_PATH, 0o600)


def create_app(
    *,
    db_url: str = DEFAULT_DATABASE_URL,
    allowed_hosts: list[str] | None = None,
) -> fastapi.FastAPI:
    """Create the web application for one process and one persistent data root."""
    prepare_storage()
    app = fastapi.FastAPI()
    app.state.bootstrap_lock = asyncio.Lock()
    app.state.pages_path = publish_api.PUB_PATH
    app.state.images_path = publish_api.IMG_PATH
    app.state.settings_path = layout_api.WEB_SETTINGS_PATH

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts or web_config.allowed_hosts(),
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=()",
        )
        if request.url.path.startswith("/api") or request.url.path == "/healthz":
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.mount(
        "/static/imgs",
        StaticFiles(directory=publish_api.IMG_PATH),
        name="published-images",
    )
    app.mount(
        "/static",
        StaticFiles(directory=web_config.WEB_ROOT / "static"),
        name="static",
    )

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        try:
            await connections.get("default").execute_query("SELECT 1")
            await layout_api.get_layout_content()
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=503,
                detail="Persistent storage is unavailable.",
            ) from exc
        return {"status": "ok"}

    app.include_router(publish_api.router)
    app.include_router(auth_api.router)
    app.include_router(layout_api.router)
    app.include_router(forms_api.router)
    app.include_router(forms.router)
    # The public single-slug catch-all must remain after every fixed and API route.
    app.include_router(home.router)

    register_tortoise(
        app,
        db_url=db_url,
        modules={"models": ["api.auth_api", "api.forms"]},
        generate_schemas=True,
        add_exception_handlers=True,
    )
    return app


api = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api, port=8000, host="127.0.0.1")
