import os
import subprocess
import json

import click

from obsidianparse import NOTE_PATH

@click.group()
def obsidiancli():
	pass


@click.command()
@click.option('--path', default='.', help='File path to new project')
def create_subl_proj(path):
	""" Command to initiate local Sublime Text project && symlink to main Obsisian Notes directory"""
	defaultJson = {
		"folders":
		[
			{
				"path": ".",
				"folder_exclude_patterns": ["__pycache__"],
			}
		],
		"settings": {
			"python_virtualenv": "/Users/curtis/prog/.envs/venv/",
			"python_interpreter": "/Users/curtis/prog/.envs/venv/bin/python",
			"python_package_paths": [
			]
		}
	}

	if path == '.':
		path = os.getcwd()

	projname = path.split('/')[-1]

	with open(os.path.join(path, f'{projname}.sublime-project'), 'w') as f:
		f.write(json.dumps(defaultJson, indent=4))

	x = subprocess.run(['ln', '-s', os.path.join(path, f'{projname}.sublime-project'), NOTE_PATH], capture_output=True)
	click.echo(x)


obsidiancli.add_command(create_subl_proj)

if __name__ == '__main__':
	obsidiancli()
