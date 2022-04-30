"""This module provides object abstraction for buffered Raspberry Pi GPIO channel"""

from typing import AsyncContextManager
import RPi.GPIO as GPIO
import time
from contextlib import AbstractContextManager, suppress
from threading import Thread

from NonBlockQueue import KeepNewQueue, Empty
from tsync import RWLock

__all__ = ['GPIOInput', 'AlreadyStarted', 'AlreadyStopped', 'GPIOManager']


class AlreadyStarted(Exception):
    pass


class AlreadyStopped(Exception):
    pass


class GPIOInput:
    """Object abstraction for buffered Raspberry Pi GPIO input channel"""

    def __init__(self, channel, edge, buffer_size, pull_up_down=GPIO.PUD_OFF, bouncetime=0):
        self._channel = channel
        self._edge = edge
        self._buffer_size = buffer_size
        self._pull_up_down = pull_up_down
        self._bouncetime = bouncetime

        self._buffer = KeepNewQueue(buffer_size)
        self._buffer_put_lock = RWLock()
        self._buffer_get_lock = RWLock()
        self._started = False

    @property
    def channel(self):
        return self._channel

    @property
    def edge(self):
        return self._edge

    @edge.setter
    def edge(self, edge):
        if self._edge != edge:
            self._edge = edge
            if self._started:
                self.restart()

    @property
    def buffer_size(self):
        return self._buffer_size

    @buffer_size.setter
    def buffer_size(self, buffer_size):
        if self._buffer_size != buffer_size:
            self._buffer_size = buffer_size
            buffer = KeepNewQueue(buffer_size)
            Thread(target=self._change_buffer, args=(buffer,)).start()

    @property
    def pull_up_down(self):
        return self._pull_up_down

    @pull_up_down.setter
    def pull_up_down(self, pull_up_down):
        if self._pull_up_down != pull_up_down:
            self._pull_up_down = pull_up_down
            if self._started:
                self.restart()

    @property
    def bouncetime(self):
        return self._bouncetime

    @bouncetime.setter
    def bouncetime(self, bouncetime):
        if self._bouncetime != bouncetime:
            self._bouncetime = bouncetime
            if self._started:
                self.restart()

    def start(self, edge=None, pull_up_down=None, bouncetime=None):
        if self._started:
            raise AlreadyStarted

        if edge is not None:
            self._edge = edge

        if pull_up_down is not None:
            self._pull_up_down = pull_up_down

        if bouncetime is not None:
            self._bouncetime = bouncetime

        GPIO.setup(self._channel, GPIO.IN, pull_up_down=self._pull_up_down)
        GPIO.add_event_detect(
            self._channel, self._edge, callback=self._event_callback, bouncetime=self._bouncetime)
        self.started = True

    def stop(self):
        if not self.started:
            raise AlreadyStopped

        GPIO.cleanup(self._channel)
        self.started = False

    def restart(self, *args, **kwargs):
        self.stop()
        self.start(*args, **kwargs)

    def get(self):
        if not self._buffer_get_lock.rlock.acquire(blocking=False):
            raise Empty
        try:
            return self._buffer.get()
        finally:
            self._buffer_get_lock.rlock.release()

    def _event_callback(self, channel):
        event_time = time.time()
        with self._buffer_put_lock.rlock:
            self._buffer.put(event_time)

    def _change_buffer(self, buffer: KeepNewQueue):
        with self._buffer_put_lock.wlock:
            with self._buffer_get_lock.wlock:
                old_buffer = self._buffer
                self._buffer = buffer
            with suppress(Empty):
                while True:
                    self._buffer.put(old_buffer.get())


class GPIOManager(AbstractContextManager):
    def __init__(self, mode):
        self._mode = mode

    @property
    def mode(self):
        return self._mode

    def __enter__(self):
        GPIO.setmode(self._mode)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        GPIO.clenup()
