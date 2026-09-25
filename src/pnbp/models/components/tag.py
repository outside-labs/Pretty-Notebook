import re

from .component import Component



"""
"""
class Tag(Component):
	""" 
	"""
	MDS_INT_TAG = r'([^\\)/>\'\w])#([A-Za-z]+)' 
	TAG_TOKEN = re.compile(r"(?<![\\/)>\'\w])#([A-Za-z]+)(?![\w-])")
	PROTECTED_PATTERNS = (
		re.compile(r'```[^`]*```'),
		re.compile(r'\[[^]]+\]\([^)]+\)'),
		re.compile(r'!?\[\[[^]]+\]\]'),
		re.compile(r'https?://[^;,\s\]\*]+'),
	)

	@classmethod
	def collect_tags(cls, note_md):
		"""Collect ASCII-letter tags outside code, links, and URLs.

		A tag begins with ``#``, contains one or more ASCII letters, and is not
		adjacent to a word character or hyphen. The returned values omit ``#``.
		"""
		spans = []
		for pattern in cls.PROTECTED_PATTERNS:
			for match in pattern.finditer(note_md):
				start, end = match.span()
				if any(start < used_end and end > used_start for used_start, used_end in spans):
					continue
				spans.append((start, end))

		eligible = list(note_md)
		for start, end in spans:
			eligible[start:end] = ' ' * (end - start)

		return [match.group(1) for match in cls.TAG_TOKEN.finditer(''.join(eligible))]

	@staticmethod
	def regex_to_html(matchobj):
		""" regex #tags out to distinguish vs
			# space means md header1
			-> \\#tag
		"""
		return f"{matchobj.group(1)}\\#{matchobj.group(2)}"

	@classmethod
	@Component.prep_md_out
	def replace_smdtags(cls, note):
		""" a regex replace mtd 

		:param note: an Note instance
		"""
		p = re.compile(cls.MDS_INT_TAG)		
		note.md_out = p.sub(Tag.regex_to_html, note.md_out)

		return note








