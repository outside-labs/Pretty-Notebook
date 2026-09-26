import json
from pathlib import Path

import fastapi
from fastapi import Depends

from pydantic import BaseModel

import aiofiles

from .auth_api import get_current_user
from .atomic_io import atomic_write_text


router = fastapi.APIRouter()
WEB_SETTINGS_PATH = Path(__file__).resolve().parents[1] / 'web-settings.json'



class PNBPWebLayout(BaseModel):
	""" """
	NAV_BRAND: str
	NAV_PAGES: dict
	FOOTER: str
	TITLE: str

	darkmode: bool 
	hljs_light: str
	hljs_dark: str
	merm_light: str 
	merm_dark: str
	


async def render_nav(pages: dict):
	""" pre-converting NAV_PAGES dict to html 
	"""
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



async def get_layout_content():
	""" """
	async with aiofiles.open(WEB_SETTINGS_PATH, mode='r') as f:
		_cont = await f.read()
		_cont = json.loads(_cont)
		_cont['NAV_PAGES'] = await render_nav(_cont['NAV_PAGES'])

	return _cont



async def update_layout(NAV_BRAND: str, NAV_PAGES: dict, FOOTER: str, TITLE: str, darkmode: bool, 
							hljs_light: str, hljs_dark: str, merm_light: str, merm_dark: str):
	""" """
	lout = dict(
		NAV_BRAND=NAV_BRAND,
		NAV_PAGES=NAV_PAGES,
		FOOTER=FOOTER,
		TITLE=TITLE,
		darkmode=darkmode,
		hljs_light=hljs_light,
		hljs_dark=hljs_dark,
		merm_light=merm_light,
		merm_dark=merm_dark
		)
	
	await atomic_write_text(WEB_SETTINGS_PATH, json.dumps(lout, indent=4))

	return lout



@router.post('/api/layout', name='update_lout', status_code=201, response_model=PNBPWebLayout, dependencies=[Depends(get_current_user)])
async def layout_post(lout_in: PNBPWebLayout):
	""" Post Layout 
	"""
	nb = lout_in.NAV_BRAND
	np = lout_in.NAV_PAGES
	f = lout_in.FOOTER
	t = lout_in.TITLE
	dm = lout_in.darkmode
	hll = lout_in.hljs_light
	hld = lout_in.hljs_dark
	mml = lout_in.merm_light
	mmd = lout_in.merm_dark

	return await update_layout(nb, np, f, t, dm, hll, hld, mml, mmd)







