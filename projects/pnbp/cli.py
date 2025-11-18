import sys
import inspect

import click

from models import ObsidianNotebook

import commands as cmds
import tasks
# from tasks import _obsidian_task_settle
from new import _nb_get_help


@click.group()
def cli():
	pass

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



""" 
"""
def _create_command(func):
	""" effectively writes a 
		```@click.command()
			def outer_act_cmd():
				_outer_act_cmd()
		```	
	where I had issues passing live parameters 
	and chaining command calls in click otherwise
	"""
	func.__name__ = func.__name__.lstrip('_')
	cmd = cli.command()
	return cmd(func)



def create_all_commands():
	""" main function for building imported module commands 
		and tacking them onto the click.group()
	"""
	print('debug...')

	# print(cmds)
	# looking into imports from commands.py
	for k,v in cmds.__dict__.items(): 
		if inspect.isfunction(v) and k.startswith('_'):
			# print(k) # _func's name...
			c = _create_command(v)
			# -> required to also setattr() here for setup.py / 
			# pip install to recognize dynamically created commands
			setattr(sys.modules[__name__], v.__name__.lstrip('_'), c)


	# print(tasks)
	for k,v in tasks.__dict__.items():
		if inspect.isfunction(v) and k.startswith('_'):
			pass
			# print(k)
			# c = _create_command(v)
			# setattr(sys.modules[__name__].lstrip('_'), c)

	# -> actually, lets be picky:
	c = _create_command(tasks._obsidian_task_settle)

	setattr(sys.modules[__name__], v.__name__.lstrip('_'), c)





# -> required to call here (pre-main) for setup.py / 
# pip install to recognize dynamically created commands
create_all_commands()

if __name__ == '__main__':
	cli()
	





