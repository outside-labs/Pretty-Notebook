local/ 

a Click CLI tool to interact w/ the blog/ API and an https://obsidian.md/ ("super markdown") notebook generally.

--- 

... -> blog/

- converts #public notes to HTML -> send to remote blog/ server ->  receives HTML (& images), and simply wraps 'em with jinja2 template tags, and saves each publicly-made notebook "page" statically to .html file to be rendered quick and statically (rather than via database interaction).
- if page made unpublic with #public removal, deletes from server on next push
- use **touch-all-public** to ensure all #public markdown files are pushed to the remote server, otherwise only pushes those pages with newer changes than most recently received 
- images only transfer once
- Tl;dr the most essential thing happening is that notebook/[[My Next Best Note]] -> myblogurl.com/my-next-best-note is caught via existence as a single-slug relative path through a single general {content} view function. 

--- 
**installing local/**

```sh
cd local/
pip install -r requirements.txt
pip install --editable .
# then from anywhere:
nb-get-help # returns list of available cli commands packaged
```

see settings_template.json -> write yours to **settings.json**, ignore any unused values e.g. barebones:

```json
{
    "NOTE_PATH": "/users/alice/notebook",
    "IMG_PATH": "/users/alice/notebook/imgs",
    "API_BASE": "http://127.0.0.1:8000",
    "API_TOKEN": "fakeinitialvalue",
    "PUB_LNK_ONLY": false
}
```

```"PUB_LNK_ONLY": true``` turns off rendering for any internal links to HTML that are not of additionally published (aka #public) notes.

--- 
**the notebook + note models**:

```py
from models import PysidianNotebook

nb = PysidianNotebook()

# notes dict available
nb.notes.values() # k=note name, v=PysidianNote

# get note directly by name
n = nb.get('example note')

# update content -> md_out
n.md_out('this is the new contents of my note~!')

# save it to the notebook
n.save(nb)

# if more in-line, 
# ensure you have the freshest version
n = n.save(nb)
# is equiv to 
nb.get('example note')


# the note instance exposes:
n.name # the name of the note
n.md # the actual file content
n.links # the double-bracketed internal nb links
n.tags # the #tags found (outside of any code, url, or \#escaped)
n.urls # the http(s) external links 
n.cblocks # any blocks of code via triple-backtick 
n.mtime # the file's modification date 

n.slugname # n.name=Example Note => n.slugname=example-note
n.sections # the n.md str split at "---"
n.header # -> bool, via looking for "Links: ..."

n.is_tagged('#egtag') # ->bool
n.is_linked('example note') # ->bool

# and others via the notebook instance:
nb.get_tagged('#egtag') # ->n list
nb.tags #-> list of all notebook found tags

nb.find(r'~!') #->n list, search notebook for regex 
nb.find_and_replace(r'~!', '!!') # replace (be careful!!)
# ... 
nb.generate_note('examp note 2', 'more great content here...', overwrite=True)
```

--- 
**main commands:**        

| |  |
| :----: | :----: |
| **nb-get-help** | if installed correctly, recieve list of available installed commands | |
| commit-local-html |  |
| commit-remote-api | post #public to nb.API_BASE |
| commit-local-api | post #public to localhost regardless nb.API_BASE |
| add-leading-newline |  |
| remove-leading-newline |  |
|  fix-link-spacing | \[\[ LINK \]\] -> \[\[LINK\]\]  |
| link-unlinked-mentions | ...this is my favorite note -> this is \[\[my... |
| git-commit-notebook | commit to local git |

--- 
commands/tasks.py

**nb-task-settle**   

does all the task things (if note contains #tasks, complete and uncheck basic and parameterized - \[x\] ex task  ->  -\[ \] ex task, or -\[x\] water (amt:2c) ->  -\[ \] water (amt: ), as well as remove bulleted todos as \#complete. All variants are recorded to [[_complete]] under section w/ today's date.

--- 
commands/collect.py

**nb-collect-all**

generates these .md files to the nb:

- all empty
- all moc
- all notes
- all public
- all stats
- all tags
- all unheadered
- all unlinked
- all urls
- TERMS
- tasks
- _complete
- sublime-project

| |  |
| :----: | :----: |
|  **nb-collect-all** |  perform all collect- commands in succession |
|  collect-all-empty | if a note is created on path w/out context ->... |
| collect-all-moc |  |
| collect-all-notes | all .md files linked -> notebook/all notes.md |
| collect-all-public | if note contains #public -> notebook/all public.md |
| collect-all-stats |  |
| collect-all-tags |  |
| collect-all-unheadered |  |
| collect-all-unlinked | if not a single \[\[\]\] found -> nb/all unlinked.md |
| collect-all-urls |  all regex-ed http-based urls -> notebook/all... |
| collect-subl-projs | notebook/example.sublime_project ->... |
| collect-tasks-note | if #tasks -> [[tasks]] |
| collect-terms | if found [[TERMS]] -> nb/TERMS.md |
| ... |  |
| delete-all-empty | delete all empty notes from nb/all empty.md |
| touch-all-public | update the mod date for all #public |
         
           

--- 



