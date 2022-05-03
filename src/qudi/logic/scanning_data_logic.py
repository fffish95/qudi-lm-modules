# -*- coding: utf-8 -*-
"""
This module is responsible for controlling any kind of scanning probe imaging for 1D and 2D
scanning.

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


import time
import copy
import datetime
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from PySide2 import QtCore

from qudi.core.module import LogicBase
from qudi.util.mutex import RecursiveMutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar
from qudi.util.datastorage import ImageFormat, NpyDataStorage, TextDataStorage
from qudi.util.units import ScaledFloat

from qudi.interface.scanning_probe_interface import ScanData


class ScanningDataLogic(LogicBase):
    """
    ToDo: Write documentation
    """

    # declare connectors
    _scan_logic = Connector(name='scan_logic', interface='ScanningProbeLogic')

    # config options
    _max_history_length = ConfigOption(name='max_history_length', default=10)

    # status variables
    _scan_history = StatusVar(name='scan_history', default=list())

    # signals
    sigHistoryScanDataRestored = QtCore.Signal(object)
    sigSaveStateChanged = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._thread_lock = RecursiveMutex()

        self._curr_history_index = 0
        self._curr_data_per_scan = dict()
        self._logic_id = None
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._shrink_history()
        if self._scan_history:
            self._curr_data_per_scan = {sd.scan_axes: sd for sd in self._scan_history}
            self.restore_from_history(-1)
        else:
            self._curr_history_index = 0
            self._curr_data_per_scan = dict()
        self._logic_id = self._scan_logic().module_uuid
        self._scan_logic().sigScanStateChanged.connect(self._update_scan_state)
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self._scan_logic().sigScanStateChanged.disconnect(self._update_scan_state)
        self._curr_data_per_scan = dict()
        return

    @_scan_history.representer
    def __scan_history_to_dicts(self, history):
        return [data.to_dict() for data in history]

    @_scan_history.constructor
    def __scan_history_from_dicts(self, history_dicts):
        return [ScanData.from_dict(hist_dict) for hist_dict in history_dicts]

    def get_current_scan_data(self, scan_axes):
        with self._thread_lock:
            return self._curr_data_per_scan.get(scan_axes, None)

    def get_all_current_scan_data(self):
        with self._thread_lock:
            return self._curr_data_per_scan.copy()

    @QtCore.Slot()
    def history_previous(self):
        with self._thread_lock:
            if self._curr_history_index < 1:
                self.log.warning('Unable to restore previous state from scan history. '
                                 'Already at earliest history entry.')
                return

            self.log.debug(f"Previous hist index called. Curr index: {self._curr_history_index}")

            return self.restore_from_history(self._curr_history_index - 1)

    @QtCore.Slot()
    def history_next(self):
        with self._thread_lock:
            if self._curr_history_index >= len(self._scan_history) - 1:
                self.log.warning('Unable to restore next state from scan history. '
                                 'Already at latest history entry.')
                return
            return self.restore_from_history(self._curr_history_index + 1)

    @QtCore.Slot(int)
    def restore_from_history(self, index):
        with self._thread_lock:
            if self._scan_logic().module_state() != 'idle':
                self.log.error('Scan is running. Unable to restore history state.')
                return

            if index < 0:
                index = max(0, len(self._scan_history) + index)

            try:
                data = self._scan_history[index]
            except IndexError:
                self.log.exception('Unable to restore scan history with index "{0}"'.format(index))
                return

            settings = {
                'range': {ax: data.scan_range[i] for i, ax in enumerate(data.scan_axes)},
                'resolution': {ax: data.scan_resolution[i] for i, ax in enumerate(data.scan_axes)},
                'frequency': {data.scan_axes[0]: data.scan_frequency}
            }
            self._scan_logic().set_scan_settings(settings)

            self.log.debug(f"Restoring hist settings from index {index} with {settings}")

            self._curr_history_index = index
            self._curr_data_per_scan[data.scan_axes] = data
            self.sigHistoryScanDataRestored.emit(data)
            return

    @QtCore.Slot(bool, object, object)
    def _update_scan_state(self, running, data, caller_id):

        settings = {
            'range': {ax: data.scan_range[i] for i, ax in enumerate(data.scan_axes)},
            'resolution': {ax: data.scan_resolution[i] for i, ax in enumerate(data.scan_axes)},
            'frequency': {data.scan_axes[0]: data.scan_frequency}
        }

        with self._thread_lock:
            if not running and caller_id is self._logic_id:
                self.log.debug(f"Adding to data history with settings {settings}")
                self._scan_history.append(data)
                self._shrink_history()
                self._curr_data_per_scan[data.scan_axes] = data
                self._curr_history_index = len(self._scan_history) - 1
                self.sigHistoryScanDataRestored.emit(data)

    def _shrink_history(self):
        while len(self._scan_history) > self._max_history_length:
            self._scan_history.pop(0)

    def draw_1d_scan_figure(self, scan_data, channel):
        """ Create an XY plot of 1D scan data.

        @return fig: a matplotlib figure object to be saved to file.
        """
        data = scan_data.data[channel]
        axis = scan_data.scan_axes[0]
        scanner_pos = self._scan_logic().scanner_target

        # ToDo: Scale data and axes in a suitable and general way (with utils)

        # Create figure
        fig, ax = plt.subplots()

        # Create image plot
        xy_plot = ax.plot(np.linspace(*scan_data.scan_range[0], scan_data.scan_resolution[0]), data)
        if scan_data.axes_units[axis]:
            x_label = '{0} position ({1})'.format(axis, scan_data.axes_units[axis])
        else:
            x_label = '{0} position'.format(axis)
        if scan_data.channel_units[channel]:
            y_label = '{0} ({1})'.format(channel, scan_data.channel_units[channel])
        else:
            y_label = '{0}'.format(channel)

        # ax.set_aspect(1)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.spines['bottom'].set_position(('outward', 10))
        ax.spines['left'].set_position(('outward', 10))
        # ax.spines['top'].set_visible(False)
        # ax.spines['right'].set_visible(False)
        # ax.get_xaxis().tick_bottom()
        # ax.get_yaxis().tick_left()

        # draw the scanner position if defined
        # ToDo: Check if scanner position is within image boundaries. Don't draw if not the case.
        trans_xmark = mpl.transforms.blended_transform_factory(ax.transData, ax.transAxes)
        ax.annotate('',
                    xy=(scanner_pos[axis], 0),
                    xytext=(scanner_pos[axis], -0.01),
                    xycoords=trans_xmark,
                    arrowprops={'facecolor': '#17becf', 'shrink': 0.05})
        return fig

    @QtCore.Slot(object, object)
    def save_scan(self, scan_data, color_range=None):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.error('Unable to save 2D scan. Saving still in progress...')
                return

            if scan_data is None:
                raise ValueError('Unable to save 2D scan. No data available.')

            self.sigSaveStateChanged.emit(True)
            self.module_state.lock()
            try:
                ds = TextDataStorage(root_dir=self.module_default_data_dir)
                timestamp = datetime.datetime.now()

                # ToDo: Add meaningful metadata if missing:
                parameters = {}
                for range, resolution, unit, axis in zip(scan_data.scan_range,
                                      scan_data.scan_resolution,
                                      scan_data.axes_units.values(),
                                      scan_data.scan_axes):

                    parameters[f"{axis} axis name"] = axis
                    parameters[f"{axis} axis unit"] = unit
                    parameters[f"{axis} scan range"] = range
                    parameters[f"{axis} axis resolution"] = resolution
                    parameters[f"{axis} axis min"] = range[0]
                    parameters[f"{axis} axis max"] = range[1]

                parameters["pixel frequency"] = scan_data.scan_frequency
                parameters[f"scanner target at start"] = scan_data.scanner_target_at_start

                # add meta data for axes in full target, but not scan axes
                if scan_data.scanner_target_at_start:
                    for new_ax in scan_data.scanner_target_at_start.keys():
                        if new_ax not in scan_data.scan_axes:
                            ax_info = self._scan_logic().scanner_constraints.axes[new_ax]
                            ax_name = ax_info.name
                            ax_unit = ax_info.unit
                            parameters[f"{new_ax} axis name"] = ax_name
                            parameters[f"{new_ax} axis unit"] = ax_unit

                # Save data and thumbnail to file
                for channel, data in scan_data.data.items():
                    # data
                    # nametag = '{0}_{1}{2}_image_scan'.format(channel, *scan_data.scan_axes)
                    file_path, _, _ = ds.save_data(data,
                                                   metadata=parameters,
                                                   nametag='test',
                                                   timestamp=timestamp,
                                                   column_headers='Image (columns is X, rows is Y)')
                    # thumbnail
                    self.log.info(f'scan data axes {scan_data.scan_axes}')
                    if len(scan_data.scan_axes) == 1:
                        self.log.info('save 1 d figure')
                        self.draw_1d_scan_figure(scan_data, channel)

                        self.log.debug(f'Scan image saved: {file_path}')
                    elif len(scan_data.scan_axes) == 2:
                        figure = self.draw_2d_scan_figure(scan_data, channel, cbar_range=color_range)
                        ds.save_thumbnail(figure, file_path=file_path.rsplit('.', 1)[0])
                        self.log.debug(f'Scan image saved: {file_path}')
                    else:
                        self.log.warning('No figure saved for data with more than 2 dimensions.')

            finally:
                self.module_state.unlock()
                self.sigSaveStateChanged.emit(False)
            return

    def draw_2d_scan_figure(self, scan_data, channel, cbar_range=None):
        """ Create a 2-D color map figure of the scan image.

        @return fig: a matplotlib figure object to be saved to file.
        """
        image_arr = scan_data.data[channel]
        scan_axes = scan_data.scan_axes
        scanner_pos = self._scan_logic().scanner_target


        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = (image_arr.min(), image_arr.max())

        # ToDo: Scale data and axes in a suitable and general way (with utils)

        # Create figure
        fig, ax = plt.subplots()

        # Create image plot
        scan_range_x = (scan_data.scan_range[0][1], scan_data.scan_range[0][0])
        scan_range_y =  (scan_data.scan_range[1][1], scan_data.scan_range[1][0])
        si_prefix_x = ScaledFloat(scan_range_x[1]-scan_range_x[0]).scale
        si_factor_x = ScaledFloat(scan_range_x[1]-scan_range_x[0]).scale_val
        si_prefix_y = ScaledFloat(scan_range_y[1]-scan_range_y[0]).scale
        si_factor_y = ScaledFloat(scan_range_y[1]-scan_range_y[0]).scale_val

        cfimage = ax.imshow(image_arr.transpose(),
                            cmap='inferno',  # FIXME: reference the right place in qudi
                            origin='lower',
                            vmin=cbar_range[0],
                            vmax=cbar_range[1],
                            interpolation='none',
                            extent=(*np.asarray(scan_data.scan_range[0])*1/si_factor_x,
                                    *np.asarray(scan_data.scan_range[1])*1/si_factor_y))

        ax.set_aspect(1)
        ax.set_xlabel(scan_axes[0] + f' position ({si_prefix_x}{scan_data.axes_units[scan_axes[0]]})')
        ax.set_ylabel(scan_axes[1] + f' position ({si_prefix_y}{scan_data.axes_units[scan_axes[1]]})')
        ax.spines['bottom'].set_position(('outward', 10))
        ax.spines['left'].set_position(('outward', 10))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()


        pos_x, pos_y = scanner_pos[scan_axes[0]], scanner_pos[scan_axes[1]]

        # draw the scanner position if defined and in range
        if pos_x > np.min(scan_range_x) and pos_y < np.max(scan_range_y) \
            and pos_y > np.min(scan_range_y) and pos_y < np.max(scan_range_y):
            trans_xmark = mpl.transforms.blended_transform_factory(ax.transData, ax.transAxes)
            trans_ymark = mpl.transforms.blended_transform_factory(ax.transAxes, ax.transData)
            ax.annotate('',
                        xy=np.asarray([pos_x, 0])/si_factor_x,
                        xytext=(pos_x/si_factor_x, -0.01),
                        xycoords=trans_xmark,
                        arrowprops={'facecolor': '#17becf', 'shrink': 0.05})
            ax.annotate('',
                        xy=np.asarray([0, pos_y])/si_factor_y,
                        xytext=(-0.01, pos_y/si_factor_y),
                        xycoords=trans_ymark,
                        arrowprops={'facecolor': '#17becf', 'shrink': 0.05})

        metainfo_str = self._pretty_print_metainfo(scan_axes, scan_data, scanner_pos)
        if metainfo_str:
            ax.annotate(metainfo_str,
                        xy=(.58, .0), xycoords='figure fraction',
                        horizontalalignment='right', verticalalignment='bottom',
                        fontsize=7, color='grey')

        # Draw the colorbar
        cbar = plt.colorbar(cfimage, shrink=0.8)  #, fraction=0.046, pad=0.08, shrink=0.75)
        if scan_data.channel_units[channel]:
            cbar.set_label('{0} ({1})'.format(channel, scan_data.channel_units[channel]))
        else:
            cbar.set_label('{0}'.format(channel))

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which=u'both', length=0)
        return fig

    def _pretty_print_metainfo(self, scan_axes, scan_data, scanner_pos):
        metainfo_str = ""

        # annotate scanner position
        metainfo_str = "Scanner target:\n"
        for axis in scan_axes:
            val = scanner_pos[axis]
            unit = scan_data.axes_units[axis]
            metainfo_str += f"{axis}: {ScaledFloat(val):.3r}{unit}\n"

        # annotate the (all axes) scanner start target
        if scan_data.scanner_target_at_start:
            target_str = ""
            for (target_ax, target_val) in scan_data.scanner_target_at_start.items():
                if target_ax not in scan_axes:
                    ax_info = self._scan_logic().scanner_constraints.axes[target_ax]
                    unit = ax_info.unit
                    target_str += f"{target_ax}: {ScaledFloat(target_val):.3r}{unit}\n"
            if target_str:
                metainfo_str += "Scan start at:\n"
                metainfo_str += target_str

        return metainfo_str

