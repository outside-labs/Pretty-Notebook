"""Escaped public notebook and directory indexes under a fixed route."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from api.public_navigation import snapshot_navigation, validate_directory
from . import home

router = APIRouter()


@router.get("/n", include_in_schema=False)
async def notebook_index(request: Request, directory: Annotated[str, Query(max_length=499)] = "",
                         limit: Annotated[int, Query(ge=1, le=100)] = 50,
                         offset: Annotated[int, Query(ge=0, le=10_000)] = 0):
    try:
        validate_directory(directory)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    navigation = await snapshot_navigation(request)
    report = navigation.directory(directory, limit=limit, offset=offset)
    content = await home.get_template_content(request, page_title=directory.rsplit("/", 1)[-1] if directory else "Notebook")
    content["notebook_index"] = report
    return home.templates.TemplateResponse(request, "home/notebook.html", content)
