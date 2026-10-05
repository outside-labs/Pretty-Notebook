pnbp = **"pretty notebook parser"**

> **0.9.0:** The published package supports the Python library and `pnbp`
> command-line interface on Python 3.11 or newer. Install it with
> `python -m pip install pnbp==0.9.0`. See the
> [release notes](https://github.com/outside-labs/Pretty-Notebook/blob/main/docs/release-0.9.0.md)
> for migration and support details.

--- 

**pnbp** provides programmatic access to a **notebook** via :
- **[> pnbp/models](https://github.com/outside-labs/Pretty-Notebook/blob/main/docs/pnbp_models.md)** : **models and methods**. 
    - access notes and their individual (regex established) components in the python repl, scripts, and your own shell commands. 
- **[> pnbp/commands](https://github.com/outside-labs/Pretty-Notebook/blob/main/docs/pnbp_commands.md)** : **shell commands**. 
    - run pre-defined function against a notebook in the terminal directly, or, scheduled.

\--- 

a pretty **notebook** is the collection of markdown files in a specific directory.
a pretty **note** is a single .md file within the notebook directory.

**links** ( \[\[link\]\] , !\[\[link.jpg\]\] ), **tags** ( \#tag ), **codeblocks** ( \`\`\`py print("Hello World")\`\`\` ), and **urls** ( \[goog\]\(https://google.com) ) are the main components outside of additional [render syntax](https://daringfireball.net/projects/markdown/syntax) of a .md note using an extended linking and tagging markdown. 

https://obsidian.md/ is the best example of this in action. 

--- 

#### quickstart guide : 

--- 

##### (0) -> update pip, then install the exact release

```bash
python -m pip install --upgrade pip
python -m pip install pnbp==0.9.0
```

##### (1) -> [access via the Notebook model](https://github.com/outside-labs/Pretty-Notebook/blob/main/docs/pnbp_models.md)

##### (2) -> [cli commands](https://github.com/outside-labs/Pretty-Notebook/blob/main/docs/pnbp_commands.md)

##### (3) -> [web application / api](https://github.com/outside-labs/Pretty-Notebook/blob/main/docs/web.md) *(supported only in the documented single-worker, single-notebook topology; not included in the `pnbp` wheel)*

##### (4) -> [“pnano”](https://github.com/outside-labs/Pretty-Notebook/blob/main/docs/pnano.md) *(experimental/unsupported in 0.9.0)*

--- 

##### (-1) -> **git clone** the repo.

```bash
git clone https://github.com/outside-labs/Pretty-Notebook/ pnbp
cd pnbp/
python -m pip install --editable . # development checkout, including the pnbp CLI
```

--- 

##### (2) -> choose a notebook path.

In the 0.10 development checkout, `Notebook(path="~/notes")` and
`Notebook.open("~/notes")` open an existing notebook without prompting or writing
configuration. Use `pnbp init ~/notes` to create settings explicitly. See
[settings, profiles, and legacy migration](settings.md) for the full contract.
The environment-based setup remains supported:

| var | desc | e.g. |
| :--: | :--: | :--: |
| **NOTE_PATH** | the full directory path of your notebook | ```echo 'export NOTE_PATH="/users/alice/notebook"' >> ~/.zshrc``` |
| **IMG_PATH** | (optional entirely; set here or in pnbp_settings.json) | ```echo 'export IMG_PATH="$NOTE_PATH/imgs"' >> ~/.zshrc``` | 
| **HTML_PATH** | (optional entirely; useful debug w/ Pretty-Notebook/apps/web api; set here, in pnbp_settings.json, or not at all.) | ```echo 'export HTML_PATH="$NOTE_PATH/html"' >> ~/.zshrc``` | 
| **NOTE_NESTED** | (optional; default=*"flat"*) => *"single"*, *"recurs"*, *"all"*,  | ... |
| **PNBP_SETTINGS** | (optional) a selected settings file, or **"off"** to ignore settings and secret files | ```echo 'export PNBP_SETTINGS="off"' >> ~/.zshrc``` |

**NOTE_NESTED**  
- *"flat"* - by default, **pnbp** assumes that every .md note exist within the base directory level of **NOTE\_PATH**/.
- *"single"* - if you want **pnbp** to search for .md notes within additional (non-hidden) directory level up.
- *"recurs"* - if you want .md notes to be found through all (non-hidden) directory levels up.
- *"all"* - includes hidden directories, except `.pnbp`, `.git`, `.obsidian`, and `__pycache__`.

**PNBP_SETTINGS**  
- Missing settings use defaults quietly in the development checkout.
- `pnbp init` creates `.pnbp/settings.json`; `pnbp init --migrate --dry-run` previews migration of a legacy `pnbp_settings.json`.

( ... on **Windows**? Environment Variable(s) can be set [here](https://docs.oracle.com/en/database/oracle/machine-learning/oml4r/1.5.1/oread/creating-and-modifying-environment-variables-on-windows.html#GUID-DD6F9982-60D5-48F6-8270-A27EC53807D0). Also, recall that in most places you'll also need to escape the "```\```" within any **path** strings (e.g. ```"IMG_PATH": "\\Users\\alice\\notebook\\imgs"```) used; the drive letter (e.g. ```"D:\\Media\imgs"```) is optional if it's your **\%HOMEDRIVE\%**. )

--- 

##### (3) -> **access your notes in python3.11+ !**


```py
>>> import pnbp
>>> nb = pnbp.Notebook()
... 
```

--- 

<p align=center>
  <img src=https://raw.githubusercontent.com/outside-labs/Pretty-Notebook/main/docs/IMG_pnbp.png alt=Pretty-Notebook width=200>
</p>
