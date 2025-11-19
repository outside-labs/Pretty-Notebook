from setuptools import setup

from click import Command

import cli


entry_points = '[console_scripts]'

for v in cli.__dict__.values():
	if isinstance(v, Command):
		if not (name := v.__dict__['name']) == 'cli':
			fxn_name = name.replace('-', '_')
			entry_points += f'\n{name}=cli:{fxn_name}'


setup(
	name='obsidian-local',
	version='0.4.0',
	py_modules=['cli'],
	install_requires=[
		'Click',
	],
	entry_points=entry_points,
)

# setup(
# 	name='obsidian-local',
# 	version='0.3.0',
# 	py_modules=['cli'],
# 	install_requires=[
# 		'Click',
# 	],
# 	entry_points='''
# 		[console_scripts]
# 		obsidian-collect-all=cli:obsidian_collect_all
# 		obsidian-delete-empty=cli:delete_all_empty
# 		obsidian-commit-local=cli:commit_local_html
# 		obsidian-commit-remote=cli:commit_remote_api
# 		obsidian-task-settle=cli:obsidian_task_settle
# 	''',
# )
