> [!WARNING]
> `apps/web` is experimental in `0.9.0rc1` and is not supported for public deployment. The package release candidate focuses on the `pnbp` library/CLI; the web deployment security gate is still open.

Pretty-Notebook/apps/web api

RESTful management of web pages implemented in FastAPI for / using [pnbp](https://github.com/outside-labs/Pretty-Notebook/docs/pnbp.md).

--- 

**web** 
- (1) receives HTML and images (wrapping HTMLwith jinja2 template tags),
- (2) saves each page statically to an .html file,
- (3) -> catching and rendering by name via existence as a single slug through a general {content} view function ...
- e.g.  notebook/[[My Next Best Note]] -> myweburl.com/my-next-best-note 

via **pnbp**
-  (1) conversion of **\#public** notes to HTML,
-  (2) communicating with : 
    -  ... **```pnbp commit-remote```** (or **```pnbp commit-local```**) to upload changes without deleting remote pages
    -  ... **```pnbp commit-stage```** to see the staged changes before updating

**...** 
-  add **```--prune```** only after reviewing **```pnbp commit-stage```** when this notebook owns the server's entire publication namespace. Pruning deletes every remote page absent from this notebook; it is not safe for a site shared by independent notebooks or users without separate ownership tracking.
-  a failed page or image upload stops the operation before pruning. HTTP failures return a nonzero command status.
-  only notes newer than their remote copy are POST-ed. Use **```pnbp touch-all-public```** to mark every currently publishable note for upload.
-  images transfer when their names are missing remotely. Use **```--refresh-images```** to resend all images referenced by publishable notes; removing a note does not remove its previously uploaded images.

--- 

#### **installation (for local development)** :

--- 

##### (1) -> ```pnbp git-clone-pnbp-web```

or do it manually : 

```bash
git clone \
  --filter=blob:none \
  --sparse \
  --depth 1 \
  --single-branch \
  --branch main \
  https://github.com/outside-labs/Pretty-Notebook.git \
  pnbp_web

git -C pnbp_web sparse-checkout set apps/web

cd pnbp_web/apps/web

```

```
pip install -r requirements.txt
```

The integration suite requires a full repository checkout rather than the
web-only sparse checkout above. From `apps/web`, run:

```bash
python -m pip install --editable ../..
python -m pip install --requirement requirements-test.txt
python -m coverage run --source=api,views,main -m pytest tests
python -m coverage report --show-missing --fail-under=90
```

The suite creates a fresh in-memory SQLite database and temporary page, image,
and settings directories for every test.

--- 

##### (2) -> **pnbp_web/** **.env** :

Generate a JWT signing secret:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Copy the resulting value into the deployment’s untracked .env file:

```dotenv
JWT_SECRET=PASTE_GENERATED_VALUE_HERE
JWT_ALGO=HS256
```

REMINDER: Never commit the generated value.


--- 

##### (3) -> hello, world! : 

-->  run server: ```python main.py```
--> see browser: http://127.0.0.1:8000/ 

--- 

##### (4) -> create your API user : 

```py
>>> import pnbp
>>> nb = pnbp.Notebook()
>>> nb.create_api_user(username="alice")
>>> nb.refresh_token()
>>> # username: 
>>> # password: 
>>> nb.get_authed_user()
{"username": "alice"}
>>> # ^^ properly authenticating!
>>> # also available:
>>> nb.reset_api_password()
>>> nb.refresh_token() # even while same password, now old token rejected
```

The first API user can be created without a token exactly once per SQLite
database. Later accounts require that owner's token. Removing the owner does
not reopen anonymous registration; recover an owner from a database backup
instead of resetting SQLite's user ID sequence. This bootstrap guard supports
one application process. Multi-process deployment remains outside the
experimental web scope.

--- 

##### (5) -> personalize ( [**pnbp_settings.json**](https://github.com/outside-labs/Pretty-Notebook/blob/main/src/pnbp/pnbp_settings.json) ) :

```json
    ...
    "NAV_BRAND": "alice.io",
    "NAV_PAGES": {
        "about": "/about/",
        "content": [
            {
                "topic a": "/topic-a/"
            },
            {
                "topic b": "/topic-b/"
            },
        ]
    },
    "FOOTER": "<p>email: fake@email.com</p>",
    "TITLE": "Alice's Blog",
    "darkmode": true,
    "hljs_light": "sublime",
    "hljs_dark": "xt256",
    "merm_light": "forest",
    "merm_dark": "default",
    "PUB_LNK_ONLY": true,
    "COMMIT_TAG": "#blog"
}
```

```"TITLE": ""``` ... 

```"NAV_BRAND": ""``` ... 

```"FOOTER": "<p></p>"``` ... 

``` "NAV_PAGES": {}``` *dict*ates what links are in the navbar. Notice you can create a nested drop down with a *list* value. 

```"darkmode": true``` sets the darkmode to default, while white-on-black text is still available by button in the navbar. ```_light``` and ```_dark``` values dictate additional styling on the switch.

```hljs_``` - see the [highlightjs demo pages](https://highlightjs.org/static/demo/) and [this github link](https://github.com/highlightjs/highlight.js/tree/main/src/styles) to find the correct string value for your favorite styles. 

```merm_``` - see [mermaid js](https://mermaid-js.github.io/mermaid/#/) and [this github link](https://github.com/mermaid-js/mermaid/tree/master/src/themes) for the correct string value to your favorite styles.

```"PUB_LNK_ONLY": true``` turns off rendering for any internal \[\[links\]\] to HTML that point to non- \#public notes. 

```"COMMIT_TAG": "#blog"``` - choose which \#tag your notebook publishes against (default: \#public).

```"EXCLUDE_TAG": "#noblog"``` - choose which \#tag your notebook won't publish even if also tagged \#private (default: \#private).

```"HIDE_COMMIT_TAG": true``` - turns off rendering the actual "\#public" tag from the published contents (e.g. "# this is a great #public blog page!" -> "\<h1\>this is a great  blog page!\<\\h1\>") (default: ```false```). 


--- 

##### -> **POST commits !**

directly in the python repl : 

```py
>>> # --> commit your new settings ! 
>>> nb.web_settings_post()
>>> # --> tag a note #public
>>> # --> 
>>> nb.post_commits_to_web_api()
```

from the command-line : 
- ```pnbp commit-settings```
- ```pnbp commit-remote```

--- 

**\*\***
-  the only [included css](https://github.com/outside-labs/Pretty-Notebook/tree/main/apps/web/static/css) files are to support inline \<i\> [bootstrap icons](https://icons.getbootstrap.com/) \</i\>. 

--- 

<p align=center>
  <img src=https://raw.githubusercontent.com/outside-labs/Pretty-Notebook/main/docs/IMG_pnbp.png alt=Pretty-Notebook width=200>
</p>
