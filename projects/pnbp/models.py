import os
import re
import subprocess
import json
import datetime
from collections import namedtuple, defaultdict
from getpass import getpass

import markdown as md
import requests

# from pathlib import Path


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
	""" regex #tags out to distinguish vs # space means md header1 """
	return f"\\#{matchobj.group(1)}"

def md_mermaid_repl(matchobj):
	""" required "scripts" in layout.html """
	return f'<div class="mermaid">{matchobj.group(1)}</div>'

def md_nakedhref_repl(matchobj):
	""" regex replacement function for e.g. http://www.blahblahblah.com -> 
		[http://www.blahblahblah.com](http://www.blahblahblah.com)
		markdown syntax so that on md -> html, these links are clickable
	"""
	return f"[{matchobj.group(1)}]({matchobj.group(1)})"



# ObsidianNote = namedtuple('Note', ['name', 'md', 'links', 'tags', 'urls', 'mtime'])

class ObsidianNote(namedtuple('Note', ['name', 'md', 'links', 'tags', 'urls', 'mtime'])):

	def __new__(cls, name, md, links, tags, urls, mtime):
		return super().__new__(cls, name, md, links, tags, urls, mtime)

	def __init__(self, *args, **kwargs):
		self.md_out = ''	

	@property
	def sections(self):
		""" """
		return [x.strip() for x in self.md.split('---')]

	@property
	def header(self):
		""" """
		if not re.match(r'^Links', self.sections[0]):
			return None

		return self.sections[0]

	def save(self, nb):
		""" """
		if not isinstance(self.md_out, str):
			print('this')
			raise TypeError(f'ObsidianNote.md_out must be a str, not {type(self.md_out)}')

		if self.md_out:
			with open(os.path.join(nb.NOTE_PATH, self.name+'.md'), 'w') as nf:
				nf.write(self.md_out)



class ObsidianNotebook:

	OBS_INT_LNK = r'\[\[([^]]+)\]\]'
	OBS_IMG_LNK = r'!\[\[([^]]+)\]\]'
	OBS_INT_TAG = r'#([A-Za-z]+)' 

	MD_CODE = r'```([^`]*)```'
	MD_MERMAID = r'```mermaid([^`]*)```'

	MD_EXT_LINK = r'\[([^]]+)\]\(([^)]+)\)'
	HTTP_NAKED_LNK = r'[^\(](https?://[^;,\s\]\*]+)'

	COMMIT_TAG = '#public'

	def __init__(self):
		self.conf_file = os.path.join(os.path.dirname(__file__), 'settings.json')
		# conf_file = Path(__file__).parent / 'settings.json' # same thing
		# with conf_file.open() as cf:

		if not os.path.exists(self.conf_file):
			raise ImportError("required settings.json file not found, please see settings_template.json")
		
		with open(self.conf_file) as cf:
			self.config = json.load(cf)

		self.NOTE_PATH = self.config.get('NOTE_PATH')
		self.IMG_PATH = self.config.get('IMG_PATH')
		self.HTML_PATH = self.config.get('HTML_PATH')

		self.API_BASE = self.config.get('API_BASE')
		self.API_TOKEN = self.config.get('API_TOKEN')

		self.notes = defaultdict()
		self.open_md()

	def open_md(self):
		""" open all files in the Obsidian Notebook path into memory
		"""
		for f in os.listdir(self.NOTE_PATH):
			fname = f.split('.')[0]
			if f.endswith('.md'):
				with open(os.path.join(self.NOTE_PATH, f), 'r') as fo:
					fo = fo.read()

					n = ObsidianNote(
						name=fname,
						md=fo,
						links=re.findall(self.OBS_INT_LNK, fo),
						tags=re.findall(self.OBS_INT_TAG, fo),
						urls=self.get_urls(fo),
						mtime=datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(self.NOTE_PATH, f)))
						)

					self.notes.update({fname: n})

	def find(self, regex):
		""" """
		print(f'regex: {regex}')
		for fn, n in self.notes.items():
			p = re.compile(regex)
			if p.search(n.md):
				print(f'\t -> {fn}')

	def get_urls(self, note):
		""" """
		ext_links = []

		p = re.compile(self.MD_EXT_LINK)
		for l in p.findall(note):
			ext_links.append(l[1])

		p = re.compile(self.HTTP_NAKED_LNK)
		for l in p.findall(note):
			ext_links.append(l.rstrip('.').rstrip(')'))

		return list(set(ext_links))
	
	def replace_imglinks(self, note):
		p = re.compile(self.OBS_IMG_LNK)
		return p.sub(int_img_repl, note)

	def replace_obslinks(self, note):
		p = re.compile(self.OBS_INT_LNK)
		return p.sub(int_link_repl, note)

	def replace_obstags(self, note):
		p = re.compile(self.OBS_INT_TAG)
		return p.sub(int_tag_repl, note)

	def replace_mermaid(self, note):
		p = re.compile(self.MD_MERMAID)
		return p.sub(md_mermaid_repl, note)

	def replace_nakedhref(self, note):
		p = re.compile(self.HTTP_NAKED_LNK)
		return p.sub(md_nakedhref_repl, note)

	def convert_to_html(self, note):
		""" a single note """

		nout = self.replace_imglinks(note)
		nout = self.replace_obslinks(nout)
		nout = self.replace_obstags(nout)
		nout = self.replace_mermaid(nout)
		nout = self.replace_nakedhref(nout)

		nout = md.markdown(nout, extensions=['fenced_code', 'nl2br', 'markdown.extensions.tables'], use_pygments=True)


		return nout


	def write_commits_to_local_html(self):
		"""  """
		self.open_md() # fresh retrival 

		print(f'\nlocal commit: {self.HTML_PATH}')
		for n in self.notes.values():
			if re.search(self.COMMIT_TAG, n.md):
				nout = self.convert_to_html(note=n.md)
				of = open(os.path.join(self.HTML_PATH, f"{n.name.replace('_', '-').replace(' ', '-').lower()}.html"), 'w')
				of.write(nout) #https://python-markdown.github.io/extensions/fenced_code_blocks/
				of.close()

				print(f'\t{n.name} ---> {self.HTML_PATH}')


	def get_headers(self):
		""" """
		return {'accept': 'application/json', 'authorization': f'Bearer {self.API_TOKEN}'}

	def refresh_token(self):
		""" """
		u = input('Username: ')
		p = getpass()
		h = self.get_headers()
		h.update({'Content-Type': 'application/x-www-form-urlencoded'})
		r = requests.post(f'{self.API_BASE}/token', data={'username': u, 'password': p}, headers=h)
		print(r)
		if r.status_code == 200:
			self.API_TOKEN = r.json()['access_token']

			with open(self.conf_file) as cf:
				config = json.load(cf)
				config.update({"API_TOKEN": self.API_TOKEN})

			with open(self.conf_file, 'w') as cf:
				json.dump(config, cf, indent=4)


	def post_commits_to_blog_api(self):
		""" """
		self.open_md() # fresh retrival
		h = self.get_headers()

		pub_pub_data = self.get_pub_commits()
		pub_pub_names = pub_pub_data.keys()

		pub_img_data = self.get_img_commits()
		pub_img_names = pub_img_data.keys()

		print(f'\nremote commit:')
		post_names = []
		for n in self.notes.values():
			to_post = False
			rname = n.name.lower().replace('_', '-').replace(' ', '-')+'.html'
			if re.search(self.COMMIT_TAG, n.md):
				post_names.append(rname)
				if rname in pub_pub_names:
					if pub_pub_data[rname] < n.mtime: # change has occured 
						to_post = True
				else: # it's newly #public
					to_post = True

			if to_post:
				nout = self.convert_to_html(note=n.md)
				r = requests.post(f'{self.API_BASE}/api/publishment',
					json={"name": n.name.replace('_', '-').replace(' ', '-').lower(), "content": nout},
					headers=h
					)
				
				print(f'\t{n.name} -> {r}')

				for img in re.findall(self.OBS_IMG_LNK, n.md):
					if not img in pub_img_names:
						try:
							f = open(os.path.join(self.IMG_PATH, img), 'rb')
							r = requests.post(f'{self.API_BASE}/api/image',
								files={"filename": img, "file": f, "content_type": "image/jpeg"},
								headers=h
								)
							
							print(f'\t\t{img} -> {r}') # r.content = {"filename": "examp.jpeg"}
						except FileNotFoundError:
							print(f'\t\t{img} -> Broken image link!')
					else:
						print(f'\t\t{img} -> EXISTS!')

		for p in pub_pub_names:
			if p not in post_names:
				self.delete_unlisted_post(p)



	def _convert_datetime(self, dt: str):
		""" """
		try:
			return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f')
		except ValueError:
			try:
				return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
			except:
				raise Exception(f'Something went wrong with the format parsing of {dt}')


	def get_pub_commits(self):
		""" """
		h = self.get_headers()
		r = requests.get(f'{self.API_BASE}/api/publishments', headers=h)
		pub_data = r.json()

		nameMtime = {}
		for pub in pub_data:
			pub['mod_date'] = self._convert_datetime(pub['mod_date'])
			nameMtime.update({pub['pub_name']: pub['mod_date']})

		return nameMtime

	def get_img_commits(self):
		""" """
		h = self.get_headers()
		r = requests.get(f'{self.API_BASE}/api/images', headers=h)
		img_data = r.json()

		nameMtime = {}
		for img in img_data:
			img['mod_date'] = self._convert_datetime(img['mod_date'])
			nameMtime.update({img['img_name']: img['mod_date']})

		return nameMtime

	def delete_unlisted_post(self, rname):
		""" """
		h = self.get_headers()
		r = requests.delete(f'{self.API_BASE}/api/publishment/{rname}', headers=h)
		print(f'(removed) {r.json()["pub_name"]} -> {r}')




def md_task_uncheck(matchobj):
	""" """
	t = matchobj.group(3).strip().replace(r'\t', ' ')

	if matchobj.group(1) == '\t':
		return f'\t- [ ] {t}'

	return f'- [ ] {t}'

# datetime.datetime.strptime('2021-05-13T11:22:10.373376', '%Y-%m-%dT%H:%M:%S.%f')
# datetime.datetime.strptime('2019-12-15T15:32:34', '%Y-%m-%dT%H:%M:%S')


def _collect_complete_tasks(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	TASK_INCOMPLETE = r'(^|\s)(-\s\[\s\]\s)(.*)'
	TASK_COMPLETE = r'(^|\s)(-\s\[x\]\s)(.*)'

	p = re.compile(TASK_COMPLETE)

	ns = nb.notes['housekeeping'].md.splitlines()

	for i, li in enumerate(ns):
		# print(li, '*')
		# if p.search(li):
			# if p.search(li).group(1) == '\t':
			# 	print('TAB')
			# print()
			# print(p.sub(md_task_uncheck, li))
			ns[i] = p.sub(md_task_uncheck, li)
		# if li.group(1) == '\t':
		# 	print('YES')

	print(ns)
	print('\n'.join(ns))
	nb.notes['housekeeping'].md_out = '\n'.join(ns)
	nb.notes['housekeeping'].save(nb)






def main():

	nb = ObsidianNotebook()
	# nb.write_commits_to_local_html()
	# nb.post_commits_to_blog_api()

	# r = requests.get('http://127.0.0.1:8000/token/')
	# print(r.text)

	# print(nb.notes['housekeeping'])
	# print(nb.notes['housekeeping'].md.splitlines())

	"""
	"""
	fin_items = ['- [x] bathroom: shower', '- [x] bathroom: toilet(s)', '- [x] some fake task']

	if fin_items:
		fin_item_str = '\n'.join(fin_items)

	new_day = True
	d_today = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
	repl_section = ''
	for i, s in enumerate(nb.notes['_complete'].sections):
		# print(s)
		# print(d_today)
		if re.match(d_today, s):

			repl_section = s + '\n' + fin_item_str
			_md_out = nb.notes['_complete'].sections.copy()
			_md_out[i] = repl_section


			nb.notes['_complete'].md_out = '\n\n--- \n'.join(_md_out)
			print(nb.notes['_complete'].md_out)
			nb.notes['_complete'].save(nb)

			# print(s.splitlines())
			new_day = False
	if new_day:
		_md_out = nb.notes['_complete'].sections.copy()
		_md_out.insert(1, f'{d_today}\n{fin_item_str}')
		nb.notes['_complete'].md_out = '\n\n--- \n'.join(_md_out)
		nb.notes['_complete'].save(nb)
		# print(nb.notes['_complete'].sections)






	if new_day:
		pass



	# for t in p.findall(nb.notes['housekeeping'].md):
	# 	# print()
	# 	# x = p.sub(md_task_uncheck, t[2])
	# 	# print(x)
	# 	# print(type(t))
	# 	pass


	# print(re.findall(TASK_INCOMPLETE, nb.notes['housekeeping'].md))




	# print(nb.get_pub_commits())
	# print(nb.get_img_commits())

	# print(nb._convert_datetime('2019-12-15T15:32:34'))\
	# h = nb.get_headers()
	# r = requests.get('http://127.0.0.1:8000/api/users/me', headers=h)
	# print(r)
	# print(r.json())
	# # r = requests.get('http://127.0.0.1:8000/api', headers=h)
	# # print(r.text)
	# # print(r.json())
	
	# nb.refresh_token()








if __name__ == '__main__':
	main()



