"""Private, replaceable receipts for successfully checked publishing actions."""

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from pnbp import _publication_plan as plans, _routes

MAX_STATE_BYTES = 8 * 1024 * 1024


def _validate(data):
    if (not isinstance(data, dict) or set(data) != {"version", "targets"}
        or type(data["version"]) is not int or data["version"] != 1
        or not isinstance(data["targets"], dict) or len(data["targets"]) > 32):
        raise ValueError("Invalid sync receipt schema; review .pnbp/sync.json before publishing.")
    for target, binding in data["targets"].items():
        if plans.api_target(SimpleNamespace(API_BASE=target)) != target:
            raise ValueError("Invalid sync receipt target.")
        if (not isinstance(binding, dict) or set(binding) != {"notebook_id", "server_notebook_id", "pages", "images"}
            or not plans._uuid(binding["server_notebook_id"])
            or binding["notebook_id"] is not None and not plans._uuid(binding["notebook_id"])):
            raise ValueError("Invalid sync receipt binding.")
        for kind in ("pages", "images"):
            records = binding[kind]
            if not isinstance(records, dict) or len(records) > plans.MAX_RECORDS:
                raise ValueError("Invalid or oversized sync receipts.")
            keys = {"etag", "source_hash", "rendered_hash", "renderer_fingerprint"} if kind == "pages" else {"etag", "source_hash"}
            for name, receipt in records.items():
                if kind == "pages":
                    if not name.endswith(".html"):
                        raise ValueError("Invalid sync receipt publication name.")
                    _routes.validate_route("/" + name[:-5], allow_namespace=True)
                elif Path(name).name != name or Path(name).suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                    raise ValueError("Invalid sync receipt image name.")
                if (not isinstance(receipt, dict) or set(receipt) != keys
                    or not isinstance(receipt["etag"], str) or not plans.ETAG.fullmatch(receipt["etag"])
                    or any(not isinstance(receipt[key], str) or not plans.DIGEST.fullmatch(receipt[key]) for key in keys - {"etag"})):
                    raise ValueError("Invalid sync receipt hashes or ETag.")
    return data


def read(root):
    path = Path(root) / ".pnbp" / "sync.json"
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Sync receipts must not use symlinks.")
    if not path.exists():
        return {"version": 1, "targets": {}}, None
    with path.open("rb") as stream:
        raw = stream.read(MAX_STATE_BYTES + 1)
    if len(raw) > MAX_STATE_BYTES:
        raise ValueError("Sync receipts exceed the supported size limit.")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Unreadable sync receipts; review .pnbp/sync.json before publishing.") from error
    return _validate(data), plans.digest(raw)


def binding(data, plan):
    saved = data["targets"].get(plan.target)
    if saved and (saved["notebook_id"] is not None and saved["notebook_id"] != plan.notebook_id
                  or saved["server_notebook_id"] != plan.server_notebook_id):
        raise ValueError("Sync receipts belong to a different notebook or server; review the target's .pnbp/sync.json entry.")
    return saved


def record(plan, kind, action, etag=None):
    """Merge one successful receipt under a short exclusive local write lock."""
    state = Path(plan.root) / ".pnbp"
    if state.is_symlink():
        raise ValueError("Sync receipts must not use symlinks.")
    state.mkdir(exist_ok=True, mode=0o700)
    lock = state / "sync.lock"
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise RuntimeError("Sync receipt write is active or interrupted; inspect .pnbp/sync.lock before retrying.") from error
    temporary = None
    try:
        os.close(descriptor)
        data, _ = read(plan.root)
        saved = binding(data, plan) or {"notebook_id": plan.notebook_id,
            "server_notebook_id": plan.server_notebook_id, "pages": {}, "images": {}}
        saved["notebook_id"] = plan.notebook_id
        if kind == "delete":
            saved["pages"].pop(action.name, None)
        elif kind == "pages":
            saved["pages"][action.name] = {"etag": etag, "source_hash": action.source_hash,
                "rendered_hash": action.rendered_hash, "renderer_fingerprint": action.renderer_fingerprint}
        elif kind == "images":
            saved["images"][action.name] = {"etag": etag, "source_hash": action.source_hash}
        else:
            raise ValueError("Unknown sync receipt kind.")
        data["targets"][plan.target] = saved
        _validate(data)
        raw = (json.dumps(data, sort_keys=True, indent=2) + "\n").encode()
        if len(raw) > MAX_STATE_BYTES:
            raise ValueError("Sync receipts exceed the supported size limit.")
        descriptor, temporary = tempfile.mkstemp(prefix=".sync-", suffix=".tmp", dir=state)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, state / "sync.json")
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
        lock.unlink(missing_ok=True)
