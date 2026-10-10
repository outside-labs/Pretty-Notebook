"""Execute one reviewed local snapshot with conditional remote writes."""

from pathlib import Path

import requests

from pretty_notebook._internal import publication_plan as plans, publication_state as state


def _validate_local(notebook, plan):
    notebook._require_clean_notes("execute a publication plan")
    notebook.open_md()
    if (str(Path(notebook.NOTE_PATH).resolve()) != plan.root or notebook.notebook_id != plan.notebook_id
        or plans.api_target(notebook) != plan.target or plans.renderer_fingerprint(notebook) != plan.fingerprint
        or plans.source_snapshot(notebook) != (plan.sources, plan.identity_hash)):
        raise ValueError("Publication plan no longer matches the notebook, target, settings, or source snapshot.")
    notes, images = notebook._publication_preflight(include_images=True)
    entries = {entry["source_path"]: entry for entry in notebook.publication_routes()["routes"]}
    local_pages = [page for page in plan.pages if page.source_path is not None]
    if {page.source_path for page in local_pages} != {note.source_path for note in notes} or len(local_pages) != len(notes):
        raise ValueError("Publication plan has an incomplete local page set.")
    by_path = {note.source_path: note for note in notes}
    for page in local_pages:
        entry = entries[page.source_path]
        content = notebook.convert_to_html(by_path[page.source_path])
        if (page.name != entry["route"][1:] + ".html" or page.title != entry["title"]
            or not set(entry["aliases"]) <= set(page.aliases) or page.content != content
            or page.rendered_hash != plans.digest(content.encode())
            or page.source_hash != dict(plan.sources)[page.source_path] or page.renderer_fingerprint != plan.fingerprint):
            raise ValueError("Publication plan no longer matches the rendered pages.")
    if {image.name for image in plan.images} != set(images) or len(plan.images) != len(images):
        raise ValueError("Publication plan has an incomplete image set.")
    for image in plan.images:
        path, content_type = images[image.name]
        data = plans._image_bytes(path)
        if (path != image.path or data != image.content or plans.digest(data) != image.source_hash
            or content_type != image.content_type):
            raise ValueError("Publication plan no longer matches its image snapshot.")
    if len({page.name for page in plan.pages}) != len(plan.pages) or any(
        page.action not in {"create", "update", "unchanged", "delete", "preserve"}
        or page.action == "delete" and not plan.prune
        or page.source_path is not None and page.action in {"delete", "preserve"}
        or page.source_path is None and page.action not in {"delete", "preserve"} for page in plan.pages
    ) or any(image.action not in {"create", "update", "unchanged"} for image in plan.images):
        raise ValueError("Publication plan contains conflicts or invalid actions; review a fresh plan.")
    for action in (*plan.pages, *plan.images):
        if action.action == "create" and action.expected_etag is not None:
            raise ValueError("A create action cannot carry an update precondition.")
        if action.action != "preserve":
            _headers(notebook, action)


def _validate_remote(notebook, plan):
    server_id, pages, images = plans.read_inventory(notebook)
    if server_id != plan.server_notebook_id:
        raise ValueError("Publication plan belongs to a different server notebook.")
    for actions, current in ((plan.pages, pages), (plan.images, images)):
        for action in actions:
            if action.action == "preserve":
                continue
            actual = current.get(action.name)
            if (action.action == "create" and actual is not None
                or action.action != "create" and (actual is None or actual.get("etag") != action.expected_etag)):
                raise ValueError("Remote representation changed since planning; review a fresh plan.")


def _headers(notebook, action):
    if action.action == "create":
        return {**notebook.get_headers(), "If-None-Match": "*"}
    if not isinstance(action.expected_etag, str) or not plans.ETAG.fullmatch(action.expected_etag):
        raise ValueError("A checked update/delete requires its strong inventory ETag.")
    return {**notebook.get_headers(), "If-Match": action.expected_etag}


def execute(notebook, plan):
    if not isinstance(plan, plans.PublicationPlan):
        raise TypeError("Expected an immutable checked publication plan.")
    _validate_local(notebook, plan)
    checkpoints, checkpoint_hash = state.read(plan.root)
    state.binding(checkpoints, plan)
    if checkpoint_hash != plan.checkpoint_hash:
        raise ValueError("Sync receipts changed after planning; review a fresh plan.")
    _validate_remote(notebook, plan)
    result = {"mode": "revision-1", "dry_run": False, "pages": [], "images": []}
    for image in plan.images:
        etag = image.expected_etag
        if image.action != "unchanged":
            response = notebook._api_request(requests.put, "/api/publishing/image", headers=_headers(notebook, image),
                files={"file": (image.name, image.content, image.content_type)})
            receipt = response.json()
            expected = f'"sha256-{image.source_hash}"'
            if (not isinstance(receipt, dict) or receipt.get("name") != image.name or receipt.get("source_hash") != image.source_hash
                or receipt.get("etag") != expected or response.headers.get("ETag") != expected):
                raise ValueError("Invalid checked image receipt; refresh the remote inventory before retrying.")
            etag = expected
        state.record(plan, "images", image, etag)
        result["images"].append({"name": image.name, "action": image.action, "etag": etag})
    for page in plan.pages:
        if page.action in {"delete", "preserve"}:
            continue
        etag = page.expected_etag
        if page.action != "unchanged":
            response = notebook._api_request(requests.put, "/api/publishing/publication", headers=_headers(notebook, page),
                json={"name": page.name[:-5], "content": page.content, "title": page.title, "aliases": list(page.aliases),
                      "source_hash": page.source_hash, "rendered_hash": page.rendered_hash, "renderer_fingerprint": page.renderer_fingerprint})
            receipt = response.json()
            etag = receipt.get("etag") if isinstance(receipt, dict) else None
            if (not isinstance(receipt, dict) or receipt.get("name") != page.name[:-5] or receipt.get("rendered_hash") != page.rendered_hash
                or type(receipt.get("revision")) is not int or receipt["revision"] < 1
                or not isinstance(etag, str) or not plans.ETAG.fullmatch(etag) or response.headers.get("ETag") != etag):
                raise ValueError("Invalid checked publication receipt; refresh the remote inventory before retrying.")
        state.record(plan, "pages", page, etag)
        result["pages"].append({"name": page.name, "action": page.action, "etag": etag})
    if plan.prune:
        _validate_local(notebook, plan)
    for page in plan.pages:
        if page.action == "delete":
            response = notebook._api_request(requests.delete, "/api/publishing/publication/" + page.name[:-5], headers=_headers(notebook, page))
            receipt = response.json()
            if not isinstance(receipt, dict) or receipt.get("name") != page.name[:-5] or receipt.get("deleted") is not True:
                raise ValueError("Invalid checked delete receipt; refresh the remote inventory before retrying.")
            state.record(plan, "delete", page)
        if page.action in {"delete", "preserve"}:
            result["pages"].append({"name": page.name, "action": page.action})
    return result
