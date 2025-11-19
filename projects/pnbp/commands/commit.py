import datetime
import subprocess

from models import ObsidianNotebook
from wrappers import pass_nb, arrow_call



@arrow_call
@pass_nb
def _git_commit_notebook(nb=None):
	""" commit to local git
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









