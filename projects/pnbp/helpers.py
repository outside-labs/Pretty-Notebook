import datetime


""" base md -> html 
	re.sub str replacement functions
"""
def int_link_repl(matchobj):
	""" regex replacement function for [[]] internal Obsidian links -> mysite.com/single-slug
	"""
	return f"<a href='/{matchobj.group(1).strip().replace('_', '-').replace(' ', '-').lower()}'>{matchobj.group(1)}</a>"

def int_img_repl(matchobj):
	""" regex replacement function for ![[]] internal Obsidian links -> mysite.com/single-slug
		todo: accept clean ( .png | .jpg ||)
	"""
	return f"""<img class="img-fluid" src='static/imgs/{matchobj.group(1)}'>"""

def int_tag_repl(matchobj):
	""" regex #tags out to distinguish vs
		# space means md header1
		-> \\#tag
	"""
	return f"\\#{matchobj.group(1)}"

def md_mermaid_repl(matchobj):
	""" required "scripts" in blog/static/layout.html 
	"""
	return f'<div class="mermaid">{matchobj.group(1)}</div>'

def md_nakedhref_repl(matchobj):
	""" regex replacement function for e.g. http://www.blahblahblah.com -> 
		[http://www.blahblahblah.com](http://www.blahblahblah.com)
		markdown syntax so that on md -> html, these links are 
		then rendered clickable on md.markdown()
	"""
	return f"[{matchobj.group(1)}]({matchobj.group(1)})"



""" tasks re.sub str replacement functions
"""
def md_task_uncheck(matchobj):
	""" """
	t = matchobj.group(3).strip().replace(r'\t', ' ')

	if matchobj.group(1) == '\t':
		return f'\t- [ ] {t}'

	return f'- [ ] {t}'

def md_reoccurring_task_uncheck(matchobj):
	""" """
	return f'- [ ] {t}'



""" blog api connection helpers
""" 
def _convert_datetime(dt: str):
	""" 
	:param dt: fastapi datetime object e.g. 
		'2021-05-13T11:22:10.373376' or
		'2019-12-15T15:32:34'

	:returns: 2019-12-15 15:32:34
	"""
	try:
		return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f')
	except ValueError:
		try:
			return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
		except:
			raise Exception(f'Something went wrong with the format parsing of {dt}')





