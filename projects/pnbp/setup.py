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
	name='pysidian-local',
	version='0.4.0',
	py_modules=['cli'],
	install_requires=[
		'Click',
		'requests'
	],
	entry_points=entry_points,
)

# setup(
# 	name='pysidian-local',
# 	version='0.3.0',
# 	py_modules=['cli'],
# 	install_requires=[
# 		'Click',
# 	],
# 	entry_points='''
# 		[console_scripts]
# 		nb-collect-all=cli:nb_collect_all
# 		delete-all-empty=cli:delete_all_empty
# 		commit-local-html=cli:commit_local_html
# 		commit-remote-api=cli:commit_remote_api
# 		nb-task-settle=cli:nb_task_settle
# 	''',
# )
