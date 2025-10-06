import os
import re
import subprocess
import json
from collections import namedtuple, defaultdict

import markdown as md
import requests



def int_link_repl(matchobj):
	""" regex replacement function for [[]] internal Obsidian links -> mysite.com/single-slug
	"""
	return f"<a href='/{matchobj.group(1).replace('_', '-').replace(' ', '-').lower()}'>{matchobj.group(1)}</a>"

def int_img_repl(matchobj):
	""" regex replacement function for ![[]] internal Obsidian links -> mysite.com/single-slug
		todo: accept clean ( .png | .jpg ||)
	"""
	return f"""<img class="img-fluid" src='static/imgs/{matchobj.group(1)}'>"""

def int_tag_repl(matchobj):
	""" regex #tags out to distinguish vs # space means md header1 """
	return f"\\#{matchobj.group(1)}"

def md_mermaid_repl(matchobj):
	""" re """
	return f'<div class="mermaid">{matchobj.group(1)}</div>'

def md_nakedhref_repl(matchobj):
	""" regex replacement function for e.g. http://www.blahblahblah.com -> 
		[http://www.blahblahblah.com](http://www.blahblahblah.com)
		markdown syntax so that on md -> html, these links are clickable
	"""
	return f"[{matchobj.group(1)}]({matchobj.group(1)})"



ObsidianNote = namedtuple('Note', ['name', 'md', 'links', 'tags', 'urls'])



class ObsidianNotebook:

	OBS_INT_LNK = r'\[\[([^]]+)\]\]'
	OBS_IMG_LNK = r'!\[\[([^]]+)\]\]'
	OBS_INT_TAG = r'#([A-Za-z]+)' 

	MD_CODE = r'```([^`]*)```' #.\s\S
	MD_MERMAID = r'```mermaid([^`]*)```'

	MD_EXT_LINK = r'\[([^]]+)\]\(([^)]+)\)'
	HTTP_NAKED_LNK = r'[^\[](https?://[^;,\s\]\*]+)'

	COMMIT_TAG = '#public'

	def __init__(self):
		if not os.path.exists('settings.json'):
			raise ImportError("required settings.json file not found, please see settings_template.json")
		
		with open('settings.json') as cf:
			self.config = json.load(cf)

		self.NOTE_PATH = self.config.get('NOTE_PATH')
		self.IMG_PATH = self.config.get('IMG_PATH')
		self.HTML_PATH = self.config.get('HTML_PATH')

		self.notes = defaultdict()
		self.open_md()

	def open_md(self):
		""" open all files in the Obsidian Notebook path into memory """
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
						urls=self.get_urls(fo)
						)

					self.notes.update({fname: n})

	def find(self, regex):
		for f, n in self.notes.items():
			p = re.compile(regex)

	def get_urls(self, note):
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

		nout = md.markdown(nout, extensions=['fenced_code', 'nl2br'])

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


	def post_commits_to_blog_api(self):
		""" """
		self.open_md() # fresh retrival

		print(f'\nremote commit:')
		for n in self.notes.values():
			if re.search(self.COMMIT_TAG, n.md):
				nout = self.convert_to_html(note=n.md)
				r = requests.post('http://127.0.0.1:8000/api/publishment',
					json={"name": n.name.replace('_', '-').replace(' ', '-').lower(), "content": nout})
				
				print(f'\t{n.name} -> {r}')

				for img in re.findall(self.OBS_IMG_LNK, n.md):
					f = open(os.path.join(self.IMG_PATH, img), 'rb')
					r = requests.post('http://127.0.0.1:8000/api/image',
						files={"filename": img, "file": f, "content_type": "image/jpeg"})
					
					print(f'\t{img} -> {r}') # r.content = {"filename": "examp.jpeg"}


	def get_pub_commits(self):
		""" """
		r = requests.get('http://127.0.0.1:8000/api/publishments')
		print(r.json())



def main():

	nb = ObsidianNotebook()
	nb.write_commits_to_local_html()
	nb.post_commits_to_blog_api()






if __name__ == '__main__':
	main()



