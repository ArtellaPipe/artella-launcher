#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation to create Artella launchers
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import math
import shutil
import traceback
import logging.config

from Qt.QtCore import *
from Qt.QtWidgets import *

from tpPyUtils import folder as folder_utils

from tpQtLib.core import base, qtutils
from tpQtLib.widgets import grid, splitters

import artellapipe.launcher
from artellapipe.utils import resource
from artellapipe.gui import window

logging.config.fileConfig(artellapipe.launcher.get_logging_config(), disable_existing_loggers=False)
logger = logging.getLogger(__name__)
logger.setLevel(artellapipe.launcher.get_logging_level())


class DCCButton(base.BaseWidget, object):

    clicked = Signal(str, str)

    def __init__(self, dcc, parent=None):
        self._dcc = dcc
        super(DCCButton, self).__init__(parent=parent)

    @property
    def name(self):
        """
        Returns the name of the DCC
        :return: str
        """

        return self._name

    def ui(self):
        super(DCCButton, self).ui()

        dcc_name = self._dcc.name.lower().replace(' ', '_')
        dcc_icon = self._dcc.icon
        icon_split = dcc_icon.split('/')
        if len(icon_split) == 1:
            theme = ''
            icon_name = icon_split[0]
        elif len(icon_split) > 1:
            theme = icon_split[0]
            icon_name = icon_split[1]
        else:
            theme = 'color'
            icon_name = dcc_name

        icon_path = resource.ResourceManager().get('icons', theme, '{}.png'.format(icon_name))
        if not os.path.isfile(icon_path):
            icon_path = resource.ResourceManager().get('icons', theme, '{}.png'.format(icon_name))
            if not os.path.isfile(icon_path):
                dcc_icon = resource.ResourceManager().icon('artella')
            else:
                dcc_icon = resource.ResourceManager().icon(icon_name, theme=theme)
        else:
            dcc_icon = resource.ResourceManager().icon(icon_name, theme=theme)

        self._title = QPushButton(self._dcc.name.title())
        self._title.setStyleSheet(
            """
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            """
        )
        self._title.setFixedHeight(20)

        self.main_layout.addWidget(self._title)
        self._dcc_btn = QPushButton()
        self._dcc_btn.setFixedSize(QSize(100, 100))
        self._dcc_btn.setIconSize(QSize(110, 110))
        self._dcc_btn.setIcon(dcc_icon)
        self._dcc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_layout.addWidget(self._dcc_btn)

        self._version_combo = QComboBox()
        self.main_layout.addWidget(self._version_combo)
        for version in self._dcc.supported_versions:
            self._version_combo.addItem(str(version))

        default_version = self._dcc.default_version
        index = self._version_combo.findText(default_version, Qt.MatchFixedString)
        if index > -1:
            self._version_combo.setCurrentIndex(index)

    def setup_signals(self):
        self._dcc_btn.clicked.connect(self._on_button_clicked)
        self._title.clicked.connect(self._on_button_clicked)

    def _on_button_clicked(self):
        dcc_name = self._dcc.name
        dcc_version = self._version_combo.currentText()
        if not dcc_version:
            dcc_version = self._dcc.default_version
        self.clicked.emit(dcc_name, dcc_version)


class DCCSelector(window.ArtellaWindow, object):

    dccSelected = Signal(str, str)

    COLUMNS_COUNT = 4

    def __init__(self, launcher, parent=None):
        self._launcher = launcher
        self._departments = dict()
        self._selected_dcc = None
        self._selected_version = None

        super(DCCSelector, self).__init__(
            name='DCCSelectorWindow',
            title='DCC Selector',
            size=(310, 600),
            fixed_size=False,
            parent=parent
        )

        selector_icon = self.launcher.icon
        if selector_icon:
            self.setWindowIcon(selector_icon)

        self.setWindowTitle('{} - {}'.format(self.launcher.name, self.launcher.version))

        self._button_settings.setVisible(False)

        self.setMinimumWidth(450)
        total_rows = int(math.ceil(self._departments['All'].count() / self.COLUMNS_COUNT))
        minimum_height = (total_rows * 105) + 275

        self.setMinimumHeight(minimum_height)
        self.setMaximumHeight(minimum_height)

        # self.setFixedWidth(self.sizeHint().width())
        # self.setFixedHeight(self.sizeHint().height())

    def get_main_layout(self):
        """
        Overrides base get_main_layout function
        :return: QLayout
        """

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setAlignment(Qt.AlignTop)
        return main_layout

    @property
    def launcher(self):
        """
        Returns launcher linked to this DCC selector
        :return: ArtellaLauncher
        """

        return self._launcher

    @property
    def selected_dcc(self):
        """
        Returns the selected DCC
        :return: str
        """

        return self._selected_dcc

    @property
    def selected_version(self):
        """
        Returns the selected DCC version
        :return: str
        """

        return self._selected_version

    def ui(self):
        super(DCCSelector, self).ui()

        self._departments_tab = QTabWidget()
        self.main_layout.addWidget(self._departments_tab)
        self.main_layout.addLayout(splitters.SplitterLayout())
        self.add_department('All')

        logger.debug('Using Launcher: {}'.format(self.launcher))
        logger.debug('DCCs found: {}'.format(self.launcher.dccs))

        if self.launcher.dccs:
            for dcc_name, dcc_data in self.launcher.dccs.items():
                logger.debug('DCC: {} | {}'.format(dcc_name, dcc_data))
                if not dcc_data.enabled:
                    continue
                if not dcc_data.installation_paths:
                    logger.warning('No installed versions found for DCC: {}'.format(dcc_name))
                    continue
                dcc_departments = ['All']
                dcc_departments.extend(dcc_data.departments)
                for department in dcc_departments:
                    self.add_department(department)
                    dcc_btn = DCCButton(dcc=dcc_data)
                    dcc_btn.clicked.connect(self._on_dcc_selected)
                    self.add_dcc_to_department(department, dcc_btn)

        search_folder_icon = resource.icon('search_folder')
        uninstall_icon = resource.icon('uninstall')
        extra_buttons_lyt = QHBoxLayout()
        extra_buttons_lyt.setContentsMargins(2, 2, 2, 2)
        extra_buttons_lyt.setSpacing(5)
        self.main_layout.addLayout(extra_buttons_lyt)
        extra_buttons_lyt.addItem(QSpacerItem(10, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.open_folder_btn = QPushButton('Open Install folder')
        self.open_folder_btn.setIcon(search_folder_icon)
        self.open_folder_btn.setMaximumWidth(120)
        self.open_folder_btn.setMinimumWidth(120)
        self.open_folder_btn.setStyleSheet(
            """
            border-radius: 5px;
            """
        )
        uninstall_layout = QHBoxLayout()
        uninstall_layout.setContentsMargins(0, 0, 0, 0)
        uninstall_layout.setSpacing(1)
        self.uninstall_btn = QPushButton('Uninstall')
        self.uninstall_btn.setIcon(uninstall_icon)
        self.uninstall_btn.setMaximumWidth(80)
        self.uninstall_btn.setMinimumWidth(80)
        self.uninstall_btn.setStyleSheet(
            """
            border-top-left-radius: 5px;
            border-bottom-left-radius: 5px;
            """
        )
        self.force_uninstall_btn = QPushButton('Force')
        self.force_uninstall_btn.setStyleSheet(
            """
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
            """
        )
        self.force_uninstall_btn.setMaximumWidth(45)
        self.force_uninstall_btn.setMinimumWidth(45)
        extra_buttons_lyt.addWidget(self.open_folder_btn)
        extra_buttons_lyt.addLayout(uninstall_layout)
        uninstall_layout.addWidget(self.uninstall_btn)
        uninstall_layout.addWidget(self.force_uninstall_btn)
        extra_buttons_lyt.addItem(QSpacerItem(10, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))

    def setup_signals(self):
        super(DCCSelector, self).setup_signals()

        self.open_folder_btn.clicked.connect(self._on_open_installation_folder)
        self.uninstall_btn.clicked.connect(self._on_uninstall)
        self.force_uninstall_btn.clicked.connect(self._on_force_uninstall)

    def add_department(self, department_name):
        if department_name not in self._departments:
            department_widget = grid.GridWidget()
            department_widget.setColumnCount(self.COLUMNS_COUNT)
            department_widget.setShowGrid(False)
            department_widget.horizontalHeader().hide()
            department_widget.verticalHeader().hide()
            department_widget.resizeRowsToContents()
            department_widget.resizeColumnsToContents()
            department_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
            department_widget.setFocusPolicy(Qt.NoFocus)
            department_widget.setSelectionMode(QAbstractItemView.NoSelection)

            self._departments[department_name] = department_widget
            self._departments_tab.addTab(department_widget, department_name.title())
            return department_widget

        return None

    def add_dcc_to_department(self, department_name, dcc_button):
        if department_name not in self._departments:
            department_widget = self.add_department(department_name)
        else:
            department_widget = self._departments[department_name]

        row, col = department_widget.first_empty_cell()
        department_widget.addWidget(row, col, dcc_button)
        department_widget.resizeRowsToContents()

    def _on_dcc_selected(self, dcc_name, dcc_version):
        """
        Internal callback function that is called when a DCC button is clicked
        :param dcc_name: str
        :param dcc_version: str
        :return: str
        """

        self._selected_dcc = dcc_name
        self._selected_version = dcc_version
        self.close()
        self.dccSelected.emit(self._selected_dcc, self._selected_version)

    def _on_open_installation_folder(self):
        """
        Internal callback function that is called when the user press Open Installation Folder button
        """

        install_path = self.launcher.get_installation_path()
        if install_path and os.path.isdir(install_path) and len(os.listdir(install_path)) != 0:
            folder_utils.open_folder(install_path)
        else:
            self.show_warning_message('{} tools are not installed! Launch any DCC first!'.format(self.launcher.name))

    def _on_uninstall(self):
        """
        Internal callback function that is called when the user press Uninstall button
        Removes environment variable and Tools folder
        :return:
        """

        install_path = self.launcher.get_installation_path()
        if install_path and os.path.isdir(install_path):
            dirs_to_remove = [os.path.join(install_path, self.launcher.project.get_clean_name())]
            project_name = self.launcher.project.name.title()
            res = qtutils.show_question(
                self, 'Uninstalling {} Tools'.format(project_name),
                'Are you sure you want to uninstall {} Tools?\n\nFolder/s that will be removed \n\t{}'.format(
                    project_name, '\n\t'.join(dirs_to_remove)))
            if res == QMessageBox.Yes:
                try:
                    for d in dirs_to_remove:
                        if os.path.isdir(d):
                            shutil.rmtree(d, ignore_errors=True)
                        elif os.path.isfile(d):
                            os.remove(d)
                    self.launcher.config.setValue(self.launcher.updater.envvar_name, None)
                    qtutils.show_info(
                        self,
                        '{} Tools uninstalled'.format(
                            project_name), '{} Tools uninstalled successfully!'.format(project_name))
                except Exception as e:
                    qtutils.show_error(
                        self,
                        'Error during {} Tools uninstall process'.format(project_name),
                        'Error during {} Tools uninstall: {} | {}'.format(project_name, e, traceback.format_exc()))
        else:
            self.show_warning_message('{} tools are not installed! Launch any DCC first!'.format(self.launcher.name))

    def _on_force_uninstall(self):
        """
        Internal callback function that is called when the user press Force button
        Removes environment variable. The user will have to remove installation folder manually
        :return:
        """

        install_path = self.launcher.get_installation_path()
        if install_path and os.path.isdir(install_path):
            dirs_to_remove = [os.path.join(install_path, self.launcher.project.get_clean_name())]
            project_name = self.launcher.project.name.title()
            res = qtutils.show_question(
                self,
                'Uninstalling {} Tools'.format(project_name),
                'Are you sure you want to uninstall {} Tools?'.format(project_name))
            if res == QMessageBox.Yes:
                qtutils.show_warning(
                    self,
                    'Important',
                    'You will need to remove following folders manually:\n\n{}'.format('\n\t'.join(dirs_to_remove)))
                self.launcher.config.setValue(self.launcher.updater.envvar_name, None)
                qtutils.show_info(
                    self,
                    '{} Tools uninstalled'.format(project_name),
                    '{} Tools uninstalled successfully!'.format(project_name))
        else:
            self.show_warning_message('{} tools are not installed! Launch any DCC first!'.format(self.launcher.name))
