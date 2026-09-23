import re

from .component import Component



"""
"""
class Tag(Component):
	""" 
	"""
	MDS_INT_TAG = r'([^\\)/>\'\w])#([A-Za-z]+)' 

	def matches(self, value) -> bool:
		"""Match a tag value with or without its leading hash."""
		return str(self).lstrip('#') == str(value).lstrip('#')

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








