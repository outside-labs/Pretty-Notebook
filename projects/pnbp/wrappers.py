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
	# callargs = inspect.getcallargs(func)
	# print(func.__name__, callargs)

	@wraps(func)
	def inner(*args, **kwargs):
		# print(inspect.getargspec(func))
		# print(inspect.signature(func))

		if not 'nb' in inspect.signature(func).parameters.keys(): # why being wrapped?
			raise TypeError(f"@pass_nb decorator expecting keyword argument 'nb' on func '{func.__name__}'")

		args = list(args) # convert from tuple to manip

		# print('args', args)
		# print('kwargs', kwargs)
		nb = None # assume
		for i, a in enumerate(args):
			if isinstance(a, ObsidianNotebook):
				nb = args.pop(i)

		if not 'nb' in kwargs.keys():
			kwargs.update({'nb': nb})

		if not isinstance(kwargs['nb'], ObsidianNotebook):
			print('fresh nb open by pass_ wrapping...')
			kwargs['nb'] = ObsidianNotebook()

		if (note := kwargs.get('note')):
			print('**', note)
			if isinstance(note, str):
				if (n := kwargs['nb'].get(note)):
					kwargs['note'] = n
				else:
					raise KeyError(f"note: '{note}' does not exist in the notebook!")

		if 'note' in kwargs.keys():
			if not (n := kwargs['note']):
				raise KeyError(f"note: '{n}' does not exist in the notebook!")

		return func(*args, **kwargs)

	return inner



def arrow_call(func):
	""" 
	"""
	@wraps(func)
	def inner(*args, **kwargs):
		print(f'-> {func.__name__}')
		return func(*args, **kwargs)
	return inner


@arrow_call
def myfavfunc():
	return 'Hello World'

# myfavfunc()


