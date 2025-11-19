import re

from models import ObsidianNotebook
from wrappers import arrow_call, pass_nb
from helpers import str_strip_link


"""
"""
@pass_nb
def _fix_link_spacing(nb=None):
	""" [[ LINK ]] -> [[LINK]]
		useful for finiky apps like 1Writer
	"""
	p = re.compile(nb.OBS_INT_LNK)

	for n in nb.notes.values():
		if n.name == 'test1':
			n.md_out = p.sub(str_strip_link, n.md)
			n.save(nb)


@pass_nb
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

@pass_nb
def _remove_leading_newline(nb=None):
	""" -> nevermind / scrub
	"""
	for n in nb.notes.values():
		if n.name == 'test1':
			if n.md.startswith('\n'):
				n.md_out = n.md[1:]
				n.save(nb)


