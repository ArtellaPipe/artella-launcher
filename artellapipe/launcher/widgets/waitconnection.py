#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Wait Connection for Artella Enterprise projects
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import time
import logging
import traceback

from Qt.QtCore import *

import tpDcc
from tpDcc.libs.python import color
from tpDcc.libs.qt.core import base
from tpDcc.libs.qt.widgets import layouts, label, dividers, loading, buttons, message

import artellapipe
from artellapipe.libs.artella.core import artellalib


LOGGER = logging.getLogger('artellapipe-launcher')


class WaitConnectionWidget(base.BaseWidget, object):

    connectionEstablished = Signal()
    listenForConnections = Signal()

    def __init__(self, parent=None):
        super(WaitConnectionWidget, self).__init__(parent=parent)

        self._check_thread = None
        self._check_worker = None

    def get_main_layout(self):
        main_layout = layouts.VerticalLayout(spacing=5, margins=(5, 5, 5, 5))
        return main_layout

    def closeEvent(self, *args, **kwargs):
        if self._check_thread:
            self._check_worker.stop()
            self._check_thread.deleteLater()

    def ui(self):
        super(WaitConnectionWidget, self).ui()

        progress_color = None
        progress_msg = 'Waiting to connect to Artella server ...'
        if hasattr(artellapipe, 'project') and artellapipe.project:
            progress_color_str_list = artellapipe.project.progress_bar.color0.split(',')
            progress_color_list = [int(color_value) for color_value in progress_color_str_list]
            progress_color = color.rgb_to_hex(progress_color_list)
            if not progress_color.startswith('#'):
                progress_color = '#{}'.format(progress_color)
            progress_msg = 'Waiting to connect to {} Artella project server'.format(
                artellapipe.project.get_clean_name().title())

        progress_layout = layouts.HorizontalLayout()
        self._progress = loading.CircleLoading(size=150, color=progress_color, parent=self)
        progress_layout.addStretch()
        progress_layout.addWidget(self._progress)
        progress_layout.addStretch()
        self._progress_label = label.BaseLabel(progress_msg)
        self._progress_label.setAlignment(Qt.AlignCenter)
        self._login_button = buttons.BaseButton('Login')
        self._login_button.setIcon(tpDcc.ResourcesMgr().icon('artella'))

        self.main_layout.addStretch()
        self.main_layout.addLayout(progress_layout)
        self.main_layout.addWidget(self._progress_label)
        self.main_layout.addStretch()
        self.main_layout.addWidget(dividers.Divider())
        self.main_layout.addStretch()
        self.main_layout.addWidget(self._login_button)
        self.main_layout.addStretch()

    def setup_signals(self):
        self._login_button.clicked.connect(self._on_login)

    def listen_for_connections(self):

        if not self._check_thread:
            self._check_thread = QThread(self)
            self._check_worker = CheckStatusWorker()
            self._check_worker.moveToThread(self._check_thread)
            self._check_worker.connectionEstablished.connect(self._on_connection_established)
            self._check_thread.start()
            self.listenForConnections.connect(self._check_worker.run)
            self.listenForConnections.emit()
        else:
            self._check_worker.resume()

    def _on_login(self):
        if not hasattr(artellapipe, 'project') or not artellapipe.project:
            msg = 'Impossible to login because no Artella project is defined'
            message.PopupMessage.error(msg, parent=self, duration=5, closable=True)
            return

        artellapipe.project.open_artella_project_url()

    def _on_connection_established(self, error_msg):
        if error_msg:
            LOGGER.error(error_msg)
            return

        self.connectionEstablished.emit()


class CheckStatusWorker(QObject, object):

    connectionEstablished = Signal(str)

    def __init__(self):
        super(CheckStatusWorker, self).__init__()

        self._stop = False

    def stop(self):
        self._stop = True

    def resume(self):
        self._stop = False
        self.run()

    def run(self):

        project_found = False
        try:
            while not project_found:
                if self._stop:
                    break

                client = artellalib.get_artella_client()
                client.update_remotes_sessions(show_dialogs=False)
                remote_projects = client.get_remote_projects(force_update=True) or dict()
                if not remote_projects or (not hasattr(artellapipe, 'project') or not artellapipe.project):
                    time.sleep(2)
                    continue
                current_project_id = artellapipe.project.id
                for remote_api, project_dict in remote_projects.items():
                    if project_found:
                        break
                    if not project_dict:
                        continue
                    for project_id, project_data in project_dict.items():
                        if project_id == current_project_id:
                            project_found = True
                            break
                time.sleep(2)
        except Exception:
            self.connectionEstablished.emit(traceback.format_exc())
            return

        self.connectionEstablished.emit('')
