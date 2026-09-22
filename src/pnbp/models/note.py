import os
import re
import stat
import tempfile

from collections import namedtuple, defaultdict
from pathlib import Path

from .components import Link, Tag, Url, CodeBlock

from pnbp.helpers import _convert_datetime


class Note(namedtuple('Note', ['name', 'md', 'links', 'tags', 'urls', 'codeblocks', 'mtime'])):

	def __new__(cls, name, md, links, tags, urls, codeblocks, mtime):
		"""
		:param str name: the filename stripped of .md
		:param str md: the in mem note context read from file
		:param list links: all regex found [[links]] 's in md
		:param list tags: all regex found #tag 's in md
		:param list urls: all regex found http/https links in md
		:param list codeblocks: all regex found ```backtick code blocks```
		:param str mtime: the local md most recent modification date
			-> used against remote blog api to determine if POST required
		"""
		all_tags = [f'#{t}' for t in tags]

		# removing "#tags" found within Urls, 
		# CodeBlocks, and Links :
		_tags = list(set(all_tags.copy()))
		_remove = defaultdict(int)
		for t in _tags:
			for u in urls:
				if (num_occur := len(re.findall(t, u))):
					_remove[t] += num_occur
			for b in codeblocks:
				if (num_occur := len(re.findall(t, b))):
					_remove[t] += num_occur
			for l in links:
				if (num_occur := len(re.findall(t, l))):
					_remove[t] += num_occur

		for tag, occ in _remove.items():
			for x in range(occ):
				if tag in all_tags:
					all_tags.remove(tag)
		
		if (m := re.match(r'^#([A-Za-z]+)', md)):
			# catch a #tag at the very beginning of the md string
			# without opening pandoras box
			all_tags.append(f'#{m.groups(1)[0]}')

		tags = [Tag(t) for t in set(all_tags)]
		urls = [Url(u) for u in set(urls)]
		links = [Link(l) for l in set(links)]

		codeblocks = [CodeBlock(cb) for cb in codeblocks if cb.split()]

		if "#pnbp" in tags:
			tags = [Tag("#pnbp")]
			urls = []
			links = []
			codeblocks = []

		return super().__new__(cls, name, md, links, tags, urls, codeblocks, mtime)

	def __init__(self, *args, **kwargs):
		""" 
		:param md_out: safety first, make it hard to overwrite any note file
			-> set self.md_out = "as example, correct as is string instance"
			-> update file via self.save()
		"""
		self.md_out: str | None = None
		self.pprotect = {}
		self.source_path: str | None = None
		self._source_exists = False
		self._source_signature = None

	def __str__(self):
		""" """
		return self.name
	
	@property
	def current_md(self) -> str:
		""" 
		:return: the most updated (between self.md and self.md_out) Markdown content
		"""
		return self.md if self.md_out is None else self.md_out

	@property
	def is_unsaved(self) -> bool:
		""" the content of self.md is different (i.e. req self.save())
			as compared to self.md_out
		"""
		return self.md_out is not None and self.md_out != self.md

	def discard_changes(self):
		""" flush self.md_out, without self.save() -ing changes
		"""
		self.md_out = None
		return self

	@property
	def subdirs(self):
		"""
		"""
		_name = Link(self.name)
		return _name.subdirs
	
	@property
	def slugname(self):
		""" My Note Name -> my-note-name
		"""
		_name = Link(self.name)
		return _name.slugname

	@property
	def linkname(self):
		""" self.name -> [[self.name]]
		"""
		_name = Link(self.name)
		return _name.aslink

	@property
	def sections(self)->list:
		"""	"""
		return [x.strip() for x in self.current_md.split('---') if x]

	@property
	def header(self):
		""" """
		NOTE_HEADER = os.environ.get('NOTE_HEADER')

		if not NOTE_HEADER:
			NOTE_HEADER = r'^Links'
		else:
			NOTE_HEADER = fr'{NOTE_HEADER}'

		try:
			for i in (0, 1):
				if re.match(NOTE_HEADER, self.sections[i]):
					return self.sections[i]

		except IndexError:
			# an empty note 
			pass
		
		return None

	@property
	def aliases(self):
		""" """
		if self.sections[0].startswith('aliases: '):
			return True
		return None

	@property
	def footnotes(self):
		""" """
		if re.match(r'\[\^\d+\]: ', self.sections[-1]):
			return True
		return None

	def save(self, nb):
		""" save note to .md file on NOTE_PATH,
			if provided self.md_out has been updated.

		:param nb: the Notebook instance must be passed to save!
		"""
		
		if self.md_out is None:
			return self

		if self.md_out == self.md and self._source_exists:
			self.md_out = None
			return self

		if not isinstance(self.md_out, str):
			raise TypeError(f'{self.__class__.__name__}.md_out must be a str, not {type(self.md_out)}')

		root = Path(nb.NOTE_PATH).expanduser().resolve()
		relative_path = self.source_path or f"{self.name}.md"
		path = (root / relative_path).resolve()

		try:
			path.relative_to(root)
		except ValueError as e:
			raise ValueError("Note path escapes NOTE_PATH") from e

		if path.suffix.lower() != ".md":
			raise ValueError(f"Not a Markdown note: {path}")

		path.parent.mkdir(parents=True, exist_ok=True)

		if self._source_exists:
			source_stat = self._require_unchanged_source(path)
			self._atomic_replace(path, self.md_out, source_stat)
		else:
			self._exclusive_create(path, self.md_out)

		saved = nb.open_note(path)
		self.source_path = saved.source_path
		self._source_exists = True
		self.md_out = None
		return saved

	@staticmethod
	def _stat_signature(file_stat):
		return (
			file_stat.st_dev,
			file_stat.st_ino,
			file_stat.st_size,
			file_stat.st_mtime_ns,
		)

	def _require_unchanged_source(self, path):
		try:
			before = path.stat()
			text = path.read_text(encoding="utf-8")
			after = path.stat()
		except FileNotFoundError as e:
			raise RuntimeError(f"Cannot save {self.name}: source changed on disk.") from e

		if (
			self._stat_signature(before) != self._stat_signature(after)
			or (
				self._source_signature is not None
				and self._stat_signature(after) != self._source_signature
			)
			or text != self.md
		):
			raise RuntimeError(f"Cannot save {self.name}: source changed on disk.")

		return after

	@staticmethod
	def _exclusive_create(path, text):
		flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
		fd = os.open(path, flags, 0o666)

		try:
			with os.fdopen(fd, "w", encoding="utf-8") as output:
				fd = None
				output.write(text)
				output.flush()
				os.fsync(output.fileno())
		except Exception:
			if fd is not None:
				os.close(fd)
			path.unlink(missing_ok=True)
			raise

	def _atomic_replace(self, path, text, source_stat):
		fd, temporary_name = tempfile.mkstemp(
			dir=path.parent,
			prefix=f".{path.name}.",
			suffix=".tmp",
		)
		temporary_path = Path(temporary_name)

		try:
			with os.fdopen(fd, "w", encoding="utf-8") as output:
				fd = None
				output.write(text)
				output.flush()
				os.fsync(output.fileno())

			os.chmod(temporary_path, stat.S_IMODE(source_stat.st_mode))

			current_stat = path.stat()
			current_text = path.read_text(encoding="utf-8")
			if (
				self._stat_signature(current_stat) != self._stat_signature(source_stat)
				or current_text != self.md
			):
				raise RuntimeError(f"Cannot save {self.name}: source changed on disk.")

			os.replace(temporary_path, path)
		finally:
			if fd is not None:
				os.close(fd)
			temporary_path.unlink(missing_ok=True)

	def is_tagged(self, tag: str="", tags: list=[], to_all=False, at_all=False)->bool:
		""" check if note.md contains a #tag

		:param tag: the #tag in question
		:param tags: a list of possible tags
		:param to_all: to_all=True requires that all entered param tags are found in self.md
		:param at_all: at_all=True as the only paramater will return False if note has no tags at all
		"""
		if not tag and not tags and at_all and self.tags:
			return True

		if not tag and not tags and not at_all:
			msg = "Did you mean to call is_tagged(at_all=True)? Otherwise,\n"
			raise ValueError(f"{msg}provide e.g. is_tagged(tag='#examp'), or is_tagged(tags=['#find', '#us'], to_all=True)")

		if tags or isinstance(tag, list):
			# handling for poss pos arg entry
			if not tags:
				tags = tag

			res = []
			for tag in tags:
				if self.is_tagged(tag):
					if not to_all:
						return True
					else:
						res.append(tag)

			if res == tags:
				return True

		tag = str(tag)

		tag = f"#{tag.lstrip('#')}" #failsafe

		if tag in self.tags:
			return True
			
		return False

	def is_linked(self, link: str="", links: list=[], to_all=False, at_all=False)->bool:
		""" check if note.md contains a [[link]]

		:param link: the [[link]] in question
		:param links: 
		:param to_all:
		:param at_all:
		"""
		if not link and not links and at_all and self.links:
			return True

		if not link and not links and not at_all:
			msg = "Did you mean to call is_linked(at_all=True)? Otherwise,\n"
			raise ValueError(f"{msg}provide e.g. is_linked('some-note'), or is_linked(links=['note-a', 'note-b'], to_all=True)")

		if links or isinstance(link, list):
			if not links:
				links = link

			res = []
			for link in links:
				if self.is_linked(link):
					if not to_all:
						return True
					else:
						res.append(link)

			if res == links:
				return True

		link = link.replace('[', '').replace(']', '').strip().lower()

		if link in [l.link.lower() for l in self.links]:
			return True

		return False

	def remove_links(self, links: list):
		""" if [[my link]] in links, -> if my link in links
			*stage* removal to self.md_out

		:param links: the [[link]] names to remove
		"""
		ns = self.current_md
		links = [l for l in links if not '.' in l] # keep images!
		
		for name in links:
			name = re.escape(str(name))
			p = re.compile(fr'(\[\[\s?)({name})(\s?\]\])')

			if (ml := p.findall(ns)):
				for m in ml:
					print(f'[[{m[1]}]] --> ', m[1])

			ns = p.sub(Link.remove_link_mention, ns)

		self.md_out = ns

		return self 

	def md_out_to_html(self, nb):
		""" 
		"""
		nb.convert_to_html(self) # ...

	def prime_md_out_protect(self):
		""" Replace links, tags, urls, codeblocks
			w/ an _key, saving all actual .md item values at
			self.pprotect[_key], and the repl'd skeleton .md 
			content to self.md_out.
			This allows for safe parsing/repl against .md "body content"
			exclusively. -> ... -> self.prime_md_out_release()
		"""
		if self.md_out is not None:
			raise Exception(f"""You already have updated context for {self.name} in note.md_out.
							note.save() or n.md_out = '' first...""")

		ns = self.md 		
		# pull out all code, links, tags, urls, 
		# so that they don't get matched with 
		for i, cb in enumerate(self.codeblocks):
			_repl = f'cb_{i}.'
			ns = ns.replace(cb.codeblock, _repl)
			self.pprotect.update({_repl: cb})
		for i, l in enumerate(self.links):
			_repl = f'l_{i}.'
			ns = ns.replace(f'[[{l.link}]]', _repl)
			self.pprotect.update({_repl: f'[[{l}]]'})
		for i, t in enumerate(self.tags):
			_repl = f't_{i}.'
			ns = ns.replace(t.tag, _repl)
			self.pprotect.update({_repl: t})
		for i, u in enumerate(self.urls):
			_repl = f'u_{i}.'
			ns = ns.replace(u.url, _repl)
			self.pprotect.update({_repl: u})

		self.md_out = ns

	def prime_md_out_release(self, nb=None):
		""" Replace the _keys at self.pprotect to prepare
			the note to be saved.

		:param nb: lazy accept Notebook to save Note inline
		"""
		if self.md_out is None and self.pprotect:
			raise Exception("Can't return prime note context that was never protected to begin with!")

		ns = self.md_out		
		for k,v in self.pprotect.items():
			# put code, links, tags, urls, back in:
			ns = ns.replace(k, v)

		self.md_out = ns
		self.pprotect = {}
		if nb:
			# save the note:
			self.save(nb)
		else:
			print("Sucessful pprotect release. Don't forget to save!")

	def prepend_section(self, content):
		""" add an section to the beginning of the .md content
			(or .md_out content instead if exists)

			reccomended save immediately (aka don't prepend 
			again inline expecting updated sections)

		:param content: should itself shouldn't start with section header "\n\n--- "
		:returns: updated self.md_out 
		"""
		sheader = "\n\n--- "

		if content.startswith(sheader):
			content = content.lstrip(sheader)

		_md_out = self.sections.copy()

		pos = 0
		if self.header:
			pos += 1
		if self.aliases:
			pos += 1

		_md_out.insert(pos, content)

		self.md_out = '\n\n--- \n'.join(_md_out)

		if self.aliases:
			self.md_out = '--- \n' + self.md_out

	def append_section(self, content):
		"""
		:param content: should itself shouldn't start with section header "\n\n--- "
		:returns: updated self.md_out 
		""" 
		_md_out = self.sections.copy()
		
		if self.footnotes:
			_md_out.insert(-1, content)
		else:
			_md_out.append(content)

		self.md_out = '\n\n--- \n'.join(_md_out)

		if self.aliases:
			self.md_out = '--- \n' + self.md_out

	def insert_section(self, pos: int, content: str):
		""" 
		:param pos: the 0-index position to insert content to new section
		:param content: the content to generate a section out of
		"""
		_md_out = self.sections.copy()
		_md_out.insert(pos, content)

		self.md_out = '\n\n--- \n'.join(_md_out)

	def prepend_today_section(self, nb=None):
		""" 
		"""
		new_day = True
		d_today = _convert_datetime("now", as_date=True)
		for i,s in enumerate(self.sections):
			if s.startswith(d_today):
				new_day = False

		if new_day:
			cont = f'\n\n--- \n{d_today}\n\n'
			self.prepend_section(cont)
			self.save(nb)







