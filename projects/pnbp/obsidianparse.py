import os
import re
import subprocess

import markdown as md

import json


OBS_INT_LNK = r'\[\[([^]]+)\]\]'
OBS_IMG_LNK = r'!\[\[([^]]+)\]\]'

NOTE_PATH = '/Users/curtis/Library/Mobile Documents/com~apple~CloudDocs/Stuff/onotes'
IMG_PATH = f'{NOTE_PATH}/imgs'

HTML_PATH = '/Users/curtis/oblog'
# -> services/

COMMIT_TAG = '#public'




def int_link_repl(matchobj):
	""" """
	return f"<a href='/{matchobj.group(1).replace('_', '-').lower()}'>{matchobj.group(1)}</a>"

def int_img_repl(matchobj):
	return f"""<img class="img-fluid" src='static/imgs/{matchobj.group(1)}'>"""


def int_img_repl_test():
	with open(f'index.md', 'r') as f:
		f = f.read()
		p = re.compile(OBS_IMG_LNK)
		print(p.findall(f))
		f = p.sub(int_img_repl, f)
		print(f)





def convert_to_html():
	for f in os.listdir(NOTE_PATH):
		if f.endswith('.md'):
			with open(os.path.join(NOTE_PATH, f), 'r') as fo:
				fo = fo.read()
				if re.search(COMMIT_TAG, fo):
					p = re.compile(OBS_INT_LNK)
					fo = p.sub(int_link_repl, fo)
					fname = f.split('.')[0] + '.html'
					of = open(os.path.join(HTML_PATH, fname), 'w')
					of.write(md.markdown(fo, extensions=['fenced_code'])) #https://python-markdown.github.io/extensions/fenced_code_blocks/
					of.close()

# convert_to_html()

import requests 

def post_to_api():
	for f in os.listdir(NOTE_PATH):
		if f.endswith('.md'):
			with open(os.path.join(NOTE_PATH, f), 'r') as fo:
				fo = fo.read()
				if re.search(COMMIT_TAG, fo):
					if re.search(COMMIT_TAG, fo):
						p = re.compile(OBS_IMG_LNK)
						f = p.sub(int_img_repl, f)
						p = re.compile(OBS_INT_LNK)
						print(p.findall(f))
						f = p.sub(int_link_repl, f)
						f = md.markdown(f, extensions=['fenced_code'])
						r = requests.post('http://127.0.0.1:8000/api/publishment', json={"name": "test1", "content": f})
						print(r)


	# with open(f'index.md', 'r') as f:
	# # with open(f'{NOTE_PATH}/test1.md', 'r') as f:
	# 	f = f.read()
	# 	p = re.compile(OBS_IMG_LNK)
	# 	f = p.sub(int_img_repl, f)
	# 	p = re.compile(OBS_INT_LNK)
	# 	print(p.findall(f))
	# 	f = p.sub(int_link_repl, f)

	# 	f = md.markdown(f, extensions=['fenced_code'])
	# 	r = requests.post('http://127.0.0.1:8000/api/publishment', json={"name": "test1", "content": f})
	# 	print(r)
		# print(f)

		# of = open('test.html', 'w')
		# of.write(md.markdown(f, extensions=['fenced_code'])) #https://python-markdown.github.io/extensions/fenced_code_blocks/
		# of.close()






def post_image_to_api(filename):
	f = open(os.path.join(IMG_PATH, filename), 'rb')
	r = requests.post('http://127.0.0.1:8000/api/image', files={"filename": filename, "file": f, "content_type": "image/jpeg"})
	print(r.content)




def main():
	pass





if __name__ == '__main__':
	int_img_repl_test()
	post_to_api()
	post_image_to_api('360+BIRD+POSTER+final+no+text.jpg')




# print(subprocess.run(['git', 'status'], capture_output=True))
# if subprocess.run(['git', 'status'], capture_output=True).stderr == b'fatal: not a git repository (or any of the parent directories): .git\n':
# 	subprocess.run(['git', 'init'], capture_output=True)

# b'On branch master\n\nNo commits yet\n\nUntracked files:\n  (use "git add <file>..." to include in what will be committed)\n\tnoncommit.md\n\tobsidianparse.py\n\ttest.html\n\ttest.md\n\nnothing added to commit but untracked files present (use "git add" to track)\n'

