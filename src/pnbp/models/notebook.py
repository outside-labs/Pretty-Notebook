import os
import re
import json
import getpass
import difflib
import mimetypes
import random

from collections.abc import Iterator, Iterable
from pathlib import Path

import markdown as md
import requests

from .note import Note

from .components import Link, Tag, Url, CodeBlock

from pnbp.helpers import _convert_datetime



class Notebook:
	""" 
	"""
	SKIP_DIRECTORIES = {".git", ".obsidian", "__pycache__"}
	PUBLICATION_SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
	PUBLICATION_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
	REQUEST_TIMEOUT = (5, 30)

	def __init__(self):

		self.NOTE_PATH = os.environ.get('NOTE_PATH')
		self.IMG_PATH = os.environ.get('IMG_PATH')
		self.HTML_PATH = os.environ.get('HTML_PATH')

		if not self.NOTE_PATH:
			raise ImportError("required to set NOTE_PATH environment variable to init a Notebook instance!")

		self.settings_file = os.path.join(self.NOTE_PATH, 'pnbp_settings.json')

		if not os.path.exists(self.settings_file):
			if not os.environ.get('PNBP_SETTINGS') == 'off':
				print("an NOTE_PATH/pnbp_settings.json file not found.")
				gen_empt = input("generate it from a template? (y/n): ")
				if gen_empt.lower() == 'y':

					empty_settings = {
							"IMG_PATH": "", "HTML_PATH": "", "VENV_PATH": "", 
							"API_BASE": "http://127.0.0.1:8000",
							"API_TOKEN": "", "PUB_LNK_ONLY": False,
							"NAV_BRAND": "", "NAV_PAGES": {},
							"FOOTER": "", "darkmode": False,
							"hljs_light": "default", "hljs_dark": "xt256",
							"merm_light": "default", "merm_dark": "dark",
							"COMMIT_TAG": '#public', "EXCLUDE_TAG": '#private',
							"HIDE_COMMIT_TAG": False, 
							}
					
					with open(self.settings_file, 'w') as sf:
						json.dump(empty_settings, sf, indent=4)

					print(f"generated (most empty/default) from template to\n{self.NOTE_PATH}/pnbp_settings.json: \n{json.dumps(empty_settings, indent=4)}")
				else:
					print("NOTE_PATH/pnbp_settings.json is only soft required, please see https://github.com/outside-labs/Pretty-Notebook/blob/main/docs/pnbp_settings.json for example.")
					print("Suppress warning+template offer message in the future by setting NOTE_CONFIG environment variable to 'off'.")
					self.settings_file = False
			else:
				self.settings_file = False

		if self.settings_file:
			with open(self.settings_file) as sf:
				self.config = json.load(sf)
		else:
			self.config = {} # lazy handle existance for conf_file=False
		
		if not os.environ.get('NOTE_NESTED') in ('flat', 'single', 'recurs', 'all'):
			self.config['NOTE_NESTED'] = 'flat'
		else:
			self.config['NOTE_NESTED'] = os.environ.get('NOTE_NESTED')

		if not self.IMG_PATH:
			# prefering set environment variable
			self.IMG_PATH = self.config.get('IMG_PATH')

		if not self.HTML_PATH:
			# but available to set in self.config 
			self.HTML_PATH = self.config.get('HTML_PATH')

		self.API_BASE = self.config.get('API_BASE')
		self.API_TOKEN = self.config.get('API_TOKEN')
		self.PUB_LNK_ONLY = self.config.get('PUB_LNK_ONLY')

		self.VENV_PATH = self.config.get('VENV_PATH') # see commands/subl.py

		if (tag := self.config.get("COMMIT_TAG")):
			# overwrite class default:
			self.COMMIT_TAG = tag
		else:
			self.COMMIT_TAG = '#public'

		if (tag := self.config.get("EXCLUDE_TAG")):
			# ... 
			self.EXCLUDE_TAG = tag
		else:
			self.EXCLUDE_TAG = '#private'

		self.notes = {}
		self.open_md()

	def __len__(self):
		""" the number of notes """
		return len(self.notes.keys())

	@property
	def unsaved_notes(self)->tuple:
		""" return a tuple of all notes that have unsaved changes
		"""
		return tuple(note for note in self.notes.values() if note.is_unsaved)
	
	@property
	def has_unsaved_notes(self)->bool:
		""" return True if any note has unsaved changes, False otherwise
		"""
		return bool(self.unsaved_notes)
	
	def save_all_notes(self):
		""" save all notes that have unsaved changes
		"""
		if not self.has_unsaved_notes:
			print("no unsaved notes to save.")
			return []

		names = [note.name for note in self.unsaved_notes]

		for name in names:
			self.notes[name].save(self)

		return names

	def discard_all_changes(self):
		""" discard all changes to all notes that have unsaved changes
		"""
		if not self.has_unsaved_notes:
			print("no unsaved notes with content to discard.")
			return []

		names = [note.name for note in self.unsaved_notes]

		for name in names:
			self.notes[name].discard_changes()

		return names

	def _iter_note_files(self) -> Iterator[Path]:
		""" an internal method to safely iterate the "flat" self.NOTE_PATH/
			directory, a "single", or full "recur"(sive) path, 
			including (if advised, not by default) "all" (i.e. incl. hidden)
		"""
		root = Path(self.NOTE_PATH).expanduser().resolve()
		mode = self.config.get("NOTE_NESTED", "flat")
		include_hidden = mode == "all"

		if mode not in {"flat", "single", "recurs", "all"}:
			raise ValueError(f"Unknown NOTE_NESTED mode: {mode!r}")

		def markdown_files(directory: Path) -> list[Path]:
			return sorted(
				path
				for path in directory.iterdir()
				if path.is_file() and path.suffix.lower() == ".md"
			)

		def child_directories(directory: Path) -> list[Path]:
			return sorted(
				path
				for path in directory.iterdir()
				if (
					path.is_dir()
					and not path.is_symlink()
					and path.name not in self.SKIP_DIRECTORIES
					and (include_hidden or not path.name.startswith("."))
				)
			)

		yield from markdown_files(root)

		if mode == "flat":
			return

		first_level = child_directories(root)

		if mode == "single":
			for directory in first_level:
				yield from markdown_files(directory)
			return

		pending = list(reversed(first_level))

		while pending:
			directory = pending.pop()
			yield from markdown_files(directory)
			pending.extend(reversed(child_directories(directory)))

	def open_note(self, f, *, notes=None):
		""" 
		:param str f: the .md note to open
		:param dict notes: optional destination mapping used during atomic reloads
		"""
		root = Path(self.NOTE_PATH).expanduser().resolve()
		raw_path = f"{f.name}.md" if isinstance(f, Note) else f
		path = Path(raw_path).expanduser()

		if not path.is_absolute():
			path = root / path

		path = path.resolve()

		try:
			relative_path = path.relative_to(root)
		except ValueError as e:
			raise ValueError("Note path escapes NOTE_PATH") from e

		if path.suffix.lower() != ".md":
			raise ValueError(f"Not a Markdown note: {path}")

		text = path.read_text(encoding="utf-8")
		file_stat = path.stat()
		note_name = relative_path.with_suffix("").as_posix()

		n = Note(
			name=note_name,
			md=text,
			links=[m.strip() for m in re.findall(Link.MDS_INT_LNK, text)],
			tags=Tag.collect_tags(text),
			urls=Url.collect_urls(text),
			codeblocks=re.findall(CodeBlock.MD_CODE, text),
			mtime=_convert_datetime(file_stat.st_mtime, as_mtime=True),
			)
		n.source_path = relative_path.as_posix()
		n._source_exists = True
		n._source_signature = Note._stat_signature(file_stat)

		target = self.notes if notes is None else notes
		target[note_name] = n

		return n

	def open_md(self, *, discard_unsaved=False)->dict:
		""" open all .md files from the self.NOTE_PATH path
			into memory as e.g. {"my note name": Note}
			-> available at nb.notes

		:param bool discard_unsaved: explicitly allow pending edits to be discarded
		"""
		if self.has_unsaved_notes and not discard_unsaved:
			names = ", ".join(note.name for note in self.unsaved_notes)
			raise RuntimeError(
				f"Cannot reload notebook with unsaved changes: {names}. "
				"Save them or call open_md(discard_unsaved=True)."
			)

		root = Path(self.NOTE_PATH).expanduser().resolve()
		loaded_notes = {}

		for path in self._iter_note_files():
			relative_path = path.relative_to(root)
			self.open_note(relative_path.as_posix(), notes=loaded_notes)

		self.notes = dict(sorted(loaded_notes.items()))

		return self.notes

	def open(self, *, discard_unsaved=False):
		""" """
		self.open_md(discard_unsaved=discard_unsaved)

	def _require_clean_notes(self, operation):
		"""Refuse operations that cannot safely consume staged note content."""
		if self.has_unsaved_notes:
			names = ", ".join(note.name for note in self.unsaved_notes)
			raise RuntimeError(
				f"Cannot {operation} with unsaved changes: {names}. "
				"Save or discard them explicitly first."
			)

	def generate_note(self, name, md_out, overwrite=False, pnbp=False):
		""" 
		:param name: the name of the note (without ".md") to generate
		:param md_out: the desired string to save to the notebook at "name.md"
		:param overwrite: if overwrite=True, allow existing file to be re-written
		:param pnbp: if pnbp=True, tagging #pnbp to track and ignore
		"""
		if not isinstance(md_out, str):
			raise TypeError(f"md_out must be a str, not {type(md_out)}")

		name = str(name).strip()
		if name.lower().endswith(".md"):
			name = name[:-3]
		if not name:
			raise ValueError("A note name is required.")

		root = Path(self.NOTE_PATH).expanduser().resolve()
		destination = (root / f"{name}.md").resolve()

		try:
			relative_path = destination.relative_to(root)
		except ValueError as e:
			raise ValueError("Note path escapes NOTE_PATH") from e

		existing_paths = []
		if destination.parent.exists():
			existing_paths = [
				path
				for path in destination.parent.iterdir()
				if path.name.casefold() == destination.name.casefold()
			]

		if existing_paths and not overwrite:
			raise FileExistsError(f"Cannot generate a new note at {relative_path}.")

		if len(existing_paths) > 1:
			raise FileExistsError(
				f"Cannot choose between case-variant note paths for {relative_path}."
			)

		if existing_paths:
			existing_path = existing_paths[0]
			if existing_path.is_symlink():
				raise ValueError(f"Refusing to overwrite a note symlink: {existing_path}")
			existing_path = existing_path.resolve()
			try:
				existing_relative = existing_path.relative_to(root)
			except ValueError as e:
				raise ValueError("Note path escapes NOTE_PATH") from e
			n = self.open_note(existing_relative.as_posix())
		else:
			note_name = relative_path.with_suffix("").as_posix()
			n = Note(
				name=note_name,
				md='',
				links=[],
				tags=[],
				urls=[],
				codeblocks=[],
				mtime='',
			)
			n.source_path = relative_path.as_posix()

		n.md_out = md_out

		if pnbp is True:
			n.md_out += '\n\n--- \n\n#pnbp'

		return n.save(self)

	def get(self, name)->Note:
		""" access the notes dict directly 

		:param name: name of the note
		:returns: Note instance or None
		"""
		if isinstance(name, Note):
			n = name
			return self.notes.get(n.name)

		name = str(name)

		name = name.replace('.md', '').replace('.html', '').replace('\\', '')

		if (note := self.notes.get(name)):
			return note

		for n in self.notes.values():
			if n.slugname == name:
				return n

		try: 
			name_in = name
			name = difflib.get_close_matches(name, [n for n in self.notes.keys()])[0]
			print(f"^^ {name} (by close match) ")
			return self.get(name)

		except IndexError:
			print(f"note: `{name_in}` does not exist in the notebook!")

		return None

	def get_random_note(self):
		"""
		:returns: a random note from the notebook
		"""
		return self.notes[random.choice([k for k in self.notes.keys()])]


	def get_tagged(self, tag)->list:
		""" 
		:param tag: the #tag in question
		:returns: a list of Note instances containing tag
		"""
		t_notes = []
		for n in self.notes.values():
			if n.is_tagged(tag):
				t_notes.append(n)

		return t_notes

	def is_publishable(self, note)->bool:
		"""Return whether a note is explicitly public and not excluded."""
		return (
			note.is_tagged(self.COMMIT_TAG)
			and not note.is_tagged(self.EXCLUDE_TAG)
		)

	def _publication_image(self, reference):
		"""Resolve one flat image reference without allowing IMG_PATH escapes."""
		reference = reference.strip()

		if not reference or not self.IMG_PATH:
			raise ValueError(f"Invalid publication image path: {reference!r}")

		root = Path(self.IMG_PATH).expanduser().resolve()
		supplied = Path(reference).expanduser()

		if supplied.is_absolute() or supplied.name != reference:
			raise ValueError(f"Invalid publication image path: {reference!r}")

		target = (root / supplied).resolve()

		try:
			target.relative_to(root)
		except ValueError as error:
			raise ValueError(
				f"Publication image path escapes IMG_PATH: {reference!r}"
			) from error

		if target.suffix.lower() not in self.PUBLICATION_IMAGE_EXTENSIONS:
			raise ValueError(f"Unsupported publication image path: {reference!r}")

		if not target.is_file():
			raise FileNotFoundError(f"Publication image not found: {reference!r}")

		content_type = mimetypes.guess_type(target.name)[0]
		if content_type is None:
			content_type = "application/octet-stream"

		return target, content_type

	def _publication_preflight(self, *, include_images=False):
		"""Validate all publication inputs before writes or HTTP requests."""
		notes = tuple(note for note in self.notes.values() if self.is_publishable(note))
		slugs = {}

		for note in notes:
			slug = note.slugname

			if not slug:
				raise ValueError(f"Note {note.name!r} has an empty publication slug.")

			if not self.PUBLICATION_SLUG_PATTERN.fullmatch(slug):
				raise ValueError(
					f"Note {note.name!r} has an invalid publication slug: {slug!r}."
				)

			if previous := slugs.get(slug):
				raise ValueError(
					f"Notes {previous.name!r} and {note.name!r} share "
					f"duplicate publication slug {slug!r}."
				)

			slugs[slug] = note

		images = {}
		if include_images:
			for note in notes:
				for reference in re.findall(Link.MDS_IMG_LNK, note.md):
					reference = reference.strip()
					if reference not in images:
						images[reference] = self._publication_image(reference)

		return notes, images

	def get_linked(self, link)->list:
		"""
		:param link: the [[link]] in question
		:returns: a list of Note instances containing link
		"""
		l_notes = []
		for n in self.notes.values():
			if n.is_linked(link):
				l_notes.append(n)

		return l_notes

	@property
	def tags(self)->list:
		""" a list of all found #tags in the Notebook instance
		"""
		ts = []
		for n in self.notes.values():
			for t in n.tags:
				ts.append(t)

		return sorted(list(set(ts)))

	@property
	def links(self):
		""" a list of all .md Notes in the Notebook
		"""
		return sorted([fn for fn in self.notes.keys()])

	@property
	def urls(self)->list:
		""" a list of all Urls found in the Notebook
		"""
		us = []
		for n in self.notes.values():
			for u in n.urls:
				us.append(u)

		return sorted(us)

	def find(self, regex):
		""" a user convenience method to effectively grep notebook
		"""
		print(f'regex: {regex}')

		notes = []
		for fn, n in self.notes.items():
			p = re.compile(regex)
			if (m := p.search(n.md)):
				print(f'\t -> {fn}')
				print(m)
				print(f'found: {m}')
				notes.append(n)

		print(f'{[n.name for n in notes]}')

		return notes

	def find_and_replace(self, regex, replace, notes=[]):
		""" 

		:param regex: 
		:param replace: 
		:param notes: 
		"""
		msg = "Notebook.find_and_replace requires a list of Notes to make replacements."
		if not notes:
			raise ValueError(f"{msg}\nnb.find_and_replace(regex='foo', replace='', notes=nb.find('foo'))")
		elif not isinstance(notes, list):
			raise ValueError(f"{msg}\nnb.find_and_replace(..., notes=[nb.get('bar'))]")
		else:
			# handle for string name -> note gets
			pass

		if (ntc := self.find(regex)):
			ntc = [n for n in ntc if n in notes]
			print('"replace" <- "regex" : n.name')
			for n in ntc:
				n.md_out = re.sub(fr'{regex}', replace, n.md)
				n.save(self)
				print(f'"{replace}" <- "{regex}" : {n.name}')

	""" preparing for api commits : 
	"""
	@classmethod
	def replace_strikethrough(cls, note):
		""" a regex replace mtd 
		
		:param note: an Note instance
		"""
		p = re.compile(r'(~~)(.*)(~~)')
		strike_repl = lambda m: f'<s>{m.group(2)}</s>'

		if note.md_out is None:
			note.md_out = note.md
		
		note.md_out = p.sub(strike_repl, note.md_out)

		return note

	@classmethod
	def replace_eqhighlight(cls, note):
		""" a regex replace mtd 
		
		:param note: an Note instance
		"""
		p = re.compile(r'(==)(.*)(==)')
		eqhl_repl = lambda m: f'<mark>{m.group(2)}</mark>'

		if note.md_out is None:
			note.md_out = note.md
		
		note.md_out = p.sub(eqhl_repl, note.md_out)

		return note

	def remove_nonpub_links(self, note):
		""" if #public note with [[not public]] links,
			remove them from html generation if nb.PUB_LNK_ONLY

		:param note: an Note instance
		""" 
		remv = []
		for link in note.links:
			target = self.notes.get(link.note)
			if target is None or not self.is_publishable(target):
				remv.append(str(link))

		note.remove_links(remv)
		# -> md_out is set initially here. 

		return note

	def hide_commit_tag(self, note):
		""" removes the #public tag (aka COMMIT_TAG) from
			the .md before export (if PUB_LNK_ONLY)

		:param note: an Note instance
		"""
		if note.md_out is None:
			# -> if md_out is not set yet...
			note.md_out = note.md

		note.md_out = note.md_out.replace(self.COMMIT_TAG, '')

		return note

	def convert_to_html(self, note):
		""" apply all the regex method changes to 
			a single note

			md->html str repl methods
			coupled with mtds from helpers.py

		:param note: an Note instance
		::
		"""
		previous_md_out = note.md_out
		
		try:
			note.md_out = note.current_md
	
			if self.PUB_LNK_ONLY:
				note = self.remove_nonpub_links(note)

			if self.config.get('HIDE_COMMIT_TAG') == True:
				note = self.hide_commit_tag(note)

			nout = Link.replace_imglinks(note)
			nout = Link.replace_intlinks(nout)
			nout = Tag.replace_smdtags(nout)
			nout = CodeBlock.replace_mermaid(nout)
			nout = Url.replace_nakedhref(nout)

			nout = Link.add_header_ids(nout)

			nout.md_out = md.markdown(nout.md_out, extensions=['fenced_code', 'nl2br', 'markdown.extensions.tables', 'attr_list', 'footnotes'], use_pygments=True)

			nout = CodeBlock.fix_blocked_comments(nout)
			nout = Notebook.replace_strikethrough(nout)
			nout = Notebook.replace_eqhighlight(nout)
			nout = Url.adjust_externallinks(nout)

			return nout.md_out
	
		finally:
			note.md_out = previous_md_out	
		

	def write_commits_to_local_html(self):
		""" a local debugging mtd 
			-> self.HTML_PATH/.html ... 
		"""
		self._require_clean_notes("publish local HTML")
		self.open_md()
		notes, _ = self._publication_preflight()

		print(f'\nlocal commit: {self.HTML_PATH}')
		for n in notes:
			html = self.convert_to_html(note=n)
			target = Path(self.HTML_PATH) / f"{n.slugname}.html"
			with target.open('w', encoding='utf-8') as output_file:
				output_file.write(html)

			print(f'\t{n.name} ---> {self.HTML_PATH}')

	""" pnbp-web api connection methods:
	"""
	def get_headers(self):
		""" the request headers """
		return {'accept': 'application/json', 'authorization': f'Bearer {self.API_TOKEN}'}

	def _api_request(self, method, path, **kwargs):
		"""Send one checked API request with a finite connection/read timeout."""
		kwargs.setdefault('timeout', self.REQUEST_TIMEOUT)
		response = method(f'{self.API_BASE}{path}', **kwargs)
		response.raise_for_status()
		return response

	def refresh_token(self):
		""" request method to replace the authenticated user's bearer token 
		"""
		u = input('Username: ')
		p = getpass.getpass()
		h = self.get_headers()
		h.update({'Content-Type': 'application/x-www-form-urlencoded'})
		r = requests.post(f'{self.API_BASE}/api/token', data={'username': u, 'password': p}, headers=h)
		print(r)
		print(r.text)
		print(r.json())
		if r.status_code == 200:
			self.API_TOKEN = r.json()['access_token']

			with open(self.settings_file) as sf:
				config = json.load(sf)
				config.update({"API_TOKEN": self.API_TOKEN})

			with open(self.settings_file, 'w') as sf:
				json.dump(config, sf, indent=4)

	def get_authed_user(self):
		""" request method to get the authenticated user's username 
		"""
		h = self.get_headers()
		r = requests.get(f'{self.API_BASE}/api/users/me', headers=h)
		print(r)
		print(r.json())
		return r

	def get_api_home(self):
		""" request method to /api/ (testing auth) 
		"""
		h = self.get_headers()
		r = requests.get(f'{self.API_BASE}/api', headers=h)
		print(r.text)
		print(r.json())
		return r

	def get_pub_commits(self)->dict:
		""" (internal use)
			request method for a remote filepath check 
			for the purpose of making smarter POST updates
			against current publishments.
		"""
		h = self.get_headers()
		r = self._api_request(requests.get, '/api/publishments', headers=h)
		pub_data = r.json()

		nameMtime = {}
		for pub in pub_data:
			pub['mod_date'] = _convert_datetime(pub['mod_date'])
			nameMtime.update({pub['pub_name']: pub['mod_date']})

		return nameMtime

	def get_img_commits(self)->dict:
		""" (internal use)
			request method for a remote filepath check
			for the purpose of making smarter POST updates
			against current imgs.
		"""
		h = self.get_headers()
		r = self._api_request(requests.get, '/api/images', headers=h)
		img_data = r.json()

		nameMtime = {}
		for img in img_data:
			img['mod_date'] = _convert_datetime(img['mod_date'])
			nameMtime.update({img['img_name']: img['mod_date']})

		return nameMtime

	def delete_unlisted_post(self, rname):
		""" (internal use)
			request method to remove the HTML at filepath
			of Note(s) made non- #public
		"""
		h = self.get_headers()
		r = self._api_request(
			requests.delete,
			f'/api/publishment/{rname}',
			headers=h,
		)
		print(f'(removed) {r.json()["pub_name"]} -> {r}')
		return r

	def post_commits_to_web_api(
		self,
		stage_only=False,
		*,
		prune=False,
		refresh_images=False,
	):
		""" the main POST method

		:param stage_only: if stage_only, print #public and don't commit
		:param prune: remove every remote page absent from this notebook
		:param refresh_images: resend referenced images even when names exist remotely
		"""
		self._require_clean_notes("preview or publish remote commits")
		self.open_md()
		notes, publication_images = self._publication_preflight(include_images=True)
		h = self.get_headers()

		pub_pub_data = self.get_pub_commits()
		pub_pub_names = tuple(pub_pub_data)

		pub_img_data = self.get_img_commits()
		pub_img_names = set(pub_img_data)

		print(f'\ncommits: (to {self.API_BASE})')
		post_names = []
		uploaded_images = set()
		for n in notes:
			to_post = False
			fname = n.slugname + '.html'

			post_names.append(fname)
			if fname in pub_pub_names:
				if pub_pub_data[fname] < n.mtime: # change has occurred
					to_post = True
			else: # it's newly #public
				to_post = True

			if stage_only:
				continue

			if to_post:
				html = self.convert_to_html(note=n)
				r = self._api_request(
					requests.post,
					'/api/publishment',
					json={"name": n.slugname, "content": html},
					headers=h,
				)
				print(f'\t{n.name} -> {r}')

			for img in re.findall(Link.MDS_IMG_LNK, n.md):
				img = img.strip()
				if img in uploaded_images:
					continue

				if refresh_images or img not in pub_img_names:
					path, content_type = publication_images[img]
					with path.open('rb') as image_file:
						r = self._api_request(
							requests.post,
							'/api/image',
							files={"file": (path.name, image_file, content_type)},
							headers=h,
						)

					print(f'\t\t{img} -> {r}')
					uploaded_images.add(img)
				else:
					print(f'\t\t{img} -> EXISTS!')

		removals = [name for name in pub_pub_names if name not in post_names]

		if stage_only:
			print("\nnew pub: ")
			for p in [n for n in post_names if not n in pub_pub_names]:
				print(f'-> {p}')

			print("\nto remove:")
			for p in removals:
				print(f'-> {p}')

			print("\nall current pubs: ")
			for p in post_names:
				print(f'-> {p}')

			print("\n\n** stage_only=True, no changes made... ***")
		elif prune:
			if removals:
				print(f'\npruning {len(removals)} remote page(s):')
			for p in removals:
				self.delete_unlisted_post(p)
		elif removals:
			print("\nremote pages not pruned; use prune=True after reviewing stage output:")
			for p in removals:
				print(f'-> {p}')

	def web_settings_post(self):
		""" request method to POST layout update 
			from self.NOTE_PATH/pnbp_settings.json 
			(see https://github.com/outside-labs/Pretty-Notebook/blob/main/apps/web-settings.json
			for examples)
		"""
		h = self.get_headers()

		_config = self.config.copy()

		bs_keys = tuple([
						"NAV_BRAND", "NAV_PAGES", 
						"FOOTER", "TITLE",
						"darkmode", 
						"hljs_light", "hljs_dark", 
						"merm_light", "merm_dark"
						])

		for k in self.config.keys():
			if not k in bs_keys:
				del _config[k]

		r = requests.post(f'{self.API_BASE}/api/layout', json=_config, headers=h)

		print(r)
		return r

	def create_api_user(self, username=''):
		""" request method to generate an pnbp-web API user 
		"""
		if not username:
			username = input('username: ')
		
		print(f'username: {username}')	
			
		while True:
			p_1 = getpass.getpass("create password: ")
			p_2 = getpass.getpass("password (again): ")
			
			if p_1 == p_2:
				break
			
			print("The passwords do not match. Please try again.")

		u = {
			"username": username,
			"password_hash": p_1
			}

		h = self.get_headers()
		r = requests.post(f'{self.API_BASE}/api/users', json=u, headers=h)
		print(r)
		print(r.json())
		return r
	
	def reset_api_password(self):
		""" request method to update the authed user's API password 
		"""
		while True:
			p_1 = getpass.getpass("new password: ")
			p_2 = getpass.getpass("password (again): ")		

			if p_1 == p_2:
				break
			
			print('passwords do not match...')

		p = {"password_hash": p_1}
		h = self.get_headers()
		r = requests.post(f'{self.API_BASE}/api/users/me', json=p, headers=h)
		print(r)
		print(r.json())
		return r


