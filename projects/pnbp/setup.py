from setuptools import setup

setup(
	name='obsidian-local',
	version='0.3.0',
	py_modules=['cli'],
	install_requires=[
		'Click',
	],
	entry_points='''
		[console_scripts]
		obsidian-collect-all=cli:obsidian_collect_all
		obsidian-delete-empty=cli:delete_all_empty
		obsidian-commit-local=cli:commit_local_html
		obsidian-commit-remote=cli:commit_remote_api
		obsidian-task-settle=cli:obsidian_task_settle
	''',
)
