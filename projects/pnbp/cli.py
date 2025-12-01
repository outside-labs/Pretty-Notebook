import os 
import subprocess
import sys
import inspect

import click

from models import ObsidianNotebook, ObsidianNote
from wrappers import arrow_call

import commands.cleanup as clea
import commands.commit as comm
import commands.collect as coll
import commands.tasks as tasks
import commands.new as new



@click.group()
def cli():
	pass


""" 
"""
def _nb_get_help():
	""" show the cli.py --help message 
	"""
	# providing access to the full installed --help list ...
	# note how documentation strings don't
	# pass into the command when built below
	loc_p = os.path.dirname(__file__)
	cli_p = os.path.join(loc_p, 'cli.py')
	# no need to print as running the file runs the command
	subprocess.run(['python3', cli_p, '--help'])


@cli.command()
def nb_get_help():
	_nb_get_help()




""" obsidian-blog api connection:
"""
@cli.command()
def commit_local_html():
	""" if note contains #public, -> HTML_PATH/.html 
		(for local debugging when running remote server 
		and not a concurrent localhost instance...)
	"""
	# ^^ docstring == help message
	nb = ObsidianNotebook()
	nb.write_commits_to_local_html()


@cli.command()
def commit_remote_api():
	""" if note contains #public, -> 
		selective update POST to obsidian-blog api
		{API_BASE}/api/publishment
	"""
	nb = ObsidianNotebook()
	nb.post_commits_to_blog_api()



""" building click.commands out of 
	the (imported above) local /commands/ package
"""
def _create_command(func):
	""" effectively writes a 
		```@click.command()
			def outer_act_cmd():
				_outer_act_cmd()
		```	
	where I had issues passing live parameters 
	and chaining command calls in click otherwise.

	Has the nice feature of passing docstring when called this way too.
	"""
	func.__name__ = func.__name__.lstrip('_')
	cmd = cli.command()

	if 'note' in inspect.signature(func).parameters.keys():
		func = click.option('--note', type=str, help='the name of a note', required=True)(func)
	func = arrow_call(func)

	return cmd(func)

def create_command(func):
	""" actually instantiates the command
		-> required to also setattr() here for setup.py / 
		pip install to recognize dynamically created commands
		(specifically, setattr-ed after built)
	"""
	c = _create_command(func)
	setattr(sys.modules[__name__], func.__name__.lstrip('_'), c)


def create_all_commands():
	""" main function for building imported module commands 
		and tacking them onto the click.group(), & module local() name cli
	"""
	# print('debug...')

	# print(coll)
	# looking into imports from commands/collect.py
	for k,v in coll.__dict__.items(): 
		if inspect.isfunction(v) and k.startswith('_'):
			# print(k) # _func's name...
			create_command(v)

	# print(tasks)
	for k,v in tasks.__dict__.items():
		if inspect.isfunction(v) and k.startswith('_'):
			pass
	# -> actually, lets be picky:
	create_command(tasks._obsidian_task_settle)

	# print(comm)
	create_command(comm._git_commit_notebook)

	# print(clea)
	create_command(clea._fix_link_spacing)
	create_command(clea._remove_leading_newline)
	create_command(clea._add_leading_newline)
	create_command(clea._link_unlinked_mentions)
	create_command(clea._remove_nonexistant_links)




# -> required to call here (pre-main) for setup.py / 
# pip install to recognize dynamically created commands
create_all_commands()

if __name__ == '__main__':
	cli()
	





