from setuptools import setup

setup(
	name='obsidian-local',
	version='0.2',
	py_modules=['obsidian'],
	install_requires=[
		'Click',
	],
	entry_points='''
		[console_scripts]
		obsidian-collect-all=obsidian:obsidian_collect_all
		obsidian-commit-local=obsidian:commit_local_html
		obsidian-commit-remote=obsidian:commit_remote_api
	''',
)
