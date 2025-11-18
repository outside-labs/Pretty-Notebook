import os
import re
import subprocess
import json
import datetime
from collections import namedtuple, defaultdict
from getpass import getpass
# from pathlib import Path

import markdown as md
import requests

from helpers import (int_link_repl, int_img_repl, int_tag_repl,
						md_mermaid_repl, md_nakedhref_repl, comment_unescape,
						_convert_datetime)



# ObsidianNote = namedtuple('Note', ['name', 'md', 'links', 'tags', 'urls', 'mtime'])

class ObsidianNote(namedtuple('Note', ['name', 'md', 'links', 'tags', 'urls', 'cblocks', 'mtime'])):

	def __new__(cls, name, md, links, tags, urls, cblocks, mtime):
		"""
		:param str name: the filename stripped of .md
		:param str md: the in mem note context read from file
		:param list links: all regex found [[links]] 's in md
		:param list tags: all regex found #tag 's in md
		:param list urls: all regex found http/https links in md
		:param list cblocks: all regex found ```backtick code blocks```
		:param str mtime: the local md most recent modification date
			-> used against remote blog api to determine if POST required
		"""
		all_tags = [f'#{t}' for t in tags]

		_tags = list(set(all_tags.copy()))
		_remove = defaultdict(int)
		for t in _tags:
			for l in urls:
				if (num_occur := len(re.findall(t, l))):
					_remove[t] += num_occur
			for b in cblocks:
				if (num_occur := len(re.findall(t, b))):
					_remove[t] += num_occur

		for tag, occ in _remove.items():
			for x in range(occ):
				if tag in all_tags:
					all_tags.remove(tag)
		
		tags = list(set(all_tags)) # only legitimate #tag's remain
		urls = list(set(urls)) # <- doing here so that duplicate urls don't create tags

		return super().__new__(cls, name, md, links, tags, urls, cblocks, mtime)

	def __init__(self, *args, **kwargs):
		""" 
		:param md_out: safety first, make it hard to overwrite any note file
			-> set self.md_out = "as example, correct as is string instance"
			-> update file via self.save()
		"""
		self.md_out = '' 	

	def __str__(self):
		""" """
		return self.name

	@property
	def slugname(self):
		""" My Note Name -> my-note-name
		"""
		_name = re.sub(r'[^a-zA-Z1-9\s_-]+', '', self.name)
		_name = _name.lower().replace(' ', '-').replace('_', '-')
		slugname = "-".join([w for w in _name.split('-') if w])
		return slugname

	@property
	def sections(self):
		"""	"""
		return [x.strip() for x in self.md.split('---')]

	@property
	def header(self):
		""" """
		if not re.match(r'^Links', self.sections[0]):
			return None

		return self.sections[0]

	def save(self, nb):
		""" save note to .md file on NOTE_PATH,
			if provided self.md_out has been updated.
		"""
		if not isinstance(self.md_out, str):
			print('this')
			raise TypeError(f'ObsidianNote.md_out must be a str, not {type(self.md_out)}')

		if self.md_out:
			with open(os.path.join(nb.NOTE_PATH, self.name+'.md'), 'w') as nf:
				nf.write(self.md_out)

	def is_tagged(self, tag: str)->bool:
		""" 
		:param tag: the #tag in question
		"""
		tag = f"#{tag.lstrip('#')}" #failsafe

		if tag in self.tags:
			return True
		return False

	def is_linked(self, link: str="", at_all=False)->bool:
		""" 
		"""
		if at_all and self.links:
			return True

		if not link and not at_all:
			raise ValueError("Did you mean to call is_linked(at_all=True)?\nOtherwise, provide is_linked(link='internal-link-looking-for')")

		if link in self.links:
			return True

		return False








class ObsidianNotebook:
	""" class owned common regex patterns
	"""
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
			as a list of dicts e.g. {"my note name": ObsidianNote}
			available at nb.notes
		"""
		for f in os.listdir(self.NOTE_PATH):
			fname = f.split('.')[0]
			if f.endswith('.md'):
				with open(os.path.join(self.NOTE_PATH, f), 'r') as fo:
					fo = fo.read()

					n = ObsidianNote(
						name=fname,
						md=fo,
						links=[m.strip() for m in re.findall(self.OBS_INT_LNK, fo)],
						tags=re.findall(self.OBS_INT_TAG, fo),
						urls=self.collect_urls(fo),
						cblocks=re.findall(self.MD_CODE, fo),
						mtime=datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(self.NOTE_PATH, f)))
						)

					self.notes.update({fname: n})

		self.notes = dict(sorted(self.notes.items()))

	def generate_note(self, name, md_out, overwrite=False):
		""" """
		name = name.strip()

		if name in self.notes.keys() and not overwrite:
			raise FileExistsError(f"Cannot generate a new note with name {name}.")
 
		n = ObsidianNote(name=name, md='', links=[], tags=[], urls=[], cblocks=[], mtime='')
		n.md_out = md_out
		n.save(self)
		# self.open_md() # refresh -> new note n attrs fill live ^^

	def get(self, name):
		"""
		:param name: name of the note
		:returns: ObsidianNote instance or None
		"""
		name = name.rstrip('.md').rstrip('.html')
		print(name)
		if (note := self.notes.get(name)):
			print(note)
			return note

		for n in self.notes.values():
			if n.slugname == name:
				return n

		return None

	def get_tagged(self, tag):
		""" """
		t_notes = []
		for n in self.notes.values():
			if n.is_tagged(tag):
				t_notes.append(n)

		return t_notes

	@property
	def tags(self)->list:
		""" """
		ts = []
		for n in self.notes.values():
			for t in n.tags:
				ts.append(t)

		return sorted(list(set(ts)))
	

	def find(self, regex):
		""" a user convenience method to effectively grep notebook
		"""
		print(f'regex: {regex}')

		notes = []
		for fn, n in self.notes.items():
			p = re.compile(regex)
			if (m := p.search(n.md)):
				print(f'\t -> {fn}')
				print(m)
				print(f'found: {m}')
				notes.append(n)

		return notes

	def find_and_replace(self, regex, replace):
		""" be careful, use find first
		"""
		if (ntc := self.find(regex)):
			for n in ntc:
				n.md_out = re.sub(regex, replace, n.md)
				n.save(self)

	def collect_urls(self, note)->list:
		""" a regex search mtd 
			for http/https links
			available via each n.urls

		:param note: 
		"""
		ext_links = []

		p = re.compile(self.MD_EXT_LINK)
		for l in p.findall(note):
			ext_links.append(l[1])

		p = re.compile(self.HTTP_NAKED_LNK)
		for l in p.findall(note):
			ext_links.append(l.rstrip('.').rstrip(')'))

		# return list(set(ext_links))
		return ext_links
	
	"""
	"""
	def replace_imglinks(self, note):
		""" a regex replace mtd """
		p = re.compile(self.OBS_IMG_LNK)
		return p.sub(int_img_repl, note)

	def replace_obslinks(self, note):
		""" a regex replace mtd """
		p = re.compile(self.OBS_INT_LNK)
		return p.sub(int_link_repl, note)

	def replace_obstags(self, note):
		""" a regex replace mtd """
		p = re.compile(self.OBS_INT_TAG)
		return p.sub(int_tag_repl, note)

	def replace_mermaid(self, note):
		""" a regex replace mtd """
		p = re.compile(self.MD_MERMAID)
		return p.sub(md_mermaid_repl, note)

	def replace_nakedhref(self, note):
		""" a regex replace mtd """
		p = re.compile(self.HTTP_NAKED_LNK)
		return p.sub(md_nakedhref_repl, note)

	def fix_blocked_comments(self, note):
		""" a regex replace mtd """
		p = re.compile(r'<code class="(.+)">((.|\n)*)</code>')
		return p.sub(comment_unescape, note)


	def convert_to_html(self, note):
		""" apply all the regex method changes to 
			a single note

		:param note: the note content itself (n.md)
		"""
		nout = self.replace_imglinks(note)
		nout = self.replace_obslinks(nout)
		nout = self.replace_obstags(nout)
		nout = self.replace_mermaid(nout)
		nout = self.replace_nakedhref(nout)

		nout = md.markdown(nout, extensions=['fenced_code',	'nl2br', 'markdown.extensions.tables'], use_pygments=True)

		nout = self.fix_blocked_comments(nout)

		return nout


	def write_commits_to_local_html(self):
		""" a local debugging mtd 
			-> HTML_PATH/.html ... 
		"""
		self.open_md() # fresh retrival 

		print(f'\nlocal commit: {self.HTML_PATH}')
		for n in self.notes.values():
			if re.search(self.COMMIT_TAG, n.md):
				nout = self.convert_to_html(note=n.md)
				of = open(os.path.join(self.HTML_PATH, f"{n.slugname}.html"), 'w')
				of.write(nout) #https://python-markdown.github.io/extensions/fenced_code_blocks/
				of.close()

				print(f'\t{n.name} ---> {self.HTML_PATH}')

	""" obsidian-blog api connection methods:
	"""
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

	def get_authed_user(self):
		""" """
		h = nb.get_headers()
		r = requests.get(f'{self.API_BASE}/api/users/me', headers=h)
		print(r)
		print(r.json())

	def get_api_home(self):
		""" """
		h = nb.get_headers()
		r = requests.get(f'{self.API_BASE}/api', headers=h)
		# print(r.text)
		# print(r.json())

	def get_pub_commits(self)->dict:
		""" internal use
			request a remote filepath check for the purpose of 
			making smarter POST updates
		"""
		h = self.get_headers()
		r = requests.get(f'{self.API_BASE}/api/publishments', headers=h)
		pub_data = r.json()

		nameMtime = {}
		for pub in pub_data:
			pub['mod_date'] = _convert_datetime(pub['mod_date'])
			nameMtime.update({pub['pub_name']: pub['mod_date']})

		return nameMtime

	def get_img_commits(self)->dict:
		""" internal use
			request a remote filepath check for the purpose of 
			making smarter POST updates
		"""
		h = self.get_headers()
		r = requests.get(f'{self.API_BASE}/api/images', headers=h)
		img_data = r.json()

		nameMtime = {}
		for img in img_data:
			img['mod_date'] = _convert_datetime(img['mod_date'])
			nameMtime.update({img['img_name']: img['mod_date']})

		return nameMtime

	def delete_unlisted_post(self, rname):
		""" """
		h = self.get_headers()
		r = requests.delete(f'{self.API_BASE}/api/publishment/{rname}', headers=h)
		print(f'(removed) {r.json()["pub_name"]} -> {r}')


	def post_commits_to_blog_api(self):
		""" the main method
		"""
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
			fname = n.slugname + '.html'
			# rname = n.name.lower().replace('_', '-').replace(' ', '-')+'.html'
			if re.search(self.COMMIT_TAG, n.md):
				post_names.append(fname)
				if fname in pub_pub_names:
					if pub_pub_data[fname] < n.mtime: # change has occured 
						to_post = True
				else: # it's newly #public
					to_post = True

			if to_post:
				nout = self.convert_to_html(note=n.md)
				r = requests.post(f'{self.API_BASE}/api/publishment',
					json={"name": n.slugname, "content": nout}, # n.name.replace('_', '-').replace(' ', '-').lower()
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

	def blog_settings_post(self):

		with open(os.path.join(self.NOTE_PATH, 'blog-settings.json'), 'r') as f:
			h = self.get_headers()
			# print(json.load(f)
			r = requests.post(f'{self.API_BASE}/api/layout', json=json.load(f), headers=h)
			print(r)
















if __name__ == '__main__':
	pass








