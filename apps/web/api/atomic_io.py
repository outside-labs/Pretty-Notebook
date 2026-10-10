"""Atomic replacement for the web app's small text files."""

from os import fchmod, fdopen, replace, fsync, link
from pathlib import Path
from stat import S_IMODE
from tempfile import mkstemp

import aiofiles


def create_text_once(target: Path, content: str) -> bool:
    """Publish complete private defaults atomically; an existing target wins."""
    descriptor, name = mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(name)
    try:
        with fdopen(descriptor, "w", encoding="utf-8") as pending:
            pending.write(content)
            pending.flush()
            fsync(pending.fileno())
        try:
            link(temporary, target)
        except FileExistsError:
            return False
        return True
    finally:
        temporary.unlink(missing_ok=True)


async def atomic_write_text(target: Path, content: str) -> None:
    """Write a sibling file, then publish it with one filesystem replacement.

    Concurrent writers each use a separate temporary file. The last successful
    replacement wins; readers see one complete version of the target.
    """
    try:
        existing_mode = S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        existing_mode = None

    descriptor, name = mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
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


async def atomic_write_bytes(target: Path, content: bytes) -> None:
    """Atomically replace a small binary file while preserving its mode."""
    try:
        existing_mode = S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        existing_mode = None

    descriptor, name = mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(name)

    try:
        with fdopen(descriptor, "wb") as pending:
            if existing_mode is not None:
                fchmod(pending.fileno(), existing_mode)

        async with aiofiles.open(temporary, "wb") as output:
            await output.write(content)
        replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
