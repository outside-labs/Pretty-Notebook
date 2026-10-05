"""Check or explicitly reinstall the reviewed assets during deployment."""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.request import urlopen

from assets import AssetResolver


def install(root):
    resolver = AssetResolver(root, mode="auto")
    for entry in resolver.entries.values():
        path = resolver.path(entry["path"])
        if path.is_file():
            continue
        with urlopen(entry["cdn"], timeout=30) as response:
            if response.geturl() != entry["cdn"]:
                raise RuntimeError("Asset download redirected away from its reviewed URL.")
            data = response.read(10 * 1024 * 1024 + 1)
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise RuntimeError("Downloaded asset does not match its reviewed checksum.")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".asset-")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
            os.chmod(temporary, 0o644)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Download missing pinned assets; never runs during application requests")
    parser.add_argument("--check", action="store_true", help="Verify local assets without network access (default)")
    options = parser.parse_args()
    root = Path(__file__).resolve().parent / "static"
    if options.fetch:
        install(root)
    resolver = AssetResolver(root, mode="local")
    print(json.dumps({"valid": True, "assets": len(resolver.entries)}, sort_keys=True))


if __name__ == "__main__":
    main()
