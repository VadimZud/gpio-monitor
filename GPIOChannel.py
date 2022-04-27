"""This module provides object abstraction for buffered Raspberry Pi GPIO channel"""

import RPi.GPIO as GPIO
import time

from NonBlockQueue import NonBlockQueue, KeepNewQueue, Empty

__all__ = ['Input']


class Input:
    """Object abstraction for buffered Raspberry Pi GPIO input channel"""

    def __init__(self, channel, buffer: NonBlockQueue = KeepNewQueue(), pull_up_down=None, edge_type=GPIO.BOTH, bouncetime=None):
        self.channel = RestartTriggerProperty(channel)
        self.pull_up_down = RestartTriggerProperty(pull_up_down)
        self.edge_type = RestartTriggerProperty(edge_type)
        self.bouncetime = RestartTriggerProperty(bouncetime)

        self.buffer = buffer
        self.started = False

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


class RestartTriggerProperty:
    """Helper class for boilerplate property code

    Calls object.restart() when updating the property"""

    def __init__(self, value=None):
        self.value = value

    def __get__(self, instance, owner=None):
        return self.value

    def __set__(self, instance: Input, value):
        self.value = value
        instance.restart()
