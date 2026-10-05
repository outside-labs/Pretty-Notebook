"""Public pages, theme preference, and fixed routes."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from api.layout_api import get_layout_content
from api.publish_api import publication_path
from pnbp._routes import RESERVED
from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates

router = APIRouter()
WEB_ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(WEB_ROOT / "templates")


async def get_template_content(request: Request) -> dict:
    prefix = request.scope.get("root_path", "")
    content = await get_layout_content(prefix)
    cookie_value = request.cookies.get("darkmode")
    if cookie_value in {"True", "False"}:
        content["darkmode"] = cookie_value == "True"
    content["request"] = request
    content["assets"] = request.app.state.assets.layout_assets(content, request)
    content["root_path"] = prefix
    return content


@router.get("/contact", include_in_schema=False)
async def contact(request: Request):
    content = await get_template_content(request)
    content["form_sent"] = request.query_params.get("sent") == "1"
    return templates.TemplateResponse(request, "home/contact.html", content)


@router.get("/", include_in_schema=False)
async def home(request: Request):
    content = await get_template_content(request)
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
def favicon():
    raise HTTPException(status_code=404, detail="Favicon not found")


@router.get("/{content:path}", include_in_schema=False)
async def content(request: Request, content: str):
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
        return templates.TemplateResponse(
            request,
            "shared/404.html",
            template_content,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    template_content["page_content"] = page["body"]
    template_content["diagram_mode"] = "detect" if page["legacy"] else "required" if "mermaid" in page["feature_flags"] else None
    return templates.TemplateResponse(
        request,
        "shared/published.html",
        template_content,
    )
