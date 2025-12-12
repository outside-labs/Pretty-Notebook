# import requests -> weird shit maybe
import re 
import os

from models import PysidianNotebook, PysidianNote
from wrappers import arrow_call, pass_nb
import click

""" just a clean place to build 
	-> modules when 
"""


@click.option('--p', default=None)
def _test_path(p):
	if not p or p == '.':
		print(os.getcwd())

@pass_nb
def _symlink_shared(nb=None):
	""" """
	shared = [n for n in nb.notes.values() if n.is_linked('shared')]
	for n in shared:
		# if tag in usernames <- 
		u = 'caw5'

		# x = subprocess.run(['ln', '-s', os.path.join(nb.NOTE_PATH, 'shared', u, ), nb.NOTE_PATH], capture_output=True)
	pass





if __name__ == '__main__':
	pass
	# nb = PysidianNotebook()










