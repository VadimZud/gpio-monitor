"""This module provides thread-safe non-blocking queues"""

from abc import ABCMeta, abstractmethod
import queue
from collections import deque
from typing import Type
from threading import Thread, Lock

__all__ = ['Empty', 'NonBlockQueue', 'KeepOldQueue', 'KeepNewQueue']


class Empty(Exception):
    """Exception raised by NonBlockQueue.get() if no data"""
    pass


class NonBlockQueue(metaclass=ABCMeta):
    """Abstract class for non-blocking queue

    Non-blocking queue realizations should provides non-blocking thread-safe put/get methods."""

    @abstractmethod
    def get(self):
        """Get item from queue

        If no data this method should raise NonBlockQueue.Empty exception without execution blocking"""

        raise NotImplementedError

    @abstractmethod
    def put(self, item):
        """Add item to queue

        If queue is full this method should discard some data without execution blocking"""

        raise NotImplementedError


class KeepOldQueue(NonBlockQueue):
    """Non-blocking thread-safe FIFO queue discard new data on queue overflow"""

    def __init__(self, maxsize=0):
        self._q = queue.Queue(maxsize)

    def get(self):
        """Get item from queue

        If no data this method raise NonBlockQueue.Empty exception without execution blocking"""

        try:
            return self._q.get_nowait()
        except queue.Empty:
            raise Empty

    def put(self, item):
        """Add item to queue

        If queue is full this method discard new item without execution blocking"""

        try:
            self._q.put_nowait(item)
        except queue.Full:
            pass


class KeepNewQueue(NonBlockQueue):
    """Non-blocking thread-safe FIFO queue discard old data on queue overflow"""

    def __init__(self, maxsize=0):
        if maxsize <= 0:
            maxsize = None
        self._d = deque([], maxsize)

    def get(self):
        """Get item from queue

        If no data this method raise NonBlockQueue.Empty exception without execution blocking"""

        try:
            return self._d.pop()
        except IndexError:
            raise Empty

    def put(self, item):
        """Add item to queue

        If queue is full this method discard old item without execution blocking"""

        self._d.appendleft(item)


class ChangableTypeQueue(NonBlockQueue):
    """Non-blocking thread-safe queue wrapper can change underlying queue type and size

    Tries to prevent data loss in underlying queue when change type"""

    def __init__(self, maxsize=0, qtype: Type[NonBlockQueue] = KeepNewQueue):
        self._maxsize = maxsize
        self._qtype = qtype
        self._q = qtype(maxsize=maxsize)
        self._change_lock = Lock()

    def get(self):
        if self._change_lock.acquire(False):
            return self._q.get()
        else:
            raise Empty
