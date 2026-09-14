import os 
import subprocess
import sys
import inspect

import click

from .commands import collect
from .commands import commit
from .commands import correct
from .commands import code
from .commands import graph
from .commands import pprint
from .commands import subl
from .commands import tasks

from .models import Notebook
from .helpers import arrow_call



@click.group()
def cli():
	pass



""" Pretty-Notebook/apps/web api connection commands:
"""
@cli.command()
def commit_html():
	""" if note contains #public, -> HTML_PATH/.html 
		(for local debugging when running remote server 
		and not a concurrent localhost instance...)
	"""
	# ^^ docstring == help message
	nb = Notebook()
	nb.write_commits_to_local_html()


@cli.command()
def commit_remote():
	""" if note contains #public, -> 
		selective update POST to .../apps/web api
		@ {API_BASE}/api/publishment
	"""
	nb = Notebook()
	nb.post_commits_to_web_api()


@cli.command()
def commit_local():
	""" commit -> localhost .../apps/web instance
	""" # a convenience command
	nb = Notebook()
	nb.API_BASE = 'http://127.0.0.1:8000'
	nb.post_commits_to_web_api()


@cli.command()
def commit_stage():
	""" *only* print commit- changes against nb.API_BASE
		to the terminal (staging view)
	"""
	nb = Notebook()
	nb.post_commits_to_web_api(stage_only=True)


@cli.command()
@click.option('--local', required=False, default=True, help="optionally, to localhost.")
def commit_settings(local):
	""" commit nb.NOTE_PATH/pnbp_settings.json -> the Pretty-Notebook/apps/web api .../web_settings.json 
	"""
	nb = Notebook()
	
	if local:
		nb.API_BASE = 'http://127.0.0.1:8000'
		
	nb.web_settings_post()


@cli.command()
def git_clone_pnbp_web():
	""" command to clone from github to ./pnbp_web/
	"""
	cmd = ["git", "clone", "--filter=blob:none", 
			"--sparse", "--depth", "1", "--single-branch", 
			"--branch", "main", "https://github.com/outside-labs/Pretty-Notebook.git",
			"pnbp-web"]

	cmd2 = ["git", "-C", "pnbp-web", "sparse-checkout", "set", "apps/web"]
		
	op = subprocess.run(cmd,capture_output=True)
		
	click.echo(op.stderr) # git outputs stdout to stderr

	wp = subprocess.run(cmd2, capture_output=True)
	
	click.echo(wp.stderr) 



""" building click.commands out of 
	the (imported above) local /commands/ package
"""
def _create_command(func):
	""" effectively writes a :

		```@click.command()
			def outer_act_cmd():
				_outer_act_cmd()
		```	

	where I had issues passing live parameters 
	and chaining command calls in click otherwise.
	
	As actively wrapping here (vs calling _outer_act_cmd()),
	has the nice feature of passing the _cmd's docstring to the --help info.

	:param func: 
	"""
	func.__name__ = func.__name__.lstrip('_')

	cmd = cli.command()

	if 'note' in inspect.signature(func).parameters.keys():
		# prove it : 
		func = click.option('-n', '--note', type=str, help='the name of a note', required=True)(func)

	func = arrow_call(func)

	return cmd(func)


def create_command(func):
	""" actually instantiating the command
		and specifically setattr-ing here after built is necessary

	:param func: 
	"""
	c = _create_command(func)
	setattr(sys.modules[__name__], func.__name__.lstrip('_'), c)


def create_commands(module, _all=False):
	""" 

	:param module: an commands/module.py imported above
	:param _all: _all=True will create a command from all leading underscore _func_name of module
	"""
	for k,v in module.__dict__.items():
		# print(k) # _func's name...
		if _all:
			if inspect.isfunction(v) 
			and k.startswith('_')
			and v.__module__ == module.__name__: # ignore if imported 
				create_command(v)
		else:
			# leave open for additional bool switches
			pass



def create_all_commands():
	""" main function for building imported module commands 
		and tacking them onto the click.group(), & module local() name cli

	"""
	create_commands(collect, _all=True)

	create_commands(commit, _all=True)

	create_commands(correct, _all=True)


	create_command(code._extract_code_blocks)
	create_command(code._extract_all_code_blocks)

	create_command(graph._create_link_graph)
	create_command(graph._create_tag_graph)
	create_command(graph._delete_all_graph_dash_name)

	create_command(pprint._nb_pprint)

	create_command(subl._subl_init)

	create_command(tasks._nb_task_settle)



	








# -> required to call here (pre-main) for pyproject.toml / 
# pip install to recognize dynamically created commands
create_all_commands()

if __name__ == '__main__':
	cli()
	





