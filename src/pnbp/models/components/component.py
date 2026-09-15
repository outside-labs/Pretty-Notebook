import datetime
from collections import namedtuple
from functools import wraps



class Component:
	""" an extendable namedtuple
		subclass that acts as though it's the string value
		found on an instance at it's class named attr (e.g.
			>>> # ... 
			>>> c = Component("foo")
			>>> c.component == "foo"
			True
			>>> c == "foo"
			True
			>>> c + " bar"
			"foo bar"
			>>> c # unaltered
			Helper("foo")
		)
	"""
	def __new__(cls, *args, **kwargs):
		""" """
		cls_name = cls.__name__
		attr_name = cls_name.lower()

		try:
			val = args[0]
		except IndexError:
			# being called empty, (e.g. ComponentSub() vs ComponentSub("value"))
			# don't care (?) -> 
			# return the uncalled (e.g. ComponentSub) class constructor
			val = None

		_cls = namedtuple(cls_name, [attr_name])

		_cls.__str__ = cls.__str__
		_cls.__repr__ = cls.__repr__
		_cls.__eq__ = cls.__eq__
		_cls.__add__ = cls.__add__

		for k,v in cls.__dict__.items():
			if k != 'prep_md_out':
				setattr(_cls, k, v)

		if val:
			return _cls(val)

		return _cls

	def __repr__(self):
		""" rather than returning namedtuple's repr of
			Component(component="foo") -> Helper("foo")
			to denote it's specific string-y actuality
		"""
		return f'{self.__class__.__name__}({self[0]})'

	def __str__(self):
		""" subscripting self (as tuple) directly to instance val, 
			("foo",)-> "foo"
		"""
		return self[0]

	def __eq__(self, b):
		""" 
		"""
		if not isinstance(b, str):
			b = str(b)

		if b == str(self):
			return True

		if self.__class__.__name__ == 'Tag':
			if b == self.tag.strip('#'):
				# may not be desired to match without (?), but
				return True					
				
		elif self.__class__.__name__ == 'Link':
			if b == self.note:
				# ...
				return True

		elif self.__class__.__name__ == 'Example':
			if b == self.asupper or b == self.astitle:
				return True

		return False

	def __add__(self, b) -> str:
		"""
		"""
		if not isinstance(b, str):
			# raise TypeError(f"cannot add non-str object to {self.__class__.__name__} instance.")
			b = str(b)

		return f'{str(self)}{b}'

	@staticmethod
	def prep_md_out(mtd):
		""" a decorator that allows to call regex replacement mtds
			against an Note (n) instance's current n.md_out and be assumed
			that if empty (n.md_out = ""), (aka being the initial mtd call
			to regex repl) that e.g. n.md_out = "" -> n.md_out = n.md initially;
			aka ... not re.sub-ing against an empty string.

			note: reference to "<class 'pnbp.models.note.Note'>":
				to allow an effective isinstance(a, pnbp.models.note.Note)
				without causing circular imports

		:param mtd: an @classmethod that does regex replacement on an Note instance
		"""
		@wraps(mtd)
		def inner(*args, **kwargs):
			""" """
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
	""" a Helper subclass is an for e.g. 

			Example = namedtuple("Example", "example")

			that 
				(a) defaults out to the string value of 
					the attribute (e.g. Name("dave") == "dave")
				(b) can define additional methods and properties
					associated with the subclass Name

			note: can't super() and assume
			you're getting the Component's dunder mtds defined here.
			have access to all subclass mtds, but at __new__ (pre-instance)
			subclass *actually* subclasses namedtuple. e.g. on this subclass,
				
				def __eq__(self, b):
					# despite the fact that as Component subclass
					# and my __eq__ mtd without on-class re-defining one
					# *is* Component.__eq__, ...
					super().__eq__(b) # <- my direct parent is ultimately namedtuple, 
	"""
	@property
	def asupper(self):
		return self.name.upper()

	@property
	def astitle(self):
		return self.name.title()













