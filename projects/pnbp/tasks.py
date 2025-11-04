import re
import datetime

from helpers import md_task_uncheck, md_reoccurring_task_uncheck
from models import ObsidianNotebook
from wrappers import pass_nb

"""
	- #todo a task to record _complete and perm remove w/ #complete


	- [x] my task item to record and reset to incomplete
	-> record _complete
	- [ ] my task item to record and reset to incomplete


	- [x] reoccuring parameterized task w/ (param1: 10units,param2:blahblah,)
	-> record _complete
	- [ ] reoccuring parameterized task w/ (param1: ,param2: ,)

"""
TASK_INCOMPLETE = r'(^|\s)(-\s\[\s\]\s)(.*)'
TASK_COMPLETE = r'(^|\s)(-\s\[x\]\s)(.*)'

TASK_VARS = r'\((.+)\)'
COMPL_TAG = '#complete'


@pass_nb
def record_complete_tasks(c_tasks:list=[], nb=None):
	""" 
	:param list c_tasks: e.g. ['- [x] bathroom: shower', '- [x] bathroom: toilet(s)', '- [x] some fake task']
	"""
	if c_tasks:
		fin_item_str = '\n'.join(c_tasks)

	new_day = True
	d_today = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
	repl_section = ''
	for i, s in enumerate(nb.notes['_complete'].sections):
		if re.match(d_today, s):
			repl_section = s + '\n' + fin_item_str
			_md_out = nb.notes['_complete'].sections.copy()
			_md_out[i] = repl_section

			nb.notes['_complete'].md_out = '\n\n--- \n'.join(_md_out)
			nb.notes['_complete'].save(nb)
			new_day = False

	if new_day:
		_md_out = nb.notes['_complete'].sections.copy()
		_md_out.insert(1, f'{d_today}\n{fin_item_str}')
		nb.notes['_complete'].md_out = '\n\n--- \n'.join(_md_out)
		nb.notes['_complete'].save(nb)


@pass_nb
def _uncheck_complete_tasks(nb=None):
	""" - [x] taskname 
		-> _complete
		-> - [ ] taskname 
	"""
	p = re.compile(TASK_COMPLETE)

	ns = nb.notes['housekeeping'].md.splitlines()

	complete_tasks = []
	for i, li in enumerate(ns):
		if p.search(li):
			complete_tasks.append(li)
			ns[i] = p.sub(md_task_uncheck, li)

	if complete_tasks:
		record_complete_tasks(complete_tasks, nb)

		nb.notes['housekeeping'].md_out = '\n'.join(ns)
		nb.notes['housekeeping'].save(nb)


@pass_nb
def _complete_complete_tasks(nb=None):
	""" #todo #complete -> _complete && delete
	"""
	p = re.compile(COMPL_TAG)
	ns = nb.notes['TODOS'].md.splitlines()

	complete_tasks = []
	for i, li in enumerate(ns):
		if p.search(li):
			complete_tasks.append(li)

	if complete_tasks:
		record_complete_tasks(complete_tasks)

		_md_out = nb.notes['TODOS'].md
		for t in complete_tasks:
			_md_out = re.sub(t, '', _md_out)

		nb.notes['TODOS'].md_out = _md_out
		nb.notes['TODOS'].save(nb)


@pass_nb
def _reset_reoccurring_tasks(nb=None):
	""" - [x] taskname (var1: x, )
		-> _complete
		-> - [ ] taskname (var1: , )
	"""
	ns = nb.notes['DAILY'].md.splitlines()

	p = re.compile(TASK_COMPLETE)
	p2 = re.compile(TASK_VARS)

	complete_tasks = []
	for i, li in enumerate(ns):

		if p.search(li) and (m := p2.search(li)):

			_vars = m.group(0).strip('(').strip(')').split(',')
			_vars = [v for v in _vars if not v == ' ']
			print('_vars', _vars)

			_key = li.strip('-[x] ').split('(')[0].strip()
			print('_key', _key)

			_t = datetime.datetime.strftime(datetime.datetime.now(), '%X')
			print('_t', _t)
			
			_keys = [v.split(':')[0].strip() for v in _vars if v.split(':')[0].strip()]
			print('_keys', _keys)

			_vals = [v.split(':')[1:][0].strip() for v in _vars if len(v.split(':')) > 1]
			print('_vals', _vals)

			d = {x:_vals[i] for i, x in enumerate(_keys)}
			print('d', d)

			if not '@' in d.keys():
				d.update({'@': _t})
			if d['@'] == '':
				d['@'] = _t

			print('d', d)
			print('-> exit to api')
			# ... todo
			# ... -> exit to api
			

			# -> format reset task
			reset_out = ''.join([f'{k}: ,' for k in _keys])
			reset_out = '(' + reset_out.strip(',') + ')'
			_reset_out_str = p.sub(md_task_uncheck, li)
			_reset_out_str = p2.sub(reset_out, _reset_out_str)
			print('_reset_out_str', _reset_out_str)

			# -> format _complete task
			complete_out = ''.join([f'{k}:{v}, ' for k,v in d.items()]).strip()
			complete_out = f'{_key} ({complete_out})'
			print('complete_out', complete_out)

			complete_in = li # carrying w/ us for str.replace() below
			complete_tasks.append([complete_in, complete_out, _reset_out_str])
			

	if complete_tasks:
		# -> reset task & vars
		# -> record to _complete
		_md_out = nb.notes['DAILY'].md
		for t in complete_tasks:
			c_in, c_out, r_out = t
			_md_out = _md_out.replace(c_in, r_out)
			nb.notes['DAILY'].md_out = _md_out
		nb.notes['DAILY'].save(nb)
		
		record_complete_tasks([t[1] for t in complete_tasks], nb)



""" commands -> cli
"""
@pass_nb
def _obsidian_task_settle(nb=None):
	""" all the task things
	"""
	_uncheck_complete_tasks(nb)
	_complete_complete_tasks(nb)
	_reset_reoccurring_tasks(nb)





