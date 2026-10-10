import subprocess
import sys
import inspect
import json
from dataclasses import asdict
from functools import wraps
from pathlib import Path

import click
import requests

from .commands import collect
from .commands import commit
from .commands import correct
from .commands import code
from .commands import graph
from .commands import pprint
from .commands import subl
from .commands import tasks
from .commands.deploy import deploy

from .models import Notebook
from .helpers import arrow_call
from pretty_notebook._internal.storage import retain_edit_draft
from pretty_notebook._internal import identities as _identities
from .settings import initialize_notebook, resolve_notebook_path, SettingsError



@click.group()
@click.option("--notebook", "notebook_path", type=click.Path(path_type=Path, file_okay=False, exists=True), help="Open this notebook path.")
@click.option("--profile", "notebook_profile", help="Open a registered local notebook profile.")
@click.pass_context
def cli(context, notebook_path, notebook_profile):
	if notebook_path is not None and notebook_profile is not None:
		raise click.UsageError("Choose --notebook or --profile, not both.")
	selection = {"path": notebook_path} if notebook_path is not None else {"profile": notebook_profile} if notebook_profile is not None else {}
	context.obj = {"selection": selection, "notebook": None}


cli.add_command(deploy)


def _open_notebook():
	state = click.get_current_context().find_root().obj
	if state["notebook"] is None:
		try:
			state["notebook"] = Notebook(**state["selection"])
		except (SettingsError, ImportError, OSError) as error:
			raise click.ClickException(str(error)) from error
	return state["notebook"]


def _command_errors(func):
	@wraps(func)
	def invoke(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except (SettingsError, ValueError, OSError, RuntimeError, KeyError) as error:
			raise click.ClickException(str(error)) from error
	return invoke


def _json_echo(payload, notebook):
	"""Serialize allowlisted reports with bounded text and token redaction."""
	def clean(value):
		if isinstance(value, str):
			if notebook.API_TOKEN:
				value = value.replace(notebook.API_TOKEN, "<redacted>")
			return value[:4096]
		if isinstance(value, (list, tuple)):
			return [clean(item) for item in value]
		if isinstance(value, dict):
			return {key: clean(item) for key, item in value.items()}
		return value
	click.echo(json.dumps(clean(payload), ensure_ascii=False))


def _note_name(name):
	name = name.strip().replace("\\", "/")
	if not name or any(part in Notebook.SKIP_DIRECTORIES for part in Path(name).parts):
		raise ValueError("Choose a note name outside reserved state directories.")
	return name


def _selected_note(notebook, name):
	name = _note_name(name)
	key = name[:-3] if name.lower().endswith(".md") else name
	if key in notebook.notes:
		return notebook.notes[key]
	return notebook.open_note(name if name.lower().endswith(".md") else name + ".md")


def _source_text(content, source, *, default=""):
	if content is not None and source is not None:
		raise click.UsageError("Choose --content or --file, not both.")
	return source.read() if source is not None else content if content is not None else default


@cli.command("init")
@click.argument("path", type=click.Path(path_type=Path, file_okay=False), required=False)
@click.option("--migrate", is_flag=True, help="Migrate legacy settings and retain a private original backup.")
@click.option("--dry-run", is_flag=True, help="Validate and show the plan without creating or changing files.")
@click.option("--profile", help="Register a named local notebook profile.")
@_command_errors
def init_notebook(path, migrate, dry_run, profile):
	"""Explicitly initialize settings and identities; never initialize Git."""
	try:
		if path is None:
			selection = click.get_current_context().find_root().obj["selection"]
			path = resolve_notebook_path(**selection) if selection else Path(".")
		initialize_notebook(path, migrate=migrate, dry_run=True, profile=profile)
		identity_plan = _identities.initialize_identities(path, dry_run=True)
		plan = initialize_notebook(path, migrate=migrate, dry_run=dry_run, profile=profile)
		if not dry_run:
			identity_plan = _identities.initialize_identities(path)
	except (SettingsError, ImportError, OSError) as error:
		raise click.ClickException(str(error)) from error
	click.echo(json.dumps({**plan.to_dict(), "identities": identity_plan, "dry_run": dry_run}, indent=2))


@cli.group("identity")
def identity_commands():
	"""Inspect, reconcile, or deliberately fork local identities."""


@identity_commands.command("status")
@click.option("--json", "output_json", is_flag=True)
@click.option("--limit", type=click.IntRange(1, 200), default=200)
@_command_errors
def identity_status(output_json, limit):
	nb = _open_notebook()
	report = nb.identity_status(limit=limit)
	if output_json:
		_json_echo(report, nb)
	else:
		click.echo(json.dumps(report, ensure_ascii=False, indent=2))


@identity_commands.command("reconcile")
@click.argument("old_path")
@click.argument("new_path")
@click.option("--dry-run", is_flag=True)
@_command_errors
def reconcile_identity(old_path, new_path, dry_run):
	nb = _open_notebook()
	_json_echo(_identities.reconcile_identity(nb.NOTE_PATH, old_path, new_path, dry_run=dry_run), nb)


@identity_commands.command("fork")
@click.option("--dry-run", is_flag=True)
@_command_errors
def fork_identity(dry_run):
	nb = _open_notebook()
	_json_echo(nb.fork_identities(dry_run=dry_run), nb)


@cli.group("note")
def note_commands():
	"""Add, read, and edit notes with explicit saves."""


@note_commands.command("add")
@click.argument("name")
@click.option("--content", help="Initial Markdown text, including an explicit empty string.")
@click.option("--file", "source", type=click.File("r", encoding="utf-8"), help="Read Markdown from a file or '-' for stdin.")
@_command_errors
def note_add(name, content, source):
	nb = _open_notebook()
	created = nb.generate_note(_note_name(name), _source_text(content, source))
	click.echo(f"Created {created.source_path}")


@note_commands.command("show")
@click.argument("name")
@click.option("--html", "as_html", is_flag=True, help="Render through the existing notebook renderer.")
@_command_errors
def note_show(name, as_html):
	nb = _open_notebook()
	note = _selected_note(nb, name)
	click.echo(nb.convert_to_html(note) if as_html else note.current_md, nl=False)


@note_commands.command("edit")
@click.argument("name")
@click.option("--content", help="Replacement Markdown, including an explicit empty string.")
@click.option("--file", "source", type=click.File("r", encoding="utf-8"), help="Read replacement Markdown from a file or '-' for stdin.")
@_command_errors
def note_edit(name, content, source):
	nb = _open_notebook()
	note = _selected_note(nb, name)
	edited = _source_text(content, source, default=None)
	if content is None and source is None:
		edited = click.edit(note.current_md, extension=".md")
	if edited is None:
		click.echo("No changes saved.")
		return
	note.md_out = edited
	try:
		saved = note.save(nb)
	except (OSError, RuntimeError, _identities.IdentityError) as error:
		try:
			draft = retain_edit_draft(nb.NOTE_PATH, edited)
		except OSError:
			raise click.ClickException("Save failed and a recovery draft could not be written.") from error
		raise click.ClickException(f"Save failed: {error}. Draft retained at {draft}") from error
	click.echo(f"Saved {saved.source_path}")


@note_commands.command("rename")
@click.argument("source")
@click.argument("new_name")
@click.option("--dry-run", is_flag=True)
@_command_errors
def note_rename(source, new_name, dry_run):
	"""Rename within the current directory and repair matching wiki targets."""
	nb = _open_notebook()
	_json_echo(nb.rename_note(source, new_name, dry_run=dry_run), nb)


@note_commands.command("move")
@click.argument("source")
@click.argument("destination")
@click.option("--dry-run", is_flag=True)
@_command_errors
def note_move(source, destination, dry_run):
	"""Move to a notebook-relative path with recoverable backlink updates."""
	nb = _open_notebook()
	_json_echo(nb.move_note(source, destination, dry_run=dry_run), nb)


@note_commands.command("operations")
@click.option("--limit", type=click.IntRange(1, 200), default=200)
@_command_errors
def note_operations(limit):
	"""List local move journals and their recovery state."""
	nb = _open_notebook()
	_json_echo({"operations": nb.move_operations(limit=limit)}, nb)


@note_commands.command("recover")
@click.argument("operation_id")
@click.option("--action", type=click.Choice(["resume", "rollback"]), default="resume", show_default=True)
@click.option("--dry-run", is_flag=True)
@_command_errors
def note_recover(operation_id, action, dry_run):
	"""Resume or roll back a checked local move journal."""
	nb = _open_notebook()
	_json_echo(nb.recover_move(operation_id, action=action, dry_run=dry_run), nb)


@cli.command("search")
@click.argument("query")
@click.option("--field", type=click.Choice(["content", "title", "tag", "any"]), default="content", show_default=True, help="Choose the matching note field.")
@click.option("--tag", "tags", multiple=True, help="Require this exact tag; repeat to require every tag.")
@click.option("--regex", is_flag=True, help="Treat the query as a local regular expression.")
@click.option("--limit", type=click.IntRange(1, 200), default=50, show_default=True)
@click.option("--offset", type=click.IntRange(min=0), default=0)
@click.option("--json", "output_json", is_flag=True)
@_command_errors
def search_notes(query, field, tags, regex, limit, offset, output_json):
	"""Search local notes using literal, case-insensitive matching by default."""
	nb = _open_notebook()
	hits = nb.search(query, field=field, tags=tags, regex=regex, limit=limit, offset=offset)
	if output_json:
		_json_echo({"hits": [asdict(hit) for hit in hits], "limit": limit, "offset": offset}, nb)
	else:
		for hit in hits:
			click.echo(f"{hit.name}: {hit.excerpt}")


@cli.command("status")
@click.option("--json", "output_json", is_flag=True)
@click.option("--limit", type=click.IntRange(1, 200), default=50, show_default=True)
def notebook_status(output_json, limit):
	nb = _open_notebook()
	unsaved = nb.unsaved_notes
	report = {
		"path": nb.NOTE_PATH, "notes": len(nb), "note_nested": nb.settings.note_nested,
		"settings_file": nb.settings_file, "api_configured": bool(nb.API_BASE),
		"unsaved": [note.name for note in unsaved[:limit]], "unsaved_count": len(unsaved),
		"truncated": len(unsaved) > limit,
	}
	if output_json:
		_json_echo(report, nb)
	else:
		click.echo(f"{nb.NOTE_PATH}: {len(nb)} notes, {len(unsaved)} pending edits")



""" Pretty-Notebook/apps/web api connection commands:
"""
def _publish_notebook(notebook, **kwargs):
	"""Run publication with concise CLI reporting for transport failures."""
	try:
		return notebook.post_commits_to_web_api(**kwargs)
	except requests.RequestException as error:
		raise click.ClickException(f'Publication failed: {error}') from error


@cli.command()
def commit_html():
	""" if note contains #public, -> HTML_PATH/.html 
		(for local debugging when running remote server 
		and not a concurrent localhost instance...)
	"""
	# ^^ docstring == help message
	nb = _open_notebook()
	nb.write_commits_to_local_html()


@cli.command()
@click.option(
	'--prune',
	is_flag=True,
	help='Remove every remote page absent from this notebook after successful uploads.',
)
@click.option(
	'--refresh-images',
	is_flag=True,
	help='Resend referenced images even when their names already exist remotely.',
)
@click.option("--mode", type=click.Choice(["auto", "checked", "legacy"]), default="auto", show_default=True)
@click.option("--accept-remote", is_flag=True, help="Use reviewed current remote versions after a sync conflict.")
@_command_errors
def commit_remote(prune, refresh_images, mode, accept_remote):
	""" if note contains #public, -> 
		selective update POST to .../apps/web api
		@ {API_BASE}/api/publishment
	"""
	nb = _open_notebook()
	_publish_notebook(nb, prune=prune, refresh_images=refresh_images, mode=mode, accept_remote=accept_remote)


@cli.command()
@click.option(
	'--prune',
	is_flag=True,
	help='Remove every remote page absent from this notebook after successful uploads.',
)
@click.option(
	'--refresh-images',
	is_flag=True,
	help='Resend referenced images even when their names already exist remotely.',
)
@click.option("--mode", type=click.Choice(["auto", "checked", "legacy"]), default="auto", show_default=True)
@click.option("--accept-remote", is_flag=True, help="Use reviewed current remote versions after a sync conflict.")
@_command_errors
def commit_local(prune, refresh_images, mode, accept_remote):
	""" commit -> localhost .../apps/web instance
	""" # a convenience command
	nb = _open_notebook()
	nb.API_BASE = 'http://127.0.0.1:8000'
	_publish_notebook(nb, prune=prune, refresh_images=refresh_images, mode=mode, accept_remote=accept_remote)


@cli.command()
@click.option("--json", "output_json", is_flag=True)
@click.option("--limit", type=click.IntRange(1, 200), default=200, show_default=True)
@click.option("--mode", type=click.Choice(["auto", "checked", "legacy"]), default="auto", show_default=True)
@click.option("--prune", is_flag=True, help="Preview deletion of unlisted remote pages.")
@click.option("--refresh-images", is_flag=True)
@click.option("--accept-remote", is_flag=True, help="Preview using reviewed current remote versions after a sync conflict.")
@_command_errors
def commit_stage(output_json, limit, mode, prune, refresh_images, accept_remote):
	""" *only* print commit- changes against nb.API_BASE
		to the terminal (staging view)
	"""
	nb = _open_notebook()
	if output_json:
		try:
			_json_echo(nb.publication_plan(limit=limit, mode=mode, prune=prune, refresh_images=refresh_images, accept_remote=accept_remote), nb)
		except requests.RequestException as error:
			raise click.ClickException("Could not read the remote publication inventory.") from error
	else:
		_publish_notebook(nb, stage_only=True, mode=mode, prune=prune, refresh_images=refresh_images, accept_remote=accept_remote)


@cli.command()
@click.option('--local', is_flag=True, default=False, help="post to localhost instead of the configured API_BASE")
def commit_settings(local):
	"""Send configured layout settings to the web API.
	"""
	nb = _open_notebook()
	
	if local:
		nb.API_BASE = 'http://127.0.0.1:8000'
		
	nb.web_settings_post()


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--local", is_flag=True, help="Upload to localhost instead of the configured API_BASE.")
@_command_errors
def favicon(path, local):
	"""Replace the site's PNG favicon using site-owner credentials."""
	nb = _open_notebook()
	if local:
		nb.API_BASE = "http://127.0.0.1:8000"
	try:
		response = nb.post_favicon(path)
	except requests.RequestException as error:
		raise click.ClickException("Could not update the site favicon.") from error
	click.echo(response.json()["url"])


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
	original = func
	parameters = inspect.signature(func).parameters
	@wraps(original)
	def invoke(*args, **kwargs):
		if "nb" in parameters and kwargs.get("nb") is None:
			kwargs["nb"] = _open_notebook()
		return original(*args, **kwargs)
	invoke.__name__ = original.__name__.lstrip('_')
	func = _command_errors(invoke)
	cmd = cli.command(name=original.__name__.lstrip('_').replace('_', '-'))

	if 'note' in inspect.signature(func).parameters.keys():
		# prove it : 
		func = click.option(
			'--fuzzy',
			is_flag=True,
			help='explicitly accept the closest matching note name',
		)(func)
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
			if (inspect.isfunction(v) 
			and k.startswith('_')
			and v.__module__ == module.__name__): # ignore if imported 
				create_command(v)
		else:
			# leave open for additional bool switches
			pass



BUILTIN_COMMANDS = (
	collect._collect_all_stats, collect._collect_all_notes, collect._collect_all_urls,
	collect._collect_all_public, collect._collect_terms, collect._collect_all_unlinked,
	collect._collect_all_empty, collect._collect_all_unheadered, collect._collect_all_moc,
	collect._collect_all_tags, collect._collect_nonexistant_links, collect._collect_all,
	collect._collect_code_blocked, collect._collect_tasks_note, collect._collect_public_graph,
	collect._collect_all_graphs, collect._collect_subl_projs,
	commit._git_commit_notebook, commit._collect_git_diff, commit._init_git_ignore,
	correct._strip_links_spacing, correct._expand_links_spacing, correct._prepend_leading_newline,
	correct._remove_leading_newline, correct._remove_leading_and_trailing_newlines,
	correct._link_unlinked_mentions, correct._collect_unlinked_mentions,
	correct._remove_nonexistant_links, correct._delete_all_pnbp, correct._delete_all_empty,
	correct._touch_all_public,
	code._extract_code_blocks, code._extract_all_code_blocks,
	graph._create_link_graph, graph._create_tag_graph, graph._delete_all_graph_dash_name,
	pprint._pprint, subl._subl_init, tasks._task_settle,
)


def create_all_commands():
	"""Register the explicit supported command list without scanning private helpers."""
	for func in BUILTIN_COMMANDS:
		create_command(func)


# -> required to call here (pre-main) for pyproject.toml / 
# pip install to recognize dynamically created commands
create_all_commands()

if __name__ == '__main__':
	cli()
	
