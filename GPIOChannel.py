"""This module provides object abstraction for buffered Raspberry Pi GPIO channel"""

import RPi.GPIO as GPIO
import time
from threading import Lock, Barrier, Thread
from contextlib import AbstractContextManager, suppress

from NonBlockQueue import NonBlockQueue, KeepNewQueue, KeepOldQueue, Empty

__all__ = ['Input', 'Closed']


class TCounter:
    def __init__(self, start=0):
        self._counter = start
        self._lock = Lock()

    def increment(self):
        with self._lock:
            self._counter += 1

    def decrement(self):
        with self._lock:
            self._counter -= 1

    def get(self):
        with self._lock:
            return self._counter


class Closed(Exception):
    pass


class Buffer(AbstractContextManager):
    TYPE_MAP = {
        'keep_new': KeepNewQueue,
        'keep_old': KeepOldQueue,
    }

    def __init__(self, type, maxsize=0):
        self._q: NonBlockQueue = self.TYPE_MAP[type](maxsize=maxsize)
        self._writer_counter = TCounter()
        self._closed = False

    def close(self):
        self._closed = True

    def __enter__(self):
        if self._closed:
            raise Closed

        self._writer_counter.increment()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._writer_counter.decrement()

    def get(self):
        try:
            return self._q.get()
        except Empty:
            if self._closed.get() and self._writer_counter.get() == 0:
                raise Closed
            else:
                raise

    def put(self, item):
        self._q.put(item)


class Input:
    """Object abstraction for buffered Raspberry Pi GPIO input channel"""

    def __init__(self, channel, buffer_type, buffer_size, pull_up_down=None, edge_type=GPIO.BOTH, bouncetime=None):
        self._channel = channel
        self._buffer_type = buffer_type
        self._buffer_size = buffer_size
        self._pull_up_down = pull_up_down
        self._edge_type = edge_type
        self._bouncetime = bouncetime

        self._buffer = Buffer(buffer_type, buffer_size)
        self._recreate_buffer_lock = Lock()
        self._started = False

    def _recreate_buffer(self):
        with self._recreate_buffer_lock:
            old_buffer = self._buffer
            self._buffer = Buffer(self._buffer_type, self._buffer_size)
            old_buffer.close()
            barrier = Barrier(2)

    def _buffer_data_recover(self, old_buffer: Buffer):
        with old_buffer:
            old_buffer.close()

    def event_handler(self, channel):
        self.buffer.put(time.time())

    def start(self):
        if not self.started:
            if self.pull_up_down is None:
                GPIO.setup(self.channel, GPIO.IN)
            else:
                GPIO.setup(self.channel, GPIO.IN,
                           pull_up_down=self.pull_up_down)

            if self.bouncetime is None:
                GPIO.add_event_detect(
                    self.channel, self.edge_type, callback=self.event_handler)
            else:
                GPIO.add_event_detect(
                    self.channel, self.edge_type, callback=self.event_handler, bouncetime=self.bouncetime)

            self.started = True

    def stop(self):
        if self.started:
            GPIO.cleanup(self.channel)
            self.started = False

    def restart(self):
        self.stop()
        self.start()
