import os
import subprocess
import json
import click

from obsidianotebook import ObsidianNotebook


@click.group()
def obsidiancli():
	pass



""" writing collections to specific notebook files:
"""
@click.command()
def collect_subl_projects():
	""" notebook/example.sublime_project -> sublime-project.md
	"""
	projs = []
	for fn in os.listdir(ObsidianNotebook.NOTE_PATH):
		if fn.endswith('.sublime-project'):
			projs.append(fn)

	obsidianmd = "\n\n".join([f'![[{p}]]' for p in projs])

	with open(os.path.join(ObsidianNotebook.NOTE_PATH, 'sublime-project.md'), 'w') as f:
		f.write(obsidianmd)


@click.command()
def collect_all_notes():
	""" -> notebook/all notes.md"""
	ns = []
	for fn in os.listdir(ObsidianNotebook.NOTE_PATH):
		if fn.endswith('.md'):
			ns.append(fn)

	obsidianmd = "".join([f"[[{x.split('.')[0]}]]\n" for x in ns])

	with open(os.path.join(ObsidianNotebook.NOTE_PATH, 'all notes.md'), 'w') as f:
		f.write(obsidianmd)


@click.command()
def collect_all_urls():
	""" -> notebook/all urls.md"""
	nb = ObsidianNotebook()

	all_urls = []
	for n in nb.notes.values():
		if n.name not in ('all urls'):
			for u in n.urls:
				all_urls.append(u)

	with open(os.path.join(nb.NOTE_PATH, 'all urls.md'), 'w') as f:
		f.write('\n'.join(str(l) for l in all_urls))


@click.command()
def collect():
	""" do all above collect- commands in succession """
	collect_subl_projects()
	collect_all_notes()
	collect_all_urls()




""" obsidian-blog api connection:
"""
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

obsidiancli.add_command(collect_subl_projects)
obsidiancli.add_command(collect_all_notes)
obsidiancli.add_command(collect_all_urls)
obsidiancli.add_command(collect)

if __name__ == '__main__':
	obsidiancli()
