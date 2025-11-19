import os
import re
import inspect
import subprocess

from models import ObsidianNotebook
from wrappers import pass_nb, arrow_call


""" commands writing collections to specific notebook files:
"""
def _collect_all_stats(nb=None):
	""" """
	pass

@pass_nb
def _collect_all_notes(nb=None):
	""" all .md files linked -> notebook/all notes.md
	"""
	ns = []
	for fn in os.listdir(nb.NOTE_PATH):
		if fn.endswith('.md'):
			ns.append(fn)

	ns.sort()

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])

	with open(os.path.join(nb.NOTE_PATH, 'all notes.md'), 'w') as f:
		f.write(obsidianmd)


@pass_nb
def _collect_all_urls(nb=None):
	""" all regex-ed http-based urls -> notebook/all urls.md
	"""
	all_urls = []
	for n in nb.notes.values():
		if n.name not in ('all urls'):
			for u in n.urls:
				all_urls.append(u)

	with open(os.path.join(nb.NOTE_PATH, 'all urls.md'), 'w') as f:
		f.write('\n'.join(str(l) for l in all_urls))


@pass_nb
def _collect_all_public(nb=None):
	""" if note contains #public -> notebook/all public.md
	"""
	ns = []

	for fn, n in nb.notes.items():
		if re.search(nb.COMMIT_TAG, n.md):
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "#public posts:\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all public.md'), 'w') as f:
		f.write(obsidianmd)


@pass_nb
def _touch_all_public(nb=None):
	""" update the mod date for all #public """
	_collect_all_public(nb)

	for f in nb.notes['all public'].links:
		subprocess.run(['touch', os.path.join(nb.NOTE_PATH, f+'.md')])


@pass_nb
def _collect_terms(nb=None):
	""" if found [[TERMS]] -> nb/TERMS.md
	"""
	ns = []

	for fn, n in nb.notes.items():
		if re.search(r'\[\[\s?TERMS\s?\]\]', n.md):
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all [[TERMS]] :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'TERMS.md'), 'w') as f:
		f.write(obsidianmd)


@pass_nb
def _collect_all_unlinked(nb=None):
	""" if not a single [[]] found -> nb/all unlinked.md
	"""
	ns = []
	for fn, n in nb.notes.items():
		if not re.search(nb.OBS_INT_LNK, n.md):
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all unlinked :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all unlinked.md'), 'w') as f:
		f.write(obsidianmd)


@pass_nb
def _collect_all_empty(nb=None):
	""" if a note is created on path w/out context -> nb/all empty.md
	"""
	ns = []
	for fn, n in nb.notes.items():
		if len(n.md) < 4:
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all unlinked :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all empty.md'), 'w') as f:
		f.write(obsidianmd)


@pass_nb
def _delete_all_empty(nb=None):
	""" delete all empty notes from nb/all empty.md
	"""
	# _collect_all_empty(nb) # refresh
	for l in nb.notes['all empty'].links:
		lfn = l + '.md'
		if os.path.exists(os.path.join(nb.NOTE_PATH, lfn)):
			print(l)
			os.remove(os.path.join(nb.NOTE_PATH, lfn))


@pass_nb
def _collect_all_unheadered(nb=None):
	"""
	"""
	ns = []
	for fn, n in nb.notes.items():
		if not n.header:
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all unheadered :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all unheadered.md'), 'w') as f:
		f.write(obsidianmd)


@pass_nb
def _collect_all_moc(nb=None):
	"""
	"""
	ns = []
	for fn in nb.notes.keys():
		if fn.isupper():
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])
	obsidianmd = "all MOC :\n\n --- \n\n " + obsidianmd

	with open(os.path.join(nb.NOTE_PATH, 'all MOC.md'), 'w') as f:
		f.write(obsidianmd)


@pass_nb
def _collect_all_tags(nb=None):
	"""
	"""
	ns = []
	
	ns.append(', '.join([t for t in nb.tags]))
	
	ns.append('--- ')

	for t in nb.tags:
		t_w = f'{t} - '
		for n in nb.get_tagged(t):
			if not n.name == 'all tags':
				t_w += f' [[{n.name}]], '

		ns.append(t_w.rstrip(', '))

	ns.append('--- ')

	for n in nb.notes.values():
		if not n.name == 'all tags':
			fn_w = f'[[{n.name}]] - '

			if n.tags:
				for t in n.tags:
					fn_w += f' #{t}, '

				ns.append(fn_w.rstrip(', '))
	
	with open(os.path.join(nb.NOTE_PATH, 'all tags.md'), 'w') as f:
		f.write('\n'.join(str(ft) for ft in ns))


# @pass_nb
# def _collect_git_diff(nb=None):
# 	""" not worth having -> parse it later?
# 	"""
# 	ns = subprocess.run(['git', 'diff', '-C', nb.NOTE_PATH], capture_output=True).stdout.decode('utf-8').strip()

# 	with open(os.path.join(nb.NOTE_PATH, 'all diff.md'), 'w') as f:
# 		f.write(ns)


@pass_nb
def _collect_subl_projs(nb=None):
	""" notebook/example.sublime_project -> sublime-project.md
	"""
	projs = []
	for fn in os.listdir(nb.NOTE_PATH):
		if fn.endswith('.sublime-project'):
			projs.append(fn)

	obsidianmd = "\n\n".join([f'![[{p}]]' for p in projs])

	with open(os.path.join(nb.NOTE_PATH, 'sublime-project.md'), 'w') as f:
		f.write(obsidianmd)


@arrow_call
@pass_nb
def _obsidian_collect_all(nb=None):
	""" perform all collect- commands in succession
	"""
	for k, func in globals().items():
		if k.startswith('_collect') and inspect.isfunction(func):
			print(f'{func.__name__} -->')
			func(nb) #call each function with the nb instance passed 






if __name__ == '__main__':
	pass
	# nb = ObsidianNotebook()
	# _collect_all_stats(nb)
