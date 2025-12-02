import json
import random

import fastapi
from fastapi import Form, status
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyCookie

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from jinja2.exceptions import TemplateNotFound

from api.layout_api import update_layout


router = fastapi.APIRouter()
templates = Jinja2Templates('templates')




async def _open_layout():
	"""
	"""
	with open('blog-settings.json') as f:
		_cont = json.load(f)

	return _cont

async def _get_layout_content():
	""" """
	with open('blog-settings.json') as f:
		_cont = json.load(f)
		_cont['nav_pages'] = await render_nav(_cont['nav_pages'])
	return _cont


@router.get('/home', include_in_schema=False)
async def home_new(request: Request):
	""" """
	print('cookies', request.cookies)

	cont = await _get_layout_content()
	cont.update({'request': request})
	cont.update({'quote': _get_random_quote()})

	return templates.TemplateResponse('home/home-new.html', cont)


@router.post('/home', include_in_schema=False)
async def home_new_post(request: Request, darkmode=Form(...)):
	# quote = _get_random_quote()
	print('cookies', request.cookies)
	print(darkmode)

	_cont = await _open_layout() # don't convert pages to html here or break 

	if darkmode == 'darkmode':
		_cont['darkmode'] = True
		await update_layout(**_cont)

	if darkmode == 'lightmode':
		_cont['darkmode'] = False
		await update_layout(**_cont)

	response = RedirectResponse(url=router.url_path_for('home_new'), status_code=status.HTTP_303_SEE_OTHER)
	print(response)
	response.set_cookie('hello', 'world')

	return response


def _get_random_quote():
	""" """
	QUOTES = open('static/quotes.json', 'r')
	QUOTES = json.load(QUOTES)
	return random.choice(QUOTES)


@router.get('/favicon.ico', include_in_schema=False)
def favicon():
	return fastapi.responses.RedirectResponse(url='static/img/favicon.ico')


@router.get('/', include_in_schema=False)
async def home(request: Request):
	quote = _get_random_quote()
	return templates.TemplateResponse('home/home.html', {'request': request, 'quote': quote})


@router.get('/about', include_in_schema=False)
async def about(request: Request):
	return templates.TemplateResponse('home/about.html', {'request': request})


@router.get('/contact', include_in_schema=False)
async def contact(request: Request):
	return templates.TemplateResponse('home/contact.html', {'request': request})


@router.post('/contact', include_in_schema=False)
async def contact_post(email_address=Form(...), email_message=Form(...)):
	""" todo 
	"""
	print(email_address, email_message) #by <input name="x">
	return {"email_address": email_address, "email_message": email_message}


@router.get('/{content}', include_in_schema=False)
async def content(request: Request, content: str):
	""" main catching route to /single-slug
		:returns: from templates/blog function
			or -> templates/home/404.html
	"""
	try:
		return templates.TemplateResponse(f'blog/{content}.html', {'request': request})
	except TemplateNotFound:
		return templates.TemplateResponse(f'shared/404.html', {'request': request, 'unavailable_content': content})









