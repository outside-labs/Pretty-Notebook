import os
import re
import subprocess
import markdown as md
import json
from collections import namedtuple, defaultdict

import requests 


def int_link_repl(matchobj):
	""" regex replacement method for [[]] internal Obsidian links -> mysite.com/single-slug
	"""
	return f"<a href='/{matchobj.group(1).replace('_', '-').lower()}'>{matchobj.group(1)}</a>"

def int_img_repl(matchobj):
	""" regex replacement method for ![[]] internal Obsidian links -> mysite.com/single-slug
		todo: accept clean ( .png | .jpg ||)
	"""
	return f"""<img class="img-fluid" src='static/imgs/{matchobj.group(1)}'>"""

def int_tag_repl(matchobj):
	""" regex #tags out to distinguish vs # space means md header1 """
	return f"\\#{matchobj.group(1)}"


ObsidianNote = namedtuple('Note', ['name', 'of'])


class ObsidianNotebook:

	OBS_INT_LNK = r'\[\[([^]]+)\]\]'
	OBS_IMG_LNK = r'!\[\[([^]]+)\]\]'
	OBS_INT_TAG = r'#([A-Za-z])' 

	NOTE_PATH = '/Users/curtis/Library/Mobile Documents/com~apple~CloudDocs/Stuff/onotes'
	IMG_PATH = f'{NOTE_PATH}/imgs'

	HTML_PATH = '/Users/curtis/oblog'
	# -> services/

	COMMIT_TAG = '#public'


	def __init__(self):
		self.notes = defaultdict()
		self.open()
		

	def open(self):
		""" open all files in the Obsidian Notebook path into memory """
		for f in os.listdir(self.NOTE_PATH):
			fname = f.split('.')[0]
			if f.endswith('.md'):
				with open(os.path.join(self.NOTE_PATH, f), 'r') as fo:
					n = ObsidianNote(name=fname, of=fo.read())
					self.notes.update({fname: n})




	def convert_to_html(self, note):
		""" a single note """

		p = re.compile(self.OBS_IMG_LNK)
		nout = p.sub(int_img_repl, note)
		# print(nout)

		p = re.compile(self.OBS_INT_LNK)
		nout = p.sub(int_link_repl, nout)

		p = re.compile(self.OBS_INT_TAG)
		nout = p.sub(int_tag_repl, nout)

		nout = md.markdown(nout, extensions=['fenced_code'])

		return nout


	def write_commits_to_local_html(self):
		"""  """
		self.open()
		for n in self.notes.values():
			if re.search(self.COMMIT_TAG, n.of):
				nout = self.convert_to_html(note=n.of)
				of = open(os.path.join(self.HTML_PATH, f'{n.name}.html'), 'w')
				of.write(nout) #https://python-markdown.github.io/extensions/fenced_code_blocks/
				of.close()

				print(f'{n.name} ---> {self.HTML_PATH}')


	def post_commits_to_blog_api(self):
		""" """
		self.open()
		for n in self.notes.values():
			if re.search(self.COMMIT_TAG, n.of):
				nout = self.convert_to_html(note=n.of)
				r = requests.post('http://127.0.0.1:8000/api/publishment', json={"name": n.name, "content": nout})
				print(r)

				for img in re.findall(self.OBS_IMG_LNK, n.of):
					f = open(os.path.join(self.IMG_PATH, img), 'rb')
					r = requests.post('http://127.0.0.1:8000/api/image', files={"filename": img, "file": f, "content_type": "image/jpeg"})
					print(r.content)



def main():

	nb = ObsidianNotebook()
	nb.write_commits_to_local_html()
	nb.post_commits_to_blog_api()






if __name__ == '__main__':
	main()
	







# print(subprocess.run(['git', 'status'], capture_output=True))
# if subprocess.run(['git', 'status'], capture_output=True).stderr == b'fatal: not a git repository (or any of the parent directories): .git\n':
# 	subprocess.run(['git', 'init'], capture_output=True)

# b'On branch master\n\nNo commits yet\n\nUntracked files:\n  (use "git add <file>..." to include in what will be committed)\n\tnoncommit.md\n\tobsidianparse.py\n\ttest.html\n\ttest.md\n\nnothing added to commit but untracked files present (use "git add" to track)\n'

