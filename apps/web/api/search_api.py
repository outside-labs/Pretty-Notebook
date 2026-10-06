"""Literal anonymous search over current public publication revisions."""

import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from .public_index import IndexCapacityError, search_documents, validate_search

router = APIRouter()
SearchField = Literal["any", "title", "content", "tag"]


async def results(request, q, field, tags, limit, offset):
    if "regex" in request.query_params:
        raise HTTPException(422, "Regular expressions are only supported by local notebook search.")
    try:
        validate_search(q, field, tags, limit, offset)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    try:
        documents = await request.app.state.public_index.snapshot()
    except IndexCapacityError as error:
        raise HTTPException(503, str(error)) from error
    return await asyncio.to_thread(search_documents, documents, q, field=field,
                                   tags=tags, limit=limit, offset=offset)


@router.get("/api/search")
async def search(request: Request, q: Annotated[str, Query(min_length=1, max_length=512)],
                 field: SearchField = "any",
                 tag: Annotated[list[str], Query()] = [],
                 limit: Annotated[int, Query(ge=1, le=100)] = 20,
                 offset: Annotated[int, Query(ge=0, le=10_000)] = 0):
    return await results(request, q, field, tag, limit, offset)
