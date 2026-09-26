"""Atomic replacement for the web app's small text files."""

from os import fchmod, fdopen, replace
from pathlib import Path
from stat import S_IMODE
from tempfile import mkstemp

import aiofiles


async def atomic_write_text(target: Path, content: str) -> None:
    """Write a sibling file, then publish it with one filesystem replacement.

    Concurrent writers each use a separate temporary file. The last successful
    replacement wins; readers see one complete version of the target.
    """
    try:
        existing_mode = S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        existing_mode = None

    descriptor, name = mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(name)

    try:
        with fdopen(descriptor, "wb") as pending:
            if existing_mode is not None:
                fchmod(pending.fileno(), existing_mode)

        async with aiofiles.open(temporary, "w", encoding="utf-8") as output:
            await output.write(content)
        replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
