"""This module provides object abstraction for buffered Raspberry Pi GPIO channel"""

import RPi.GPIO as GPIO
import time
from contextlib import suppress
from threading import Thread

from NonBlockQueue import KeepNewQueue, Empty
from tsync import RWLock

__all__ = ['GPIOInput', 'AlreadyStarted', 'AlreadyStopped']


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
        self._buffer_lock = RWLock()
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
            self.restart()

    @property
    def bouncetime(self):
        return self._bouncetime

    @bouncetime.setter
    def bouncetime(self, bouncetime):
        if self._bouncetime != bouncetime:
            self._bouncetime = bouncetime
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
        if self._started:
            self.stop()
            self.start(*args, **kwargs)

    def _event_callback(self, channel):
        event_time = time.time()
        with self._buffer_lock.rlock:
            self._buffer.put(event_time)

    def _change_buffer(self, buffer: KeepNewQueue):
        with self._buffer_lock.wlock:
            with suppress(Empty):
                while True:
                    buffer.put(self._buffer.get())
            self._buffer = buffer
