import os
import subprocess
import json

import click

from obsidianotebook import ObsidianNotebook

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

	x = subprocess.run(['ln', '-s', os.path.join(path, f'{projname}.sublime-project'), ObsidianNotebook.NOTE_PATH], capture_output=True)
	click.echo(x)


@click.command()
def collect_subl_projects():
	""" -> notebook/sublime-project.md"""
	projs = []
	for fn in os.listdir(ObsidianNotebook.NOTE_PATH):
		if fn.endswith('.sublime-project'):
			projs.append(fn)

	obsidianmd = "\n\n".join([f'![[{p}]]' for p in projs])

	with open(os.path.join(ObsidianNotebook.NOTE_PATH, 'sublime-project.md'), 'w') as f:
		f.write(obsidianmd)



@click.command()
def commit_local_html():
	""" if note contains #public, -> blog """
	nb = ObsidianNotebook()
	nb.write_commits_to_local_html()


@click.command()
def commit_local_api():
	""" if note contains #public, -> blog """
	nb = ObsidianNotebook()
	nb.post_commits_to_blog_api()







obsidiancli.add_command(commit_local_html)
obsidiancli.add_command(commit_local_api)

obsidiancli.add_command(create_subl_proj)
obsidiancli.add_command(collect_subl_projects)

if __name__ == '__main__':
	obsidiancli()
