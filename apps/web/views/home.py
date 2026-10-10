"""Public pages, theme preference, and fixed routes."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from api.layout_api import get_layout_content
from api.publish_api import publication_path
from api.public_navigation import snapshot_navigation
from pretty_notebook._internal.routes import RESERVED
from pretty_notebook._internal.icons import render_icon, replace_legacy_icons
from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from api.site_api import favicon_url, read_favicon

router = APIRouter()
WEB_ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(WEB_ROOT / "templates")


async def get_template_content(request: Request, *, page_title: str | None = None) -> dict:
    prefix = request.scope.get("root_path", "")
    content = await get_layout_content(prefix)
    cookie_value = request.cookies.get("darkmode")
    if cookie_value in {"True", "False"}:
        content["darkmode"] = cookie_value == "True"
    content["request"] = request
    content["icon"] = render_icon
    content["highlight_code"] = request.app.state.code_highlight
    for field in ("NAV_BRAND", "FOOTER"):
        content[field] = replace_legacy_icons(content[field])
    content["assets"] = request.app.state.assets.layout_assets(content, request)
    content["root_path"] = prefix
    content["page_title"] = page_title
    favicon = await read_favicon(request)
    content["favicon_url"] = favicon_url(request, favicon) if favicon is not None else None
    return content


@router.get("/contact", include_in_schema=False)
async def contact(request: Request):
    content = await get_template_content(request, page_title="Contact")
    content["form_sent"] = request.query_params.get("sent") == "1"
    return templates.TemplateResponse(request, "home/contact.html", content)


@router.get("/", include_in_schema=False)
async def home(request: Request):
    content = await get_template_content(request)
    navigation = await snapshot_navigation(request)
    content["notebook_index"] = navigation.directory()
    return templates.TemplateResponse(request, "home/home.html", content)


@router.post("/theme", include_in_schema=False)
async def set_theme(
    request: Request,
    darkmode: Literal["darkmode", "lightmode"] = Form(...),
    return_to: str = Form("/"),
):
    parsed = urlsplit(return_to)
    invalid = (
        not parsed.path.startswith("/")
        or parsed.path.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or "\\" in return_to
        or any(ord(character) < 32 for character in return_to)
    )
    if invalid:
        raise HTTPException(status_code=400, detail="Invalid return path")
    prefix = request.scope.get("root_path", "")
    if prefix:
        if return_to == "/":
            return_to = prefix + "/"
        elif not parsed.path.startswith(prefix + "/"):
            raise HTTPException(400, "Invalid return path")
    response = RedirectResponse(url=return_to, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        "darkmode",
        darkmode == "darkmode",
        httponly=True,
        max_age=31_536_000,
        samesite="lax",
        path=prefix + "/",
    )
    return response


@router.get("/favicon.ico", include_in_schema=False)
async def favicon(request: Request):
    content = await read_favicon(request)
    if content is None:
        raise HTTPException(status_code=404, detail="Favicon not found")
    return RedirectResponse(favicon_url(request, content), status_code=307,
                            headers={"Cache-Control": "no-store"})


@router.get("/{content:path}", include_in_schema=False)
async def content(request: Request, content: str, related: bool = True):
    if content.split("/", 1)[0] in RESERVED - {"n"}:
        raise HTTPException(404, "Not Found")
    template_content = await get_template_content(request)
    try:
        if b"%" in request.scope.get("raw_path", b"").split(b"?", 1)[0]:
            raise HTTPException(404, "Invalid encoded path")
        publication_path(content)
        resolved = await request.app.state.publications.resolve(content)
        if resolved and resolved["canonical_route"] != "/" + content:
            return RedirectResponse(template_content["root_path"] + resolved["canonical_route"], status_code=308)
        page = await request.app.state.publications.read_page(content)
        if page is None:
            raise FileNotFoundError
    except (HTTPException, FileNotFoundError, IsADirectoryError):
        template_content["unavailable_content"] = content
        template_content["page_title"] = "Page not found"
        return templates.TemplateResponse(
            request,
            "shared/404.html",
            template_content,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    template_content["page_title"] = resolved["title"] if resolved else content
    template_content["page_content"] = replace_legacy_icons(page["body"])
    navigation = await snapshot_navigation(request)
    template_content["navigation"] = navigation.page("/" + content, related=related)
    template_content["diagram_mode"] = "detect" if page["legacy"] else "required" if "mermaid" in page["feature_flags"] else None
    template_content["code_mode"] = "detect" if page["legacy"] else "required" if "code" in page["feature_flags"] else None
    return templates.TemplateResponse(
        request,
        "shared/published.html",
        template_content,
    )
