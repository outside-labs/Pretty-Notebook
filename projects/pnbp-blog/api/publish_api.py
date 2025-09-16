import os

import fastapi
from pydantic import BaseModel
from fastapi import File, UploadFile

router = fastapi.APIRouter()

PUB_PATH = 'templates/blog/'
IMG_PATH = 'static/imgs/'

class Publishment(BaseModel):
	name: str
	content: str


async def add_publishment(name: str, content: str) -> Publishment:
	extends = "{% extends 'shared/layout.html' %}\n\n"
	start_block = '{% block content %}\n\n'
	end_block = '\n\n{% endblock %}'
	content = f'{extends}{start_block}{content}{end_block}'

	with open(os.path.join(PUB_PATH, f'{name}.html'), 'w') as pf:
		pf.write(content)

	pub = Publishment(
		name=name,
		content=content,
		)

	return pub


@router.post('/api/publishment', name='add_pub', status_code=201, response_model=Publishment) # if ok status_code 200 -> 201, if not, it's handled in the ValidationError
async def publishment_post(pub_submittal: Publishment):
	
	n = pub_submittal.name
	c = pub_submittal.content

	return await add_publishment(n, c)


@router.post('/api/image', name='add_img', status_code=201)
async def image_post(file: UploadFile = File(...)):
	# file.filename = f'{name}.jpg'
	contents = await file.read()

	with open(os.path.join(IMG_PATH, file.filename), 'wb') as f:
		f.write(contents)

	return {"filename": file.filename}


