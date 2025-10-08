import json
import random

import fastapi
from fastapi import Form

from starlette.requests import Request
from starlette.templating import Jinja2Templates


QUOTES = open('static/quotes.json', 'r')
QUOTES = json.load(QUOTES)

templates = Jinja2Templates('templates')
router = fastapi.APIRouter()


@router.get('/', include_in_schema=False)
async def index(request: Request):
	quote = random.choice(QUOTES)
	return templates.TemplateResponse('home/index.html', {'request': request, 'quote': quote})


@router.get('/about', include_in_schema=False)
async def about(request: Request):
	return templates.TemplateResponse('home/about.html', {'request': request})


@router.get('/contact', include_in_schema=False)
async def contact(request: Request):
	return templates.TemplateResponse('home/contact.html', {'request': request})


@router.get('/{content}', include_in_schema=False)
async def content(request: Request, content: str):
	return templates.TemplateResponse(f'blog/{content}.html', {'request': request})


@router.get('/favicon.ico', include_in_schema=False)
def favicon():
	return fastapi.responses.RedirectResponse(url='static/img/favicon.ico')


@router.post('/contact', include_in_schema=False)
async def contact_post(email_address=Form(...), email_message=Form(...)):
	print(email_address, email_message) #by <input name="x">
	return {"email_address": email_address, "email_message": email_message}


