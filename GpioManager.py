from contextlib import AbstractContextManager
import RPi.GPIO as GPIO
from enum import Enum
from gpio_monitor import OverflowPolicy
import janus
from queue import Full


class GpioManager(AbstractContextManager):
    MODE_MAP = {
        'board': GPIO.BOARD,
        'bcm': GPIO.BCM,
    }

    PULL_UP_DOWN_MAP = {
        'up': GPIO.PUD_UP,
        'down': GPIO.PUD_DOWN,
    }

    EDGE_TYPE_MAP = {
        'rising': GPIO.RISING,
        'falling': GPIO.FALLING,
        'both': GPIO.BOTH,
    }

    class OverflowPolicy(Enum):
        KEEP_NEW = 1
        KEEP_OLD = 2

    OVERFLOW_POLICY_MAP = {
        'keep_new': OverflowPolicy.KEEP_NEW,
        'keep_old': OverflowPolicy.KEEP_OLD,
    }

    def __init__(self, config):
        self._mode = self.MODE_MAP[config.get('mode', 'bcm')]

        self._channels = {}

        channels = config.get('channels', {})
        for channel, channel_config in channels.items():
            channel_info = {
                'gpio_setup_kwargs': {},
                'gpio_add_event_detect_kwargs': {},
                'queue_put_kwargs': {},
            }

            pull_up_down = channel_config.get('pull_up_down')
            if pull_up_down is not None:
                channel_info['setup_kwargs']['pull_up_down'] = self.PULL_UP_DOWN_MAP[pull_up_down]

            channel_info['event_type'] = self.EDGE_TYPE_MAP[channel_config.get(
                'event_type', 'both')]

            bouncetime = channel_config.get('bouncetime')
            if bouncetime is not None:
                channel_info['add_event_detect_kwargs']['bouncetime'] = int(
                    bouncetime)

            channel_info['buffer_size'] = int(
                channel_config.get('buffer_size', 0))

            overflow_timeout = channel_config.get('overflow_timeout')
            if overflow_timeout == 'nowait':
                channel_info['queue_put_kwargs']['block'] = False
            elif overflow_timeout is not None:
                channel_info['queue_put_kwargs']['timeout'] = int(
                    overflow_timeout)

            channel_info['overflow_policy'] = self.OVERFLOW_POLICY_MAP[channel_config.get(
                'overflow_policy', 'keep_new')]

            self._channels[int(channel)] = channel_info

    # def _event_handler(self, channel):
    #     channel_info = self._channels[channel]
    #     q = channel_info['queue'].sync_q
    #     kwargs = channel_info['queue_put_kwargs']
    #     overflow_policy = channel_info['overflow_policy']
    #     try:
    #         q.put(**kwargs)
    #     except Full:
    #         if overflow_policy == self.OverflowPolicy.KEEP_NEW:
    #             while True:

    # def __enter__(self):
    #     for channel, channel_info in self._channels.items():
