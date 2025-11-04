import inspect
from functools import wraps

from models import ObsidianNotebook


def pass_nb(func):
	""" custom non-click pass_param decorator,
		maily used to boilerplate each func rather than:
		```if not nb:
			nb = ObsidianNotebook()```
		the point of which is to not be re-opening all .md
		unnecessarily when building commands that chain together.
		will handle regardless if nb passed via arg or kwarg
	"""
	callargs = inspect.getcallargs(func)

	@wraps(func)
	def inner(*args, **kwargs):
		
		if not 'nb' in callargs.keys(): # why being wrapped?
			raise TypeError(f"@pass_nb decorator expecting keyword argument 'nb' on func '{func.__name__}'")

		args = list(args) # convert from tuple to manip
		nb = None # assume
		for i, a in enumerate(args):
			if isinstance(a, ObsidianNotebook):
				nb = args.pop(i)

		if not 'nb' in kwargs.keys():
			kwargs.update({'nb': nb})

		if not isinstance(kwargs['nb'], ObsidianNotebook):
			print('fresh nb open by pass_ wrapping...')
			kwargs['nb'] = ObsidianNotebook()

		return func(*args, **kwargs)

	return inner





