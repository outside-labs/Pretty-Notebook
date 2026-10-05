import datetime
from pathlib import Path
from typing import Annotated

import fastapi
from fastapi import Depends, File, HTTPException, UploadFile, Request
from pydantic import BaseModel, Field
from web_config import IMAGES_PATH, PAGES_PATH

from .atomic_io import atomic_write_bytes
from .auth_api import get_current_user
from .catalog import SLUG_PATTERN
from .catalog import publication_body as publication_body
from .catalog import LEGACY_PAGE_PREFIX as LEGACY_PAGE_PREFIX, LEGACY_PAGE_SUFFIX as LEGACY_PAGE_SUFFIX

router = fastapi.APIRouter()

PUB_PATH = PAGES_PATH
MAX_PUBLICATION_CHARS = 2_000_000

IMG_PATH = IMAGES_PATH
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_SIGNATURES = {
    ".png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
    ".jpg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".gif": lambda content: content.startswith((b"GIF87a", b"GIF89a")),
    ".webp": lambda content: (
        len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    ),
}

class Publishment(BaseModel):
    name: str = Field(max_length=200)
    content: str = Field(max_length=MAX_PUBLICATION_CHARS)


def publication_path(name: str) -> Path:
    """build path to publishment, ensuring validity of slug-name"""
    if not SLUG_PATTERN.fullmatch(name):
        raise HTTPException(400, "Invalid publication name.")

    target = (PUB_PATH / f"{name}.html").resolve()

    if target.parent != PUB_PATH:
        raise HTTPException(400, "Invalid publication path.")

    return target


async def add_publishment(name: str, content: str, *, store) -> Publishment:
    """Store owner-authored HTML as data, never as executable Jinja source."""
    publication_path(name)
    await store.publish(name, content)

    pub = Publishment(
        name=name,
        content=content,
    )

    return pub


@router.post(
    "/api/publishment",
    name="add_pub",
    status_code=201,
    response_model=Publishment,
    dependencies=[Depends(get_current_user)],
)  # if ok status_code 200 -> 201, if not, it's handled in the ValidationError
async def publishment_post(pub_submittal: Publishment, request: Request):
    """Store a publication."""
    n = pub_submittal.name
    c = pub_submittal.content

    return await add_publishment(n, c, store=request.app.state.publications)


def image_path(filename: str | None) -> Path:
    """ensures valid filename and file type of images"""
    if not filename:
        raise HTTPException(400, "Missing filename.")

    supplied = Path(filename)

    if supplied.name != filename:
        raise HTTPException(400, "Invalid filename.")

    if supplied.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(400, "Unsupported image type.")

    target = (IMG_PATH / supplied.name).resolve()

    if target.parent != IMG_PATH:
        raise HTTPException(400, "Invalid image path.")

    return target


@router.post(
    "/api/image",
    name="add_img",
    status_code=201,
    dependencies=[Depends(get_current_user)],
)
async def image_post(file: Annotated[UploadFile, File(...)]):
    """Validate and atomically store a bounded image upload."""
    target = image_path(file.filename)
    content = await file.read(MAX_IMAGE_BYTES + 1)
    await file.close()

    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image exceeds the 10 MiB limit.")

    suffix = target.suffix.lower()
    if not IMAGE_SIGNATURES[suffix](content):
        raise HTTPException(400, "File content does not match its image type.")

    await atomic_write_bytes(target, content)

    return {"filename": file.filename}


@router.get("/api/publishments", dependencies=[Depends(get_current_user)])
async def publishments_get(request: Request) -> list:
    """Publishments Get"""
    return await request.app.state.publications.inventory()


@router.get("/api/images", dependencies=[Depends(get_current_user)])
async def images_get() -> list:
    """Images Get"""
    img_names = sorted(Path.iterdir(IMG_PATH), key=lambda path: path.name)
    img_data = []
    for i in img_names:
        if i.is_file() and i.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
            mod_date = datetime.datetime.fromtimestamp(
                i.stat().st_mtime,
                tz=datetime.UTC,
            )
            img_data.append({"img_name": i.name, "mod_date": mod_date})

    return img_data


@router.delete("/api/publishment/{pub_name}", dependencies=[Depends(get_current_user)])
async def publishment_delete(pub_name: str, request: Request):
    """Publishment Delete"""
    supplied = Path(pub_name)

    if supplied.name != pub_name or supplied.suffix.lower() != ".html":
        raise HTTPException(400, "Invalid publication filename.")

    target = publication_path(supplied.stem)

    if not await request.app.state.publications.delete(supplied.stem):
        raise HTTPException(404, "Publication not found.")

    return {"pub_name": target.name}
