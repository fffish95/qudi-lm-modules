# -*- coding: utf-8 -*-

"""
A module for controlling a shutter via a digital output line of an NI card.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

from PySide2 import QtCore
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex


class ShutterLogic(LogicBase):
    """
    Control a shutter through a digital output channel of a (possibly shared) NI card.

    The connected NI card hardware module may also be used by other modules (e.g. scanners
    or counters) for completely different tasks (AO/AI/CI/CO). This module only ever creates
    and tears down its own, uniquely named digital output task and never touches tasks
    belonging to other modules, so it can safely run alongside them on the same NI card.
    """

    # declare connectors
    nicard = Connector(interface="NICard")
    # declare config options
    _do_channel = ConfigOption('do_channel', None, missing='error')
    # Unique DAQmx task name. Must be unique per ShutterLogic instance connected to the same
    # NI card so that several shutters can share one card without task-name collisions.
    _task_name = ConfigOption('task_name', 'shutter', missing='nothing')
    # Logic level meaning "shutter open". Some shutter drivers are wired active-low.
    _open_level = ConfigOption('open_level', True, missing='nothing')

    # signal emitted whenever the shutter state changes (True == open)
    sigShutterStateChanged = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._thread_lock = Mutex()
        self._nicard = None
        self.do_task = None
        self._is_open = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._nicard = self.nicard()
        self.do_task = None
        self._is_open = False

        channels = self._do_channel
        if channels is None:
            self.log.error('No "do_channel" configured for ShutterLogic. Shutter control '
                            'will be disabled.')
            return
        if isinstance(channels, str):
            channels = [channels]

        # Defensively close any stale task with the same name that may be left over from a
        # previous crashed session. This never touches tasks belonging to other modules since
        # it only ever addresses a task with this module's own, uniquely configured name.
        try:
            self._nicard.close_do_task(taskname=self._task_name)
        except Exception:
            pass

        task = self._nicard.create_do_task(taskname=self._task_name, channels=channels)
        if task in (None, -1):
            self.log.error(f'Could not create digital output task "{self._task_name}" for the '
                            f'shutter on channel(s) {channels}. Shutter control will be disabled.')
            self.do_task = None
            return
        self.do_task = task
        # Make sure the shutter starts in a well-defined (closed) state.
        self.shutter_off()

    def on_deactivate(self):
        """ Perform required deactivation. """
        if self._nicard is not None and self.do_task is not None:
            try:
                self._nicard.close_do_task(taskname=self._task_name)
            except Exception:
                self.log.exception(f'Error while closing shutter task "{self._task_name}".')
        self.do_task = None

    @property
    def is_open(self):
        """ Return the last known shutter state (True == open). """
        return self._is_open

    def shutter_on(self):
        """ Open the shutter. """
        if self.do_task is None:
            self.log.error('Shutter digital output task is not available. Cannot open shutter.')
            return -1
        with self._thread_lock:
            result = self._nicard.write_task(task=self.do_task, data=self._open_level)
        self._is_open = True
        self.sigShutterStateChanged.emit(True)
        return result

    def shutter_off(self):
        """ Close the shutter. """
        if self.do_task is None:
            self.log.error('Shutter digital output task is not available. Cannot close shutter.')
            return -1
        with self._thread_lock:
            result = self._nicard.write_task(task=self.do_task, data=(not self._open_level))
        self._is_open = False
        self.sigShutterStateChanged.emit(False)
        return result
