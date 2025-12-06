import json
import random

import fastapi
from fastapi import Form, status
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyCookie

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from jinja2.exceptions import TemplateNotFound

from api.layout_api import update_layout, render_nav, _open_layout, _get_layout_content


router = fastapi.APIRouter()
templates = Jinja2Templates('templates')



async def _cookie_handler(content: dict, cookies: dict):
	""" """
	for k,v in cookies.items():
		if k in content.keys():
			if k == 'darkmode':
				if v == 'False':
					v = False
				elif v == 'True':
					v = True

			content.update({k:v})

	return content


@router.get('/', include_in_schema=False)
async def home(request: Request):
	""" """
	# print('cookies', request.cookies)
	cont = await _get_layout_content()
	cont = await _cookie_handler(cont, request.cookies)
	
	cont.update({'request': request})
	cont.update({'quote': _get_random_quote()})

	return templates.TemplateResponse('home/home.html', cont)



@router.post('/', include_in_schema=False)
async def home(request: Request, darkmode=Form(...)):
	""" """	
	response = RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)

	if darkmode == 'darkmode':
		response.set_cookie('darkmode', True)

	if darkmode == 'lightmode':
		response.set_cookie('darkmode', False)

	return response



@router.get('/{content}', include_in_schema=False)
async def content(request: Request, content: str):
	""" main catching route to /single-slug
		:returns: from templates/blog function
			or -> templates/home/404.html
	"""
	cont = await _get_layout_content()

	for k,v in request.cookies.items():
		if k in cont.keys():
			if k == 'darkmode':
				if v == 'False':
					v = False
				elif v == 'True':
					v = True

			cont.update({k:v})

	cont.update({'request': request})

	try:
		return templates.TemplateResponse(f'blog/{content}.html', cont)
	except TemplateNotFound:
		cont.update({'unavailable_content': content})
		return templates.TemplateResponse(f'shared/404.html', cont)

@router.post('/{content}', include_in_schema=False)
async def cookie_post(request: Request, content: str, darkmode=Form(...)):
	""" """

	print('cookies', request.cookies)
	print(darkmode)
	print('**',content)
	response = RedirectResponse(url=request.url.path, status_code=status.HTTP_303_SEE_OTHER)
	response.set_cookie('hello', 'world')	

	if darkmode == 'darkmode':
		response.set_cookie('darkmode', True)

	if darkmode == 'lightmode':
		response.set_cookie('darkmode', False)

	return response



@router.get('/home', include_in_schema=False)
async def home_new(request: Request):
	""" """
	print('cookies', request.cookies)

	cont = await _get_layout_content()

	for k,v in request.cookies.items():
		if k in cont.keys():
			if k == 'darkmode':
				if v == 'False':
					v = False
				elif v == 'True':
					v = True

			cont.update({k:v})
			
	cont.update({'request': request})
	cont.update({'quote': _get_random_quote()})
	
	print(cont)

	return templates.TemplateResponse('home/home-new.html', cont)


@router.post('/home', include_in_schema=False)
async def home_new_post(request: Request, darkmode=Form(...)):
	# quote = _get_random_quote()
	print('cookies', request.cookies)
	print(darkmode)

	_cont = await _open_layout() # don't convert pages to html here or break 
	response = RedirectResponse(url=router.url_path_for('home_new'), status_code=status.HTTP_303_SEE_OTHER)
	response.set_cookie('hello', 'world')	

	if darkmode == 'darkmode':
		response.set_cookie('darkmode', True)
		# _cont['darkmode'] = True
		# await update_layout(**_cont)

	if darkmode == 'lightmode':
		response.set_cookie('darkmode', False)
		# _cont['darkmode'] = False
		# await update_layout(**_cont)

	print(response)

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
	print('cookies', request.cookies)
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









