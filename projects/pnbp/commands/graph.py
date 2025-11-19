from string import ascii_uppercase

from models import ObsidianNotebook
from wrappers import pass_nb



""" -> graph 
"""

@pass_nb
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


@pass_nb
def _create_link_graph(name: str, nb=None): # , tag: str=""
	"""
	:param name: note name
	"""
	ll = [ch for ch in ascii_uppercase] # ["A", "B", "C", ...]

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
	# print(outstr)
	# print(len(outstr)) # wonder when it breaks

	outstr += "\n--- \n"
	
	for n in _nts:
		# add the clickable links at the bottom of the note:
		outstr += f"\n[[{n.name}]]"
	
	nb.generate_note(f'flat-link-graph-{name}', outstr, overwrite=True)





if __name__ == '__main__':
	# nb = ObsidianNotebook()

	# _create_link_graph('PYTHON', nb)

	# for n in nb.notes.values():
	# 	# print(n.name)
	# 	if n.is_tagged('public'):
	# 		print(n.name)
			# _create_link_graph(n.name, nb)