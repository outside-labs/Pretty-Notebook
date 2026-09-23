from functools import wraps


class Component(str):
	"""A stable string value with a component-specific named attribute.

	Component subclasses behave like strings for equality, hashing, and string
	operations. Their lower-cased class name remains available as an attribute,
	for example ``Tag("#topic").tag``.
	"""

	def __new__(cls, value=None, **kwargs):
		attr_name = cls.__name__.lower()

		if value is not None and kwargs:
			raise TypeError(f"{cls.__name__} accepts either a value or {attr_name}=, not both")

		if value is None:
			try:
				value = kwargs.pop(attr_name)
			except KeyError as e:
				raise TypeError(f"{cls.__name__} requires a value or {attr_name}=") from e

		if kwargs:
			unexpected = next(iter(kwargs))
			raise TypeError(f"{cls.__name__} got an unexpected keyword argument {unexpected!r}")

		return super().__new__(cls, str(value))

	def __init__(self, value=None, **kwargs):
		# Construction is completed in __new__; accepting the same arguments here
		# lets named component fields work with immutable str subclasses.
		pass

	def __getattr__(self, name):
		if name == self.__class__.__name__.lower():
			return str(self)
		raise AttributeError(f"{self.__class__.__name__!s} has no attribute {name!r}")

	def __repr__(self):
		return f"{self.__class__.__name__}({str(self)!r})"

	def matches(self, value) -> bool:
		"""Return whether *value* is an exact component value match."""
		return str(self) == str(value)

	@staticmethod
	def prep_md_out(mtd):
		"""Prepare a note's staged Markdown before a replacement method runs."""
		@wraps(mtd)
		def inner(*args, **kwargs):
			from pnbp.models.note import Note

			note = kwargs.get('note')

			if note is None:
				note = next((a for a in args if isinstance(a, Note)), None)

			if not note:
				raise ValueError("...")

			if note.md_out is None:
				note.md_out = note.md

			return mtd(*args, **kwargs)

		return inner


class Example(Component):
	"""Example component used by the component documentation."""

	@property
	def asupper(self):
		return str(self).upper()

	@property
	def astitle(self):
		return str(self).title()
