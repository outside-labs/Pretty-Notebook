import re
from random import randint

from rich.console import Console
from rich.markdown import Markdown

from pnbp.models import Notebook, Note, Link
from pnbp.helpers import pass_nb 



def sub_for_this(matchobj):
	""" str repl helper fxn to convert [[]] -> []()
		on rich print -> clickable (-> rich print)
	"""
	note_name = matchobj.group(1).strip()

	_note_name = note_name.replace(' ' , '%20')
	_key = f'poiuytrewq/{_note_name}.md'
	
	return f'[{note_name}]({_key})'


@pass_nb
def get_rich_note(note=Note, nb=None):
	""" 
	"""
	n = note 

	p = re.compile(Link.MDS_INT_LNK)
	rich_md = p.sub(sub_for_this, n.current_md)

	note_path_encoded = nb.NOTE_PATH.replace(' ' , '%20')

	nano_path = 'nano://' + note_path_encoded
	pnbp_path = 'pnbp://' + note_path_encoded

	rich_md = re.sub('poiuytrewq', pnbp_path, rich_md)

	menu_header = '**MENU** : '
	refresh_link = f'--->: [refresh]({pnbp_path}/{n.name.replace(" ", "%20")}.md)'
	nano_edit_link = f'nano: [{n.name}]({nano_path}/{n.name.replace(" ", "%20")}.md)'

	new_nums = []
	for fn in nb.notes.keys():
		if (m := re.match(r'new(\d{0,3})$', fn)):
			if m.group(1):
				new_nums.append(int(m.group(1)))
	if new_nums:
		new_name = f'new{max(new_nums)+1}.md'
	else:
		new_name = 'new.md'

	nano_new_link = f'nano: [new note]({nano_path}/{new_name})'
	frame = f'\n --- \n\n{menu_header}\n{refresh_link}\n{nano_edit_link}\n{nano_new_link}\n\n--- \n\n'

	rich_md = frame + rich_md + frame

	# adding 2x trailing spaces ensures single \n is rendered
	return Markdown("\n".join([line + "  " for line in rich_md.split('\n')]))



"""
"""
@pass_nb
def _pprint(note: Note, nb=None):
	""" richtext print note to terminal"""
	md = get_rich_note(note, nb)
	console = Console()

	console.print(md)









