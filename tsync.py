from threading import Lock
from contextlib import AbstractContextManager
from time import time

__all__ = ['Turnstile', 'Switch', 'RWLock']


class Turnstile:
    def __init__(self, lock=Lock()):
        self._lock = lock

    @property
    def lock(self):
        return self._lock

    def cross(self, *args, **kwargs):
        if not self._lock.acquire(*args, **kwargs):
            return False
        try:
            return True
        finally:
            self._lock.release()


class Switch(AbstractContextManager):
    def __init__(self, lock=Lock()):
        self._lock = lock
        self._counter = 0
        self._counter_lock = Lock()

    @property
    def lock(self):
        return self._lock

    def enter(self, *args, **kwargs):
        with self._counter_lock:
            if self._counter == 0:
                if not self._lock.acquire(*args, **kwargs):
                    return False
            try:
                self._counter += 1
                try:
                    return True
                except:
                    self._counter -= 1
                    raise
            except:
                if self._counter == 0:
                    self._lock.release()
                raise

    def exit(self):
        with self._counter_lock:
            self._counter -= 1
            try:
                if self._counter == 0:
                    self._lock.release()
            except:
                self._counter += 1
                raise

    def __enter__(self):
        self.enter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.exit()


class RWLock:
    class RLock(AbstractContextManager):
        def __init__(self, turnstile: Turnstile, switch: Switch):
            self._turnstile = turnstile
            self._switch = switch

        def acquire(self, blocking=True, timeout=-1):
            start = time()
            if not self._turnstile.cross(blocking, timeout):
                return False
            if timeout > 0:
                timeout -= (time() - start)
                if timeout < 0:
                    return False
            return self._switch.enter(blocking, timeout)

        def release(self):
            self._switch.exit()

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self):
            self.release()

    class WLock(AbstractContextManager):
        def __init__(self, turnstile: Turnstile, switch: Switch):
            self._turnstile = turnstile
            self._switch = switch

        def acquire(self, blocking=True, timeout=-1):
            start = time()
            if not self._turnstile.lock.acquire(blocking, timeout):
                return False
            try:
                if timeout > 0:
                    timeout -= (time() - start)
                    if timeout < 0:
                        return False
                return self._switch.lock.acquire(blocking, timeout)
            finally:
                self._turnstile.lock.release()

        def release(self):
            self._switch.lock.release()

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self):
            self.release()

    def __init__(self):
        turnstile = Turnstile()
        switch = Switch()
        self._rlock = self.RLock(turnstile, switch)
        self._wlock = self.WLock(turnstile, switch)

    @property
    def rlock(self):
        return self._rlock

    @property
    def wlock(self):
        return self._wlock
