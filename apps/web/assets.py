"""Resolve reviewed browser assets without runtime network requests."""

import base64
import hashlib
import json
import logging
import re
from pathlib import Path
from urllib.parse import urlsplit

MODES = {"auto", "local", "cdn"}
CDN_HOSTS = {"cdn.jsdelivr.net", "cdnjs.cloudflare.com"}


class AssetResolver:
    def __init__(self, root, *, mode="auto"):
        if mode not in MODES:
            raise RuntimeError("PNBP_ASSET_MODE must be auto, local, or cdn.")
        self.root, self.mode = Path(root), mode
        manifest = json.loads((self.root / "asset-manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1 or not isinstance(manifest.get("assets"), dict):
            raise RuntimeError("Unsupported browser asset manifest.")
        self.entries = manifest["assets"]
        self.present = set()
        for name, entry in self.entries.items():
            path = self.path(entry["path"])
            url = urlsplit(entry["cdn"])
            if url.scheme != "https" or url.hostname not in CDN_HOSTS or url.username or url.password or url.query or url.fragment:
                raise RuntimeError("Asset manifest requires an allowlisted pinned HTTPS CDN URL.")
            if not entry["version"] or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]):
                raise RuntimeError("Asset manifest has invalid version or integrity metadata.")
            version = entry["version"]
            if not entry["path"].startswith("vendor/") or f"/{version}/" not in entry["path"] or not (f"@{version}/" in url.path or f"/{version}/" in url.path):
                raise RuntimeError("Browser asset paths and CDN URLs must pin the reviewed version.")
            if not self.path(entry["notice"]).is_file():
                raise RuntimeError("A reviewed browser asset license notice is missing.")
            if path.exists():
                if not path.is_file():
                    raise RuntimeError(f"Browser asset is not a regular file: {name}.")
                data = path.read_bytes()
                integrity = "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode("ascii")
                if hashlib.sha256(data).hexdigest() != entry["sha256"] or integrity != entry["integrity"]:
                    raise RuntimeError(f"Browser asset checksum mismatch: {name}. Reinstall reviewed assets.")
                self.present.add(name)
        for entry in self.entries.values():
            if any(dependency not in self.entries for dependency in entry.get("dependencies", [])):
                raise RuntimeError("Asset manifest references an unknown dependency.")
        missing = set(self.entries) - self.present
        if missing and mode == "local":
            raise RuntimeError("Required local browser assets are missing: " + ", ".join(sorted(missing)) + ". Run install_assets.py --fetch during deployment.")
        if missing and mode == "auto":
            logging.getLogger(__name__).warning("Missing local browser assets; using pinned CDN fallbacks for %s", ", ".join(sorted(missing)))

    def path(self, relative):
        path = Path(relative)
        if path.is_absolute() or any(part in {".", ".."} for part in path.parts) or "\\" in relative:
            raise RuntimeError("Browser asset path escapes static storage.")
        candidate = self.root / path
        if any(item.is_symlink() for item in (candidate, *candidate.parents)):
            raise RuntimeError("Browser assets must not use symlink files or directories.")
        if not candidate.resolve().is_relative_to(self.root.resolve()):
            raise RuntimeError("Browser asset path escapes static storage.")
        return candidate

    def local(self, name):
        return self.mode != "cdn" and name in self.present and all(dependency in self.present for dependency in self.entries[name].get("dependencies", []))

    def resolve(self, name, request):
        if name not in self.entries:
            raise ValueError("Unknown browser asset; select a reviewed manifest entry.")
        entry = self.entries[name]
        url = str(request.url_for("static", path=entry["path"])) if self.local(name) else entry["cdn"]
        return {"url": url, "integrity": entry["integrity"], "local": self.local(name)}

    def layout_assets(self, layout, request):
        style = layout["hljs_dark"] if layout["darkmode"] else layout["hljs_light"]
        result = {name: self.resolve(name, request) for name in ("highlight-js", "mermaid-js")}
        result["highlight-css"] = self.resolve("highlight-style-" + style, request)
        for mode in ("light", "dark"):
            result["highlight-css-" + mode] = self.resolve("highlight-style-" + layout["hljs_" + mode], request)
        return result

    def validate_layout(self, layout):
        if any("highlight-style-" + layout[name] not in self.entries for name in ("hljs_light", "hljs_dark")):
            raise ValueError("Highlight styles must be reviewed asset manifest entries (default or xt256 in this installation).")

    def cacheable(self, path):
        return path in {"/static/" + entry["path"] for entry in self.entries.values()}

    def security_policy(self):
        hosts = sorted({"https://" + urlsplit(entry["cdn"]).netloc for name, entry in self.entries.items() if not self.local(name)})
        origins = " ".join(hosts)
        return "; ".join((
            "default-src 'self'", "script-src 'self' 'unsafe-inline' " + origins,
            "style-src 'self' 'unsafe-inline' " + origins,
            "font-src 'self' " + origins, "img-src 'self' data: https:",
            "connect-src 'self'", "object-src 'none'", "base-uri 'self'",
            "frame-ancestors 'none'", "form-action 'self'",
        ))
