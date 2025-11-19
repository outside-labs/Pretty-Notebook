import os
import datetime
import json

import fastapi
from fastapi import Depends

from pydantic import BaseModel

from .auth_api import oauth2_scheme



router = fastapi.APIRouter()



class ObsidianBlogLayout(BaseModel):
	NAV_BRAND: str
	footer: str
	hljs_style: str
	nav_pages: dict
	darkmode: bool 


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


async def update_layout(NAV_BRAND: str, footer: str, hljs_style: str, nav_pages: dict, darkmode: bool):
	""" 
	"""
	lout = dict(
		NAV_BRAND=NAV_BRAND,
		footer=footer,
		hljs_style=hljs_style,
		nav_pages=nav_pages,
		darkmode=darkmode
		)
	
	with open(os.path.join(f'blog-settings.json'), 'w') as pf:
		json.dump(lout, pf, indent=4)

	return lout


@router.post('/api/layout', name='update_lout', status_code=201, response_model=ObsidianBlogLayout, dependencies=[Depends(oauth2_scheme)]) # if ok status_code 200 -> 201, if not, it's handled in the ValidationError
async def layout_post(lout_sub: ObsidianBlogLayout):
	""" """
	n = lout_sub.NAV_BRAND
	f = lout_sub.footer
	h = lout_sub.hljs_style
	np = lout_sub.nav_pages
	dm = lout_sub.darkmode
	return await update_layout(n, f, h, np, dm)


