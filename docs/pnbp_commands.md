**commands**

--- 

**core** : 

| cmd | desc |
| :----: | :----: |
| **pnbp --help** | help documentation; a list of available commands |
| **pnbp collect-all** | |
| **pnbp delete-all-pnbp** | if note contains #pnbp -> DELETE |
| ... | ... |
| pnbp collect-unlinked-mentions | ... -> nb/all unlinked mentions.md |
| pnbp delete-all-graph-dash-name | ... |

--- 

**correct** : 

| cmd | desc |
| :----: | :----: |
| pnbp delete-all-empty | delete all empty notes from nb/all empty.md |
| ... | ... |
| pnbp prepend-leading-newline | add '\n' if not to top note |
| pnbp remove-leading-newline | remove '\n' if exists from top note |
| pnbp remove-leading-and-trailing-newlines | ... | 
| ... | ... |
| pnbp strip-links-spacing --note “name” | \[\[ LINK \]\] -> \[\[LINK\]\]  |
| pnbp expand-links-spacing --note “name” | \[\[LINK\]\] -> \[\[ LINK \]\]  |
| ... | ... |
| **pnbp link-unlinked-mentions --note “name”** | here is my favorite note -> here is my \[\[favorite note\]\] |
| **pnbp remove-nonexistant-links --note “name”** | \[\[An Old Note\]\] link -> An Old Note link |

--- 

**commit** :

| cmd | desc |
| :----: | :----: |
| **pnbp git-commit-notebook** | commit to local git |
| pnbp collect-git-diff | git diff -> nb/all diff.md |

--- 

**-> pnbp-web** :

| cmd | desc |
| :----: | :----: |
| **pnbp git-clone-pnbp-web** | command to clone from github to a new blog/ |
| pnbp commit-remote | post #public to nb.API_BASE |
| pnbp commit-local | post #public to localhost:8000 regardless nb.API_BASE |
| pnbp commit-html | save the nb->html conversion to nb.HTML_PATH (local debug) |
| pnbp commit-stage | *only* print commit- changes against nb.API_BASE (staging view) |
| pnbp touch-all-public | update the mod date for all #public (remote debug) |
| pnbp commit-settings | update the remote web-settings.json values (local to server); use “--local True” for localhost setups |

--- 

#### **more commands** : 

--- 

**collect.py**

| cmd | desc |
| :----: | :----: |
| **pnbp collect-all** |  perform all collect- commands in succession |
| pnbp collect-all-empty | if a note is created on path w/out context ->... |
| pnbp collect-all-moc | "maps of content" via capitalization (e.g. \[\[PYTHON\]\]) |
| pnbp collect-all-notes | all .md files linked -> nb/all notes.md |
| pnbp collect-all-public | if note contains #public -> nb/all public.md |
| pnbp collect-all-stats | stats (incl [[links]] to collect-all "all \*" entries) |
| pnbp collect-all-tags | a fancy generated note showing \#tag per \[\[\]\] (and \[\[\]\] per \#tag)  |
| pnbp collect-all-unheadered | if not "Links: ..." at the first line, -> nb/all unheadered.md |
| pnbp collect-all-unlinked | if not a single \[\[\]\] found -> nb/all unlinked.md |
| pnbp collect-all-urls |  all regex-ed http-based urls -> nb/all urls.md |
| pnbp collect-subl-projs | nb/example.sublime_project ->... |
| pnbp collect-tasks-note | if \#tasks -> [[tasks]] |
| pnbp collect-terms | if found [[TERMS]] -> nb/TERMS.md |
| pnbp collect-code-blocked | if \`\`\`lang \`\`\` -> nb/all code blocked.md | 
| pnbp collect-all-graphs | if \`\`\`mermaid \`\`\`, \[\[\]\] -> nb/all graphs.md |
| pnbp collect-public-graph | \#public -> flat link graph...  |
| pnbp collect-git-diff | git diff -> nb/all diff.md |
| pnbp collect-nonexistant-links | ... -> nb/all nonexistant links.md |

... :
- ```pnbp collect-all``` is a main command to call **that generates** a series of .md files to the **nb.NOTE_PATH**
- **nb/all stats.md** is one that \[\[links\]\] to all **\#pnbp** tag mentions.
- ```pnbp delete-all-pnbp``` **will delete** every **\#pnbp** tagged .md file.
- **\#pnbp** tagged .md notes will all express as having : 
	- ```n.tags = [Tag(#pnbp)]```, ```n.links = []```,  ```n.codeblocks = []```, ```n.urls = []```.
- ^^ this ensures that any packaged command .md files produced to your **NOTE\_PATH** : 
	- (a) can be quickly bulk removed, 
	- (b) aren't referenced *themselves* among notes (and rather, just be abstracted collections of \[\[links\]\], \#tags, etc.); **we don't want** : 
		- ... ```pnbp collect-all-tags``` -> **nb/all tags.md** reporting *itself* as having every single **\#tag**
		- ... **'all tags'** to show up in this: ```nb.get_tagged('#mytag')```
		- ... **'all notes'** in this: ```nb.get_linked('SCIENCE')```

```pnbp collect-all-moc```
- MOCs (*"Maps of Content"* ) ~= notes that mostly contain reference links to other notes (i.e. the *"content"* itself).
- By default, any note with an n.name that is "**ENTIRELY UPPERCASE**" is considered to be an MOC here. 
	- e.g. (default) **nb/HOME.md** would be an MOC, **nb/home.md** wouldn't be; 
	- ... if note **'HOME'** was tagged with **\#cont**, it *wouldn't* be considered an MOC
	- ... if note **'home'** was tagged with **\#moc**, it *would* be considered an MOC

-> personalize w/in **pnbp_settings.json** (default values shown here) :
	- ```"MOC_TAG": "#moc"``` -> explicit **\#tag** to *include* note to MOCs
	- ```"CONT_TAG": "#cont"``` -> explicit **\#tag** to *exclude* as MOC

```json
	...
	"MOC_TAG": "#map",
	"CONT_TAG": "#nam",
	...
```



---

**tasks.py**  

| cmd | desc |
| :----: | :----: |
| **pnbp task-settle** | ... | 


```pnbp task-settle```  

e.g. **note**(s) tagged **\#tasks** : 
- complete and **uncheck** 
	- *basic* (e.g. - \[x\] ex task -> - \[ \] ex task)
	- *parameterized* (e.g. -\[x\] water (amt:2c) ->  -\[ \] water (amt: )
- complete and ***remove*** 
	- *bulleted* (e.g. - todos marked as **\#complete** ->  )
- **record** completes
	- ... to **nb\/_complete.md** under a generated section w/ today's date.

-> personalize w/in **pnbp_settings.json** (default values shown here) :
- ```"TASKS_TAG": "#tasks"``` - the \#tag denoting that a note contains "tasks".
- ```"COMPL_TAG": "#complete"``` - the \#tag denoting that a bulleted line (within a note containing \#tasks) should be recorded to nb.NOTE_PATH/\_complete.md and removed from the note.
- ```"SCHED_TAG": "#schedule"``` - (under construction)
- ```"TASKS_NOTE": "tasks"``` - a .md file name for pnbp to save a list of \[\[note\]\] links for each that contain \#tasks.
- ```"COMPL_NOTE": "_complete"``` - a .md file name for pnbp to save bulleted tasks to, on **pnbp task-settle** 

```json
	... 
	"TASKS_TAG": "#todos",
	"COMPL_TAG": "#compl",
	"COMPL_NOTE": "_compl",
	... 
```

--- 

**graph.py**

| cmd | desc |
| :----: | :----: |
| **pnbp create-link-graph --note “name”** | -> nb/graph-{note}.md | 
| **pnbp create-tag-graph** | --tag -> nb/graph-tag-{tag}.md |

generating flat relationship graphs to .md using **[mermaid js](https://mermaid-js.github.io/mermaid/#/)** : 

```pnbp create-link-graph -n SCIENCE```
- e.g. includes (and relates) every note **\[\[linked\]\]** within **nb/SCIENCE.md**, as well as every note that *backlinks* to **\[\[SCIENCE\]\]** (i.e. ```n.is_linked("SCIENCE")==True```);
- producing an **\`\`\`mermaid \`\`\`** graph to **nb/graph-SCIENCE.md**. 

```pnbp create-tag-graph -t #mytag``` 
- e.g. includes every note tagged **\#mytag** (i.e. ```n.is_tagged("#mytag")==True```) and relates among them; 
- producing an \`\`\`mermaid \`\`\` graph to **nb/graph-tag-mytag.md**.


--- 

**code.py**

| cmd | desc |
| :----: | :----: |
| **pnbp extract-code-blocks --note “name”** | --lang -> nb.NOTE_PATH/code/ | 
| **pnbp extract-all-code-blocks --note** | -> nb.NOTE_PATH/code/ (per lang found) | 

```pnbp extract-code-blocks --note="examp note" --lang=py```
- e.g. for each **\`\`\`py \`\`\`** (in ```n.codeblocks```) -> **nb/code/examp note.py**

```pnbp extract-all-codeblocks -n SCIENCE```
- e.g. for every valid commands.code.**LANG_EXTS** found (in ```n.codeblocks```) 
- -> **nb/code/n.name.ext**

```
% pnbp extract-code-blocks -n SCIENCE -l py
% cd notebook/code
% python SCIENCE.py
Hello World!
```


--- 

**subl.py**

| cmd | desc |
| :----: | :----: |
| **pnbp subl-init** | --path="." |

```pnbp subl-init```
```pnbp subl-init --path="/Users/alice/myproject"```
- (1) initiates a templated **.sublime-project** (json) file to the path
- (2) symlinks the (remote) **.sublime-project** to the **nb.NOTE\_PATH**
- -> on call to ```pnbp collect-subl-projs```, **nb/sublime-project.md** contains links that can open in **Sublime Text** when clicked ( e.g. **!\[\[myproject.sublime-project\]\]** ... ). 

```
% mkdir myproject
% cd myproject
% pnbp subl-init
```


--- 

**commit.py**

| cmd | desc |
| :----: | :----: |
| **pnbp init-git-ignore** | --path="." |

```pnbp init-git-ignore```
```pnbp init-git-ignore --path="/Users/alice/myproject"```

Command to initiate a templated **.gitignore** file to the current working dir.
- that has nothing inherently to do with the **Notebook** (is available for general convenience)
 

```
% mkdir myproject
% cd myproject
% nb-init-git-ignore
```

--- 

**pprint.py**

| cmd | desc |
| :----: | :----: |
| **pnbp pprint --note “name”** |  ... | 

```pnbp pprint -n SCIENCE```
- e.g. rich print note to terminal ( ... )

\# see [pnano](https://github.com/outside-labs/Pretty-Notebook/blob/main/apps/pnano) for more details.

--- 

___ 

### register new commands :

--- 

##### **intro** :
- -> ```pnbp do-this-thing``` will be the resulting command (when registered).
- ```@pass_nb``` provides an instance of **Notebook**, if one isn't being provided.  
- w/ ```def _func_name(nb=None):``` (decorator + leading underscore +  default) tells you that the function will be registered as a **command** ( in ../cli.py ). 
- meaning, ```def func_name():``` here (as a general pattern) aren't.
- (note : using ```def _do_this_thing(...``` will result in the same ```pnbp do-this-thing``` command name. ) 

```py
# commands/new.py
from pnbp.helpers import pass_nb


def some_portion(nb):
	pass

@pass_nb
def _do_this_thing(nb=None):
	# ...
	some_portion(nb)
	# ...
```

...  


##### **accepting a note by name** :
- -> ```pnbp parse-these-thing -n SCIENCE```

```py
# commands/new.py
from pnbp.helpers import pass_nb
from pnbp.models import Note

@pass_nb
def _parse_these_thing(note: Note, nb=None):
	pass
```

...  

##### **accept your own click options** :
-> ```pnbp search-for -s "blah blah"```

```py
# commands/new.py
import click
from pnbp.helpers import pass_nb


@pass_nb
@click.option('-s', '--search-str', help="a string to search for in the notebook.")
def _search_for(search_str: str, nb=None):
	ns = []
	for n in nb.notes.values():
		if search_str in n.md:
			ns.append(n)

	print(f"{search_str} found in {len(ns)} notes :")
	for n in ns:
		print(f"- {n.name}")
```

... 

##### pnbp=True -> 
nb.generate_note(..., **pnbp=True**)
- on ```pnbp=True```, the note.md is tagged **\#pnbp** (at the bottom).
- **ensuring that** : 
	- (a) no litter is left behind when calling ```pnbp delete-all-pnbp```.
	- (b) it's **nb/all stats.md** collected.
	- (c) it's not littering your own (or anybody else's) matches when using e.g. :  ```n.is_tagged(...), n.is_linked(...)```, ```nb.get_tagged(...), nb.get_linked(...)```.
	- (d) ^^ it's not littering other **\#pnbp** (e.g. ... 
- every (currently) generated via ```pnbp collect-all``` and ```pnbp collect-unlinked-mentions```
- **user generated *w/* pnbp commands** are explicitly *not* **\#pnbp** : 
	- **graph.py** 's ```pnbp create-link-graph```,  ```pnbp create-tag-graph```, 
	- **tasks.py** used ```nb/_complete.md``` file,  
	- anything **code.py** extracted via```pnbp extract-code-blocks``` or ```pnbp extract-all-code-blocks``` to ```nb.NOTE_PATH/code/``` files.
- **ensuring that** :
	- ```pnbp delete-all-pnbp``` doesn't remove things you likely want to keep. 
	- ```pnbp collect-all-graphs``` (-> **nb/all graphs.md**) gives \[\[links\]\].
	- ... 

```py
@pass_nb
def _collect_something_new(nb=None):
	# ...
	nb.generate_note(name='new thing', md_out='...', overwrite=True, pnbp=True)
```


--- 

#### -> **[../cli.py](https://github.com/outside-labs/Pretty-Notebook/blob/main/src/pnbp/cli.py)**


1. import your module from the commands package (at the top) :

```py
# ...
from .commands import new
# ...
```

2. find and append to the ```create_all_commands()``` function : 

```py
# ... 
def create_all_commands():
	# ... 
	# add individually : 
	create_command(new._collect_something_new) # -> pnbp collect-something-new
	# or by module :
	create_commands(new, _all=True) # _func -> pnbp func 
# ... 
```

3. navigate to ```pnbp/``` and run ```pip install --editable .``` again : 

```py
(venv) % cd pnbp
(venv) % pip install --editable .
# ... 
(venv) % pnbp --help
# -> see your new command in the list !
(venv) % pnbp do-this-thing
```

--- 

<p align=center>
  <img src=https://raw.githubusercontent.com/outside-labs/Pretty-Notebook/main/docs/IMG_pnbp.png alt=Pretty-Notebook width=200>
</p>
