import os
import subprocess
import datetime
import re
from string import ascii_uppercase

from models import ObsidianNotebook
from wrappers import arrow_call

def str_strip_link(matchobj):
	""" """
	return f'[[{matchobj.group(1).strip()}]]'


def _fix_link_spacing(nb=None):
	""" [[ LINK ]] -> [[LINK]]
		useful for finiky apps like 1Writer
	"""
	p = re.compile(nb.OBS_INT_LNK)

	for n in nb.notes.values():
		if n.name == 'test1':
			n.md_out = p.sub(str_strip_link, n.md)
			n.save(nb)


def _add_leading_newline(nb=None):
	""" 
		useful for finiky apps like 1Writer
		where without, can't see header
	"""
	for n in nb.notes.values():
		if n.name == 'test1':
			if not n.md.startswith('\n'):
				n.md_out = '\n' + n.md
				n.save(nb)


def _collect_all_stats(nb=None):
	pass

def _fix_tags_collect(nb=None):
	# nb.MD_CODE
	# nb.OBS_INT_TAG
	p = re.compile(nb.MD_CODE)
	for n in nb.notes.values():
		if n.name == 'test1':
			print(p.findall(n.md))

			for t in n.tags:
				pass


""" -> tasks """
def _parse_today_note(nb=None):
	n = nb.get('TODAY')
	# print(n.sections)
	td = datetime.datetime.today().date()
	td = datetime.datetime.strftime(td, '%Y-%m-%d')
	print(td)
	for s in n.sections:
		# print(s)
		if s.strip().startswith(td):
			j = '\n'.join([x for x in s.split('\n') if not x.startswith('-')])
			print(j) #journal content
			# for x in :
			# 	if x.startswith('-'):
			# 		pass

			# print(s)

@arrow_call
def _git_commit_notebook(nb=None):
	"""
	"""
	# print(subprocess.run(['cd', nb.NOTE_PATH], capture_output=True)) doesn't hold, even with the function...
	st = subprocess.run(['git', '-C', nb.NOTE_PATH, 'status'], capture_output=True)
	print(st)

	if st.stderr == b'fatal: not a git repository (or any of the parent directories): .git\n':
		print(subprocess.run(['git', '-C', nb.NOTE_PATH, 'init'], capture_output=True))

	lt = datetime.datetime.strftime(datetime.datetime.now(), '%X')
	ld = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')

	print(subprocess.run(['git', '-C', nb.NOTE_PATH, 'add', '-A'], capture_output=True))
	print(subprocess.run(['git', '-C', nb.NOTE_PATH, 'commit', '-m' , f'Automated commit @ {lt} on {ld}'], capture_output=True))




def _nb_get_help():
	""" show the cli.py --help message 
	"""
	loc_p = os.path.dirname(__file__)
	cli_p = os.path.join(loc_p, 'cli.py')
	# print(lp)
	# no need to print as running the file runs the command
	subprocess.run(['python3', cli_p, '--help'])


# _nb_get_help()



#@pass_nb
def _collect_public_graph(nb=None):
	""" """
	# nb = ObsidianNotebook()

	ll = [ch for ch in ascii_uppercase] # link letters

	for i in range(2, 31): # support ~800 notes here (but mermaid might break)
		ll += [c*i for c in ascii_uppercase] # -> "AA", ... -> "AAA", ... -> 

	nnames = [n.slugname for n in nb.notes.values() if n.is_tagged('public')]

	nameMvar = {nnames[i]:ll[i] for i in range(len(nnames))} # "all-public": "AAAA"

	outstr = "#public\n\n```mermaid\n\tgraph TD;"

	for k, v in nameMvar.items():
		outstr += f"\n\t{v}[{k}]" # set variables 

	for fn,n in nb.notes.items():
		if n.is_tagged('public'):
			sv = nameMvar[n.slugname]
			for li in n.links:
				if (n := nb.get(li)):
					if n.slugname in nnames:
						if n.is_tagged('public'):
							rv = nameMvar[n.slugname]
							outstr += f"\n\t{sv} --> {rv}" # link from variables 

	outstr += "\n```" # close md code block
	print(outstr)
	# print(len(outstr)) # wonder when it breaks
	nb.generate_note('flat-link-graph', outstr, overwrite=True)




# nb = ObsidianNotebook()
# _collect_public_graph(nb)


def _create_link_graph(name: str, nb=None): # , tag: str=""
	"""
	:param name: note name
	"""
	# nb = ObsidianNotebook()

	ll = [ch for ch in ascii_uppercase] # link letters

	for i in range(2, 31): # support ~800 notes here (but mermaid might break)
		ll += [c*i for c in ascii_uppercase] # -> "AA", ... -> "AAA", ... -> 



	_nts = [n for n in nb.notes.values() if n.is_linked(name)]
	nnames = [n.slugname for n in _nts]

	nameMvar = {nnames[i]:ll[i] for i in range(len(nnames))} # "all-public": "AAAA"

	outstr = "#public\n\n```mermaid\n\tgraph TD;" # open md code block

	for k, v in nameMvar.items():
		outstr += f"\n\t{v}[{k}]" # set variables 

	for fn,n in nb.notes.items():
		if n.is_linked(name):
			sv = nameMvar[n.slugname]
			for li in n.links:
				if (n := nb.get(li)):
					if n.slugname in nnames:
						if n.is_linked(name):
							rv = nameMvar[n.slugname]
							outstr += f"\n\t{sv} --> {rv}" # link from variables 

	outstr += "\n```\n" # close md code block
	print(outstr)
	for n in _nts:
		outstr += f"\n[[{n.name}]]"
	# print(len(outstr)) # wonder when it breaks
	nb.generate_note(f'flat-link-graph-{name}', outstr, overwrite=True)


# nb = ObsidianNotebook()
# _fix_link_spacing(nb)
# _add_leading_newline(nb)
# _fix_tags_collect(nb)
# _parse_today_note(nb)
# _git_commit_notebook(nb)

# _create_link_graph('PYTHON', nb)


# for n in nb.notes.values():
# 	# print(n.name)
# 	if n.is_tagged('public'):
# 		print(n.name)
		
		# _create_link_graph(n.name, nb)



# remote commit:
# flat-link-graph-test3 -> <Response [201]>
# flat-link-graph-python functions -> <Response [201]>
# flat-link-graph-namespace -> <Response [201]>
# flat-link-graph-obsidian parser -> <Response [201]>
# flat-link-graph-all public -> <Response [201]>
# flat-link-graph-mermaid js -> <Response [201]>
# flat-link-graph-blog-settings -> <Response [201]>
# flat-link-graph-linked-page -> <Response [201]>
# flat-link-graph-command-line interface -> <Response [201]>
# flat-link-graph-flat-link-graph-PYTHON -> <Response [201]>
# flat-link-graph-PROGRAMMING -> <Response [201]>
# flat-link-graph-flat-link-graph-PROGRAMMING -> <Response [201]>
# flat-link-graph-INDEX -> <Response [201]>
# flat-link-graph-all tags -> <Response [201]>
# flat-link-graph -> <Response [201]>
# flat-link-graph-flat-link-graph -> <Response [201]>
# flat-link-graph-TEST -> <Response [201]>
# flat-link-graph-about -> <Response [201]>
# flat-link-graph-Program Management (James Smith) -> <Response [201]>
# flat-link-graph-test1 -> <Response [201]>
# flat-link-graph-python imports -> <Response [201]>
# flat-link-graph-organism-environment -> <Response [201]>
# flat-link-graph-PYTHON -> <Response [201]>


