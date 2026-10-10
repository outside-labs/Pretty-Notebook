import asyncio
import os

import pytest
from api.process_lock import ProcessLock


def test_independent_coordinators_serialize_and_cancellation_releases_waiter(tmp_path):
    async def scenario():
        first = ProcessLock(tmp_path / 'site.lock')
        second = ProcessLock(tmp_path / 'site.lock')
        entered = []
        async def contender():
            async with second:
                entered.append(True)
        async with first:
            waiter = asyncio.create_task(contender())
            await asyncio.sleep(0.05)
            assert entered == []
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError): await waiter
            assert not second.local.locked() and second.descriptor is None
        async with second:
            assert second.descriptor is not None
        assert not first.local.locked() and not second.local.locked()
    asyncio.run(scenario())


def test_failed_lock_open_releases_local_task_lock(tmp_path):
    target = tmp_path / 'site.lock'
    target.symlink_to(tmp_path / 'other')
    lock = ProcessLock(target)
    async def scenario():
        with pytest.raises(OSError):
            async with lock: pass
        assert not lock.local.locked()
        target.unlink()
        async with lock:
            assert os.stat(target).st_mode & 0o777 == 0o600
    asyncio.run(scenario())
