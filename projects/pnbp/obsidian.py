import os
import subprocess
import json
import re

import click

from models import ObsidianNotebook


@click.group()
def obsidiancli():
	pass



""" commands writing collections to specific notebook files:
"""
def _collect_subl_projs(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	projs = []
	for fn in os.listdir(nb.NOTE_PATH):
		if fn.endswith('.sublime-project'):
			projs.append(fn)

	obsidianmd = "\n\n".join([f'![[{p}]]' for p in projs])

	with open(os.path.join(nb.NOTE_PATH, 'sublime-project.md'), 'w') as f:
		f.write(obsidianmd)

@click.command()
def collect_subl_projs():
	""" notebook/example.sublime_project -> sublime-project.md
	"""
	_collect_subl_projs()



def _collect_all_notes(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	ns = []

	for fn in os.listdir(nb.NOTE_PATH):
		if fn.endswith('.md'):
			ns.append(fn)

	ns.sort()

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])

	with open(os.path.join(nb.NOTE_PATH, 'all notes.md'), 'w') as f:
		f.write(obsidianmd)

@click.command()
def collect_all_notes():
	""" all .md files linked -> notebook/all notes.md
	"""
	_collect_all_notes()




def _collect_all_urls(nb=None):
	if not nb:
		nb = ObsidianNotebook()


	all_urls = []
	for n in nb.notes.values():
		if n.name not in ('all urls'):
			for u in n.urls:
				all_urls.append(u)

	with open(os.path.join(nb.NOTE_PATH, 'all urls.md'), 'w') as f:
		f.write('\n'.join(str(l) for l in all_urls))

@click.command()
def collect_all_urls():
	""" all regex-ed http-based urls -> notebook/all urls.md
	"""
	_collect_all_urls()



def _collect_all_public(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	ns = []

	for fn, n in nb.notes.items():
		if re.search(nb.COMMIT_TAG, n.md):
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "#public posts:\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all public.md'), 'w') as f:
		f.write(obsidianmd)

@click.command()
def collect_all_public():
	""" if note contains #public -> notebook/all public.md
	"""
	_collect_all_public()



@click.command()
def touch_all_public():
	""" update the mod date for all #public """
	_collect_all_public()
	nb = ObsidianNotebook()
	for f in nb.notes['all public'].links:
		subprocess.run(['touch', os.path.join(nb.NOTE_PATH, f+'.md')])



def _collect_terms(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	ns = []

	for fn, n in nb.notes.items():
		if re.search(r'\[\[\s?TERMS\s?\]\]', n.md):
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all [[TERMS]] :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'TERMS.md'), 'w') as f:
		f.write(obsidianmd)

@click.command()
def collect_terms():
	""" if found [[TERMS]] -> nb/TERMS.md
	"""
	_collect_terms()



def _collect_all_unlinked(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	ns = []
	for fn, n in nb.notes.items():
		if not re.search(nb.OBS_INT_LNK, n.md):
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all unlinked :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all unlinked.md'), 'w') as f:
		f.write(obsidianmd)

@click.command()
def collect_all_unlinked():
	""" if not a single [[]] found -> nb/all unlinked.md
	"""
	_collect_all_unlinked()



def _collect_all_empty(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	ns = []
	for fn, n in nb.notes.items():
		if len(n.md) < 4:
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all unlinked :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all empty.md'), 'w') as f:
		f.write(obsidianmd)

@click.command()
def collect_all_empty():
	""" if a note is created on path w/out context -> nb/all empty.md
	"""
	_collect_all_empty()



def _delete_all_empty(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	# _collect_all_empty(nb)

	for l in nb.notes['all empty'].links:
		lfn = l + '.md'
		if os.path.exists(os.path.join(nb.NOTE_PATH, lfn)):
			print(l)
			os.remove(os.path.join(nb.NOTE_PATH, lfn))

@click.command()
def delete_all_empty():
	""" delete all empty notes from nb/all empty.md
	"""
	_delete_all_empty()



def _collect_all_unheadered(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	ns = []
	for fn, n in nb.notes.items():
		if not n.header:
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all unheadered :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all unheadered.md'), 'w') as f:
		f.write(obsidianmd)

@click.command()
def collect_all_unheadered():
	"""
	"""
	_collect_all_unheadered()



def _collect_all_moc(nb=None):
	if not nb:
		nb = ObsidianNotebook()

	ns = []
	for fn in nb.notes.keys():
		if fn.isupper():
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all MOC :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all MOC.md'), 'w') as f:
		f.write(obsidianmd)

@click.command()
def collect_all_moc():
	""" """
	_collect_all_moc()



def _collect_all_tags(nb=None):
	if not nb:
		nb = ObsidianNotebook()


	ns = []
	for fn, n in nb.notes.items():
		fn_w = f'[[{fn}]] '

		if n.tags:
			for t in n.tags:
				fn_w += f' #{t}'
			ns.append(fn_w)

	with open(os.path.join(nb.NOTE_PATH, 'all tags.md'), 'w') as f:
		f.write('\n'.join(str(ft) for ft in ns))

@click.command()
def collect_all_tags():
	""" """
	_collect_all_tags()



def _collect_git_diff(nb=None):
	# not worth having 
	if not nb:
		nb = ObsidianNotebook()

	ns = subprocess.run(['git', 'diff', '-C', nb.NOTE_PATH], capture_output=True).stdout.decode('utf-8').strip()

	with open(os.path.join(nb.NOTE_PATH, 'all diff.md'), 'w') as f:
		f.write(ns)




@click.command()
def obsidian_collect_all():
	""" perform all collect- commands in succession
	"""
	notebook = ObsidianNotebook()

	_collect_all_urls(nb=notebook)
	_collect_all_notes(nb=notebook)
	_collect_subl_projs(nb=notebook)
	_collect_all_public(nb=notebook)
	_collect_terms(nb=notebook)
	_collect_all_unlinked(nb=notebook)
	_collect_all_empty(nb=notebook)
	# _delete_all_empty(nb=notebook) -> avail at obsidian-delete-all
	_collect_all_unheadered(nb=notebook)
	_collect_all_moc(nb=notebook)
	_collect_all_tags(nb=notebook)
	# _collect_git_diff(nb=notebook)




""" obsidian-blog api connection:
"""
@click.command()
def commit_local_html():
	""" if note contains #public, -> blog """
	nb = ObsidianNotebook()
	nb.write_commits_to_local_html()


@click.command()
def commit_remote_api():
	""" if note contains #public, -> blog """
	nb = ObsidianNotebook()
	nb.post_commits_to_blog_api()




# def _ho



obsidiancli.add_command(collect_subl_projs)
obsidiancli.add_command(collect_all_notes)
obsidiancli.add_command(collect_all_urls)
obsidiancli.add_command(collect_all_public)
obsidiancli.add_command(collect_terms)
obsidiancli.add_command(collect_all_unlinked)
obsidiancli.add_command(collect_all_empty)
obsidiancli.add_command(delete_all_empty)
obsidiancli.add_command(collect_all_moc)
obsidiancli.add_command(collect_all_tags)

obsidiancli.add_command(obsidian_collect_all)

obsidiancli.add_command(touch_all_public)


obsidiancli.add_command(commit_local_html)
obsidiancli.add_command(commit_remote_api)




if __name__ == '__main__':
	obsidiancli()
