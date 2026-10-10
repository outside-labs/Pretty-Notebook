"""Cooperative writer coordination for workers sharing one local state root."""

import asyncio
import os
import stat
from pathlib import Path


class ProcessLock:
    """Combine task serialization with a cancellation-safe POSIX file lock.

    The persistent lock file must never be replaced or removed while workers
    run. The operating system releases the lock when a process exits.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.local = asyncio.Lock()
        self.descriptor = None

    async def __aenter__(self):
        import fcntl
        await self.local.acquire()
        descriptor = None
        try:
            descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise RuntimeError("Worker coordination requires a regular local lock file.")
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    await asyncio.sleep(0.02)
            self.descriptor = descriptor
            return self
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            self.local.release()
            raise

    async def __aexit__(self, *exception):
        import fcntl
        descriptor, self.descriptor = self.descriptor, None
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
            self.local.release()
