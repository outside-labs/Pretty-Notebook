import re

from .component import Component



"""
"""
class CodeBlock(Component):
	"""
	"""
	MD_CODE = r'```([^`]*)```'
	MD_MERMAID = r'```mermaid([^`]*)```'

	LANG_EXTS = {
		'py': 'py',
		'html': 'html',
		'mermaid': None,
		'bash': 'sh',
		'powershell': 'ps1',
		'txt': 'txt',
		'json': 'json'
		}

	@staticmethod
	def regex_mermaid_to_html(matchobj):
		""" required "scripts" in blog/static/layout.html 
		"""
		return f'<div class="mermaid">{matchobj.group(1)}</div>'

	@classmethod
	@Component.prep_md_out
	def replace_mermaid(cls, note):
		""" a regex replace mtd 

		:param note: an Note instance
		"""
		p = re.compile(cls.MD_MERMAID)		
		note.md_out = p.sub(CodeBlock.regex_mermaid_to_html, note.md_out)

		return note

	@staticmethod
	def regex_unescape_comments(matchobj):
		r""" where tags are escaped by int_tag_repl,
			regex \#comment -> #comment
			within html code blocks
		"""
		_code = matchobj.group(2).replace(r'\#', '#')

		return f'<code class="{matchobj.group(1)}">{_code}</code>'

	@classmethod
	@Component.prep_md_out
	def fix_blocked_comments(cls, note):
		""" a regex replace mtd 

		:param note: an Note instance
		"""
		p = re.compile(r'<code class="(.+)">((.|\n)*)</code>')		
		note.md_out = p.sub(CodeBlock.regex_unescape_comments, note.md_out)

		return note

	@property
	def lang(self):
		""" ```lang \\n```

			the language string as used to 
			render the codeblock with syntax highlighting	
		"""
		language_line = self.codeblock.partition('\n')[0].strip()
		if not language_line:
			return None

		_lang = language_line.split(maxsplit=1)[0]
		if _lang in self.LANG_EXTS:
			return _lang

		return None

	@property
	def extn(self):
		""" ```python \\n``` => .py

			the language's file extension
		"""
		if self.lang is not None:
			return self.LANG_EXTS[self.lang]

		return None

	@property
	def body(self):
		"""Return everything after the fence language line verbatim."""
		_, separator, body = self.codeblock.partition('\n')
		return body if separator else ''

	@property
	def fname(self):
		""" a filename found in/if the
			top of a codeblock contains one:

				```py
				# hello.py
				print("hello world!")
				```
		"""
		if self.lang != 'py' or not self.body:
			return None

		first_line = self.body.partition('\n')[0]
		match = re.fullmatch(r'\s*#\s*(?P<name>\S+\.py)\s*', first_line)
		return match.group('name') if match else None

	@property
	def extraction_body(self):
		"""Return the body, excluding a recognized filename directive."""
		if not self.fname:
			return self.body

		_, separator, body = self.body.partition('\n')
		return body if separator else ''
