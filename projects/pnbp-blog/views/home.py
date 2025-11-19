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

NAV_BRAND = """
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-globe2" viewBox="0 0 16 16">
  <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8zm7.5-6.923c-.67.204-1.335.82-1.887 1.855-.143.268-.276.56-.395.872.705.157 1.472.257 2.282.287V1.077zM4.249 3.539c.142-.384.304-.744.481-1.078a6.7 6.7 0 0 1 .597-.933A7.01 7.01 0 0 0 3.051 3.05c.362.184.763.349 1.198.49zM3.509 7.5c.036-1.07.188-2.087.436-3.008a9.124 9.124 0 0 1-1.565-.667A6.964 6.964 0 0 0 1.018 7.5h2.49zm1.4-2.741a12.344 12.344 0 0 0-.4 2.741H7.5V5.091c-.91-.03-1.783-.145-2.591-.332zM8.5 5.09V7.5h2.99a12.342 12.342 0 0 0-.399-2.741c-.808.187-1.681.301-2.591.332zM4.51 8.5c.035.987.176 1.914.399 2.741A13.612 13.612 0 0 1 7.5 10.91V8.5H4.51zm3.99 0v2.409c.91.03 1.783.145 2.591.332.223-.827.364-1.754.4-2.741H8.5zm-3.282 3.696c.12.312.252.604.395.872.552 1.035 1.218 1.65 1.887 1.855V11.91c-.81.03-1.577.13-2.282.287zm.11 2.276a6.696 6.696 0 0 1-.598-.933 8.853 8.853 0 0 1-.481-1.079 8.38 8.38 0 0 0-1.198.49 7.01 7.01 0 0 0 2.276 1.522zm-1.383-2.964A13.36 13.36 0 0 1 3.508 8.5h-2.49a6.963 6.963 0 0 0 1.362 3.675c.47-.258.995-.482 1.565-.667zm6.728 2.964a7.009 7.009 0 0 0 2.275-1.521 8.376 8.376 0 0 0-1.197-.49 8.853 8.853 0 0 1-.481 1.078 6.688 6.688 0 0 1-.597.933zM8.5 11.909v3.014c.67-.204 1.335-.82 1.887-1.855.143-.268.276-.56.395-.872A12.63 12.63 0 0 0 8.5 11.91zm3.555-.401c.57.185 1.095.409 1.565.667A6.963 6.963 0 0 0 14.982 8.5h-2.49a13.36 13.36 0 0 1-.437 3.008zM14.982 7.5a6.963 6.963 0 0 0-1.362-3.675c-.47.258-.995.482-1.565.667.248.92.4 1.938.437 3.008h2.49zM11.27 2.461c.177.334.339.694.482 1.078a8.368 8.368 0 0 0 1.196-.49 7.01 7.01 0 0 0-2.275-1.52c.218.283.418.597.597.932zm-.488 1.343a7.765 7.765 0 0 0-.395-.872C9.835 1.897 9.17 1.282 8.5 1.077V4.09c.81-.03 1.577-.13 2.282-.287z"/>
</svg>
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-book-fill" viewBox="0 0 16 16">
  <path d="M8 1.783C7.015.936 5.587.81 4.287.94c-1.514.153-3.042.672-3.994 1.105A.5.5 0 0 0 0 2.5v11a.5.5 0 0 0 .707.455c.882-.4 2.303-.881 3.68-1.02 1.409-.142 2.59.087 3.223.877a.5.5 0 0 0 .78 0c.633-.79 1.814-1.019 3.222-.877 1.378.139 2.8.62 3.681 1.02A.5.5 0 0 0 16 13.5v-11a.5.5 0 0 0-.293-.455c-.952-.433-2.48-.952-3.994-1.105C10.413.809 8.985.936 8 1.783z"/>
</svg>"""

# NAV_BRAND = 'dynamic!'
NAV_PAGES = {
	"content": "/index/",
	"about": "/obsidian-parser/",
	"contact": [
		{"github": "https://github.com/cbrun3"},
		{"subname2": "/subroute2/"}
		]
}

async def render_nav(pages: dict):
	_nav_pages = ""
	
	for k,v in pages.items():
		s = ""
		if isinstance(v, str):
			if not _nav_pages:
				s = f"""<li class="nav-item">
			<a class="nav-link active" aria-current="page" href="{v}">{k}</a>
		</li>"""
			else:
				s = f"""<li class="nav-item">
          <a class="nav-link" href="{v}">{k}</a>
        </li>"""

		if isinstance(v, list):
			s = '<li class="nav-item dropdown">'
			s += f"""<a class="nav-link dropdown-toggle" href="#" id="navbarDropdownMenuLink" role="button" data-bs-toggle="dropdown" aria-expanded="false">
            {k}
          </a>"""
			s += '<ul class="dropdown-menu" aria-labelledby="navbarDropdownMenuLink">'
			for p in v:
				if isinstance(p, dict):
					for k,v in p.items():
						x = f'<li><a class="dropdown-item" href="{v}">{k}</a></li>'
						s += x
			s += '</ul></li>'

		if s:
			_nav_pages += s

	return _nav_pages

def footer():
	s = """<p><small>mail to:</small><button type="button" class="btn btn-link"><small>self&commat;linked.page</small></button>
            &nbsp;| <small>powered by <a href="https://www.python.org/">Python</a>&nbsp;,&nbsp;<a href="https://fastapi.tiangolo.com/">FastAPI</a>&nbsp;,&nbsp;<a href="https://getbootstrap.com/">Bootstrap</a>&nbsp;,&nbsp;and&nbsp;</a><a href="https://obsidian.md/">Obsidian</a>&nbsp;via&nbsp;<a href="https://daringfireball.net/projects/markdown/">markdown</a>.</small></p>
	"""
	return s

def get_hljs_style():
	s = 'xt256'
	# s = 'default'
	return s


async def _get_layout_content():

	_cont = {
		'NAV_BRAND': NAV_BRAND,
		'nav_pages' : render_nav(),
		'hljs_style' : get_hljs_style(),
		'darkmode' : True,
		'footer': footer()
	}

	return _cont

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

# cookie_sec = APIKeyCookie(name="session")
# secret_key = "someactualsecret"

@router.get('/home', include_in_schema=False)
async def home_new(request: Request):
	
	# request.cookies['hello'] = 'world'
	print('cookies', request.cookies)
	# quote = _get_random_quote()
	cont = await _get_layout_content()
	cont.update({'request': request})
	cont.update({'quote': _get_random_quote()})
	return templates.TemplateResponse('home/home-new.html', cont)

	# return templates.TemplateResponse('home/home-new.html', {'request': request, 'quote':quote,'NAV_BRAND': NAV_BRAND, 'nav_pages': nav_pages, 'hljs_style': hljs_style, 'darkmode': darkmode})

@router.post('/home', include_in_schema=False)
async def home_new_post(request: Request, darkmode=Form(...)):
	# quote = _get_random_quote()
	print('cookies', request.cookies)
	print(darkmode)
	_cont = await _open_layout() # don't convert pages to html here or break 
	# sp = open('blog-settings.json')
	if darkmode == 'darkmode':
		_cont['darkmode'] = True
		await update_layout(**_cont)
		# with open('blog-settings.json', 'w') as sf:
			# json.dump(_cont, sf, indent=4)
	if darkmode == 'lightmode':
		_cont['darkmode'] = False
		with open('blog-settings.json', 'w') as sf:
			json.dump(_cont, sf, indent=4)
	print(router.url_path_for('home_new'))
	response = RedirectResponse(url=router.url_path_for('home_new'), status_code=status.HTTP_303_SEE_OTHER)
	print(response)
	response.set_cookie('hello', 'world')

	return response
	# return RedirectResponse(url=router.url_path_for('home_new'))
	# return 

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









