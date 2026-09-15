import re
import datetime
from pathlib import Path

import aiofiles

import fastapi
from fastapi import File, UploadFile, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel

from .auth_api import get_current_user


router = fastapi.APIRouter()

PUB_PATH = (Path(__file__).resolve().parents[1] / 'templates' / 'pages').resolve()
SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")

IMG_PATH = (Path(__file__).resolve().parents[1] / 'static' / 'imgs').resolve()
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}



class Publishment(BaseModel):
	name: str
	content: str



def publication_path(name: str) -> Path:
	""" build path to publishment, ensuring validity of slug-name
	"""
	if not SLUG_PATTERN.fullmatch(name):
		raise HTTPException(400, "Invalid publication name.")

	target = (PUB_PATH / f"{name}.html").resolve()

	if target.parent != PUB_PATH:
		raise HTTPException(400, "Invalid publication path.")

	return target


async def add_publishment(name: str, content: str) -> Publishment:
	""" """
	extends = "{% extends 'shared/layout.html' %}\n\n"
	start_block = '{% block content %}\n\n'
	end_block = '\n\n{% endblock %}'
	content = f'{extends}{start_block}{content}{end_block}'

	target = publication_path(name)
	
	async with aiofiles.open(target, 'w', encoding='utf-8') as pf:
		await pf.write(content)

	pub = Publishment(
		name=name,
		content=content,
		)

	return pub


@router.post('/api/publishment', name='add_pub', status_code=201, response_model=Publishment, dependencies=[Depends(get_current_user)]) # if ok status_code 200 -> 201, if not, it's handled in the ValidationError
async def publishment_post(pub_submittal: Publishment):
	""" Add Pub 
	"""
	n = pub_submittal.name
	c = pub_submittal.content

	return await add_publishment(n, c)


def image_path(filename: str | None) -> Path:
	""" ensures valid filename and file type of images
	"""
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


@router.post('/api/image', name='add_img', status_code=201, dependencies=[Depends(get_current_user)])
async def image_post(file: UploadFile = File(...)):
	""" Add Img 
	"""
	target = image_path(file.filename)
	
	async with aiofiles.open(target, 'wb') as f:
		while chunk := await file.read(1024 * 1024):
			await f.write(chunk)

	return {"filename": file.filename}



@router.get('/api/publishments', dependencies=[Depends(get_current_user)])
async def publishments_get() -> list:
	""" Publishments Get 
	"""
	pub_names = Path.iterdir(PUB_PATH)
	pub_data = []
	for p in pub_names:
		if p.is_file() and p.suffix.lower() == '.html':
			mod_date = datetime.datetime.fromtimestamp(Path(PUB_PATH / p).stat().st_mtime)
			pub_data.append({'pub_name': p.name, 'mod_date': mod_date})

	return pub_data


@router.get('/api/images', dependencies=[Depends(get_current_user)])
async def images_get() -> list:
	""" Images Get 
	"""
	img_names = Path.iterdir(IMG_PATH)
	img_data = []
	for i in img_names:
		if i.is_file() and i.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
			mod_date = datetime.datetime.fromtimestamp(Path(IMG_PATH / i).stat().st_mtime)
			img_data.append({'img_name': i.name, 'mod_date': mod_date})

	return img_data


@router.delete('/api/publishment/{pub_name}', dependencies=[Depends(get_current_user)])
async def publishment_delete(pub_name: str):
	""" Publishment Delete 
	"""
	supplied = Path(pub_name)

	if (supplied.name != pub_name or supplied.suffix.lower() != ".html"):
		raise HTTPException(400, "Invalid publication filename.")

	target = publication_path(supplied.stem)

	if not target.is_file():
		raise HTTPException(404, "Publication not found.")

	target.unlink()

	return {"pub_name": target.name}









