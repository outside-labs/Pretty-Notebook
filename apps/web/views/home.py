"""Public pages, theme preference, and fixed routes."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jinja2.exceptions import TemplateNotFound
from starlette.templating import Jinja2Templates

from api.layout_api import get_layout_content

router = APIRouter()
WEB_ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(WEB_ROOT / "templates")


async def get_template_content(request: Request) -> dict:
    content = await get_layout_content()
    cookie_value = request.cookies.get("darkmode")
    if cookie_value in {"True", "False"}:
        content["darkmode"] = cookie_value == "True"
    content["request"] = request
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
    darkmode: Literal["darkmode", "lightmode"] = Form(...),
    return_to: str = Form("/"),
):
    if not return_to.startswith("/") or return_to.startswith("//") or "\\" in return_to:
        raise HTTPException(status_code=400, detail="Invalid return path")
    response = RedirectResponse(url=return_to, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("darkmode", darkmode == "darkmode", samesite="lax")
    return response


@router.get("/favicon.ico", include_in_schema=False)
def favicon():
    raise HTTPException(status_code=404, detail="Favicon not found")


@router.get("/{content}", include_in_schema=False)
async def content(request: Request, content: str):
    template_content = await get_template_content(request)
    try:
        return templates.TemplateResponse(
            request, f"pages/{content}.html", template_content
        )
    except TemplateNotFound:
        template_content["unavailable_content"] = content
        return templates.TemplateResponse(
            request,
            "shared/404.html",
            template_content,
            status_code=status.HTTP_404_NOT_FOUND,
        )
