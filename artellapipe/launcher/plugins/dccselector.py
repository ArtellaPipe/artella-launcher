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
import sys
import time
import json
import shutil
import random
import logging
import argparse
import importlib
import traceback
from distutils import util

from Qt.QtCore import *
from Qt.QtWidgets import *

from tpPyUtils import folder as folder_utils, path as path_utils

from tpQtLib.core import base, qtutils
from tpQtLib.widgets import grid, splitters

from artellapipe.launcher.core import defines, plugin, updater, config
from artellapipe.core import artellalib
from artellapipe.utils import exceptions, resource

LOGGER = logging.getLogger()


class DccData(object):
    def __init__(self, name, icon, enabled, default_version, supported_versions,
                 installation_paths, departments, plugins, launch_fn=None):
        super(DccData, self).__init__()

        self.name = name
        self.icon = icon
        self.enabled = enabled
        self.default_version = default_version
        self.supported_versions = supported_versions
        self.installation_paths = installation_paths
        self.departments = departments
        self.plugins = plugins
        self.launch_fn = launch_fn

    def __str__(self):
        msg = super(DccData, self).__str__()

        msg += '\tName: {}\n'.format(self.name)
        msg += '\tIcon: {}\n'.format(self.icon)
        msg += '\tEnabled: {}\n'.format(self.enabled)
        msg += '\tDefault Version: {}\n'.format(self.default_version)
        msg += '\tSupported Versions: {}\n'.format(self.supported_versions)
        msg += '\tInstallation Paths: {}\n'.format(self.installation_paths)
        msg += '\tDepartments: {}\n'.format(self.departments)
        msg += '\tPlugins: {}\n'.format(self.plugins)
        msg += '\tLaunch Function: {}\n'.format(self.launch_fn)

        return msg


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


class DCCSelector(plugin.ArtellaLauncherPlugin, object):

    LABEL = 'DCC Launcher'
    ICON = 'launcher'
    dccSelected = Signal(str, str)
    UPDATER_CLASS = updater.ArtellaUpdater

    COLUMNS_COUNT = 4

    def __init__(self, project, parent=None):

        self._dccs = dict()
        self._splash = None
        self._updater = None
        self._departments = dict()
        self._selected_dcc = None
        self._selected_version = None

        super(DCCSelector, self).__init__(project=project, parent=parent)

        self._updater = self.UPDATER_CLASS(project=self.project, dccselector=self)

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
    def dccs(self):
        """
        Returns dict of current DCCs data
        :return: dict
        """

        return self._dccs

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

    @property
    def updater(self):
        """
        Retunrs the updater used by Artella Luancher
        :return: ArtellaUpdater
        """

        return self._updater

    def ui(self):
        super(DCCSelector, self).ui()

        self._departments_tab = QTabWidget()
        self.main_layout.addWidget(self._departments_tab)
        self.main_layout.addLayout(splitters.SplitterLayout())
        self.add_department('All')

        LOGGER.debug('DCCs found: {}'.format(self._dccs))

        if self._dccs:
            for dcc_name, dcc_data in self._dccs.items():
                LOGGER.debug('DCC: {} | {}'.format(dcc_name, dcc_data))
                if not dcc_data.enabled:
                    continue
                if not dcc_data.installation_paths:
                    LOGGER.warning('No installed versions found for DCC: {}'.format(dcc_name))
                    continue
                dcc_departments = ['All']
                dcc_departments.extend(dcc_data.departments)
                for department in dcc_departments:
                    self.add_department(department)
                    dcc_btn = DCCButton(dcc=dcc_data)
                    dcc_btn.clicked.connect(self._on_dcc_selected)
                    self.add_dcc_to_department(department, dcc_btn)

        search_folder_icon = resource.ResourceManager().icon('search_folder')
        uninstall_icon = resource.ResourceManager().icon('uninstall')
        extra_buttons_lyt = QHBoxLayout()
        extra_buttons_lyt.setContentsMargins(2, 2, 2, 2)
        extra_buttons_lyt.setSpacing(5)
        self.main_layout.addLayout(extra_buttons_lyt)
        extra_buttons_lyt.addItem(QSpacerItem(10, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.open_folder_btn = QPushButton('Open Install folder')
        self.open_folder_btn.setIcon(search_folder_icon)
        self.open_folder_btn.setMaximumWidth(140)
        self.open_folder_btn.setMinimumWidth(140)
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

    def init_config(self):
        mod_name = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
        mod_folder = os.path.dirname(os.path.abspath(__file__))
        plugin_config = os.path.join(mod_folder, mod_name + '.json')
        if os.path.isfile(plugin_config):
            self.load_dccs(plugin_config)

    def get_enabled_dccs(self):
        """
        Returns a list with all enabled DCCs
        :return: list(str)
        """

        return [dcc_name for dcc_name, dcc_data in self._dccs.items() if dcc_data.enabled]

    def get_installation_path(self):
        """
        Returns tools installation path
        :return: str
        """

        return self._updater.get_installation_path()

    def set_installation_path(self):
        """
        Sets tools installation path
        :return: str
        """

        return self._updater.set_installation_path()

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

    def load_dccs(self, config_file):
        """
        Loads DCCs from given configuration file
        :param config_file: str
        """

        with open(config_file, 'r') as f:
            plugin_config_data = json.load(f)
        if not plugin_config_data:
            return

        dccs = plugin_config_data.get(defines.LAUNCHER_DCCS_ATTRIBUTE_NAME, dict())
        for dcc_name, dcc_data in dccs.items():
            dcc_icon = dcc_data.get(defines.LAUNCHER_DCC_ICON_ATTRIBUTE_NAME, None)
            dcc_enabled = bool(util.strtobool(dcc_data.get(defines.LAUNCHER_DCC_ENABLED_ATTRIBUTE_NAME, False)))
            default_version = dcc_data.get(defines.LAUNCHER_DCC_DEFAULT_VERSION_ATTRIBUTE_NAME, None)
            supported_versions = dcc_data.get(defines.LAUNCHER_DCC_SUPPORTED_VERSIONS_ATTRIBUTE_NAME, list())
            departments = dcc_data.get(defines.LAUNCHER_DCC_DEPARTMENTS_ATTRIBUTE_NAME, list())
            plugins = dcc_data.get(defines.LAUNCHER_DCC_PLUGINS_ATTRIBUTE_NAME, list())
            self._dccs[dcc_name] = DccData(
                name=dcc_name,
                icon=dcc_icon,
                enabled=dcc_enabled,
                default_version=default_version,
                supported_versions=supported_versions,
                installation_paths=list(),
                departments=departments,
                plugins=plugins
            )

        if not self._dccs:
            LOGGER.warning('No DCCs enabled!')
            return

        for dcc_name, dcc_data in self._dccs.items():
            if dcc_data.enabled and not dcc_data.supported_versions:
                LOGGER.warning('{0} DCC enabled but no supported versions found in launcher settings. '
                               '{0} DCC has been disabled!'.format(dcc_name.title()))

            try:
                dcc_module = importlib.import_module(
                    'artellapipe.launcher.dccs.{}dcc'.format(dcc_name.lower().replace(' ', '')))
            except ImportError:
                LOGGER.warning('DCC Python module {}dcc not found!'.format(dcc_name.lower().replace(' ', '')))
                continue

            if not dcc_data.enabled:
                continue

            fn_name = 'get_installation_paths'
            fn_launch = 'launch'
            if not hasattr(dcc_module, fn_name):
                continue

            dcc_installation_paths = getattr(dcc_module, fn_name)(dcc_data.supported_versions)
            dcc_data.installation_paths = dcc_installation_paths

            if hasattr(dcc_module, fn_launch):
                dcc_data.launch_fn = getattr(dcc_module, fn_launch)
            else:
                LOGGER.warning('DCC {} has not launch function implemented. Disabling it ...'.format(dcc_data.name))
                dcc_data.enabled = False

    def add_dcc_to_department(self, department_name, dcc_button):
        if department_name not in self._departments:
            department_widget = self.add_department(department_name)
        else:
            department_widget = self._departments[department_name]

        row, col = department_widget.first_empty_cell()
        department_widget.addWidget(row, col, dcc_button)
        department_widget.resizeRowsToContents()

    def _get_splash_pixmap(self):
        """
        Returns pixmap to be used as splash background
        :return: Pixmap
        """

        splash_path = resource.ResourceManager().get('images', 'splash.png', key='project')
        if not os.path.isfile(splash_path):
            splash_dir = os.path.dirname(splash_path)
            splash_files = [f for f in os.listdir(splash_dir) if
                            f.startswith('splash') and os.path.isfile(os.path.join(splash_dir, f))]
            if splash_files:
                splash_index = random.randint(0, len(splash_files) - 1)
                splash_name, splash_extension = os.path.splitext(splash_files[splash_index])
                splash_pixmap = resource.ResourceManager().pixmap(
                    splash_name, extension=splash_extension[1:], key='project')
            else:
                splash_pixmap = resource.ResourceManager().pixmap('splash')
        else:
            splash_pixmap = resource.ResourceManager().pixmap('splash')

        return splash_pixmap.scaled(QSize(800, 270))

    def _setup_splash(self, dcc_name):
        """
        Internal function that is used to setup launch splash depending on the selected DCC
        :param dcc_name: str
        """

        splash_pixmap = self._get_splash_pixmap()

        self._splash = QSplashScreen(splash_pixmap)
        # self._splash.setFixedSize(QSize(800, 270))
        self._splash.setWindowFlags(Qt.FramelessWindowHint)
        self._splash.setEnabled(True)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 2, 5, 2)
        self.main_layout.setSpacing(2)
        self.main_layout.setAlignment(Qt.AlignBottom)

        self._splash.setLayout(self.main_layout)
        progress_colors = self._updater.progress_colors
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar {border: 0px solid grey; border-radius:4px; padding:0px} "
            "QProgressBar::chunk {background: qlineargradient(x1: 0, y1: 1, x2: 1, y2: 1, stop: 0 rgb(" + str(
                progress_colors[0]) + "), stop: 1 rgb(" + str(progress_colors[1]) + ")); }")
        self.main_layout.addWidget(self.progress_bar)
        self.progress_bar.setMaximum(6)
        self.progress_bar.setTextVisible(False)

        self._progress_text = QLabel('Loading {} Tools ...'.format(self._project.name.title()))
        self._progress_text.setAlignment(Qt.AlignCenter)
        self._progress_text.setStyleSheet("QLabel { background-color : rgba(0, 0, 0, 180); color : white; }")
        font = self._progress_text.font()
        font.setPointSize(10)
        self._progress_text.setFont(font)
        self.main_layout.addWidget(self._progress_text)

        self.main_layout.addItem(QSpacerItem(0, 20))

        artella_icon = resource.ResourceManager().icon('artella')
        artella_lbl = QLabel()
        artella_lbl.setFixedSize(QSize(52, 52))
        artella_lbl.setParent(self._splash)
        artella_lbl.move(self._splash.width() - artella_lbl.width(), 0)
        artella_lbl.setPixmap(artella_icon.pixmap(artella_icon.actualSize(QSize(48, 48))))

        dcc_icon = resource.ResourceManager().icon(dcc_name.lower())
        dcc_lbl = QLabel()
        dcc_lbl.setFixedSize(QSize(52, 52))
        dcc_lbl.setParent(self._splash)
        dcc_lbl.move(self._splash.width() - dcc_lbl.width(), 52)
        dcc_lbl.setPixmap(dcc_icon.pixmap(dcc_icon.actualSize(QSize(48, 48))))

        console_icon = resource.ResourceManager().icon('console')
        console_btn = QPushButton('')
        console_btn.setFixedSize(QSize(42, 42))
        console_btn.setIconSize(QSize(38, 38))
        console_btn.setParent(self._splash)
        console_btn.move(5, 5)
        console_btn.setFlat(True)
        console_btn.setIcon(console_icon)
        # console_btn.clicked.connect(self._on_toggle_console)

        self._splash.show()
        self._splash.raise_()

    def _set_text(self, msg):
        """
        Internal function that sets given text
        :param msg: str
        """

        self._progress_text.setText(msg)
        self._updater.console.write('> {}'.format(msg))
        QApplication.instance().processEvents()

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
                        self, '{} Tools uninstalled'.format(project_name),
                        '{} Tools uninstalled successfully!'.format(project_name))
                except Exception as e:
                    qtutils.show_error(
                        self, 'Error during {} Tools uninstall process'.format(project_name),
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
                self, 'Uninstalling {} Tools'.format(project_name),
                'Are you sure you want to uninstall {} Tools?'.format(project_name))
            if res == QMessageBox.Yes:
                qtutils.show_warning(
                    self, 'Important',
                    'You will need to remove following folders manually:\n\n{}'.format('\n\t'.join(dirs_to_remove)))
                self.launcher.config.setValue(self.launcher.updater.envvar_name, None)
                qtutils.show_info(
                    self, '{} Tools uninstalled'.format(project_name),
                    '{} Tools uninstalled successfully!'.format(project_name))
        else:
            self.show_warning_message('{} tools are not installed! Launch any DCC first!'.format(self.launcher.name))

    def _on_dcc_selected(self, selected_dcc, selected_version):
        """
        Internal callback function that is called when the user selects a DCC to launch in DCCSelector window
        :param selected_dcc: str
        """

        self._selected_dcc = selected_dcc
        self._selected_version = selected_version
        self.dccSelected.emit(self._selected_dcc, self._selected_version)

        try:
            if not selected_dcc:
                qtutils.show_warning(
                    None, 'DCC installations not found',
                    '{} Launcher cannot found any DCC installed in your computer.'.format(self.name))
                sys.exit()

            if selected_dcc not in self._dccs:
                qtutils.show_warning(
                    None, '{} not found in your computer'.format(selected_dcc.title()),
                    '{} Launcher cannot launch {} because no version is installed in your computer.'.format(
                        self.name, selected_dcc.title()))
                sys.exit()

            installation_paths = self._dccs[selected_dcc].installation_paths
            if not installation_paths:
                return

            if selected_version not in installation_paths:
                qtutils.show_warning(
                    None, '{} {} installation path not found'.format(selected_dcc.title(), selected_version),
                    '{} Launcher cannot launch {} {} because it is not installed in your computer.'.format(
                        self.name, selected_dcc.title(), selected_version))
                return

            installation_path = installation_paths[selected_version]

            self._setup_splash(selected_dcc)

            self._updater.console.move(self._splash.geometry().center())
            # self._updater.console.move(300, 405)
            self._updater.console.show()

            self._progress_text.setText('Creating {} Launcher Configuration ...'.format(self._project.name.title()))
            self._updater.console.write('> Creating {} Launcher Configuration ...'.format(self._project.name.title()))
            QApplication.instance().processEvents()
            cfg = config.create_config(
                launcher_name=self._project.get_clean_name(),
                console=self._updater.console, window=None, dcc_install_path=installation_path)
            if not cfg:
                self._splash.close()
                self._updater.close()
                qtutils.show_warning(
                    None, '{} location not found'.format(selected_dcc.title()),
                    '{} Launcher cannot launch {}!'.format(self._project.name.title(), selected_dcc.title()))
                return
            QApplication.instance().processEvents()
            self._config = cfg

            parser = argparse.ArgumentParser(
                description='{} Launcher allows to setup a custom initialization for DCCs. '
                            'This allows to setup specific paths in an easy way.'.format(self._project.name.title())
            )
            parser.add_argument(
                '-e', '--edit',
                action='store_true',
                help='Edit configuration file'
            )

            args = parser.parse_args()
            if args.edit:
                self._updater.write(
                    'Opening {} Launcher Configuration file to edit ...'.format(self._project.name.title()))
                return cfg.edit()

            exec_ = cfg.value('executable')

            self.progress_bar.setValue(1)
            QApplication.instance().processEvents()
            time.sleep(1)

            self._set_text('Updating Artella Paths ...')
            artellalib.update_artella_paths()

            self._set_text('Closing Artella App instances ...')
            valid_close = artellalib.close_all_artella_app_processes(console=self._updater.console)
            self.progress_bar.setValue(2)
            QApplication.instance().processEvents()
            time.sleep(1)

            if valid_close:
                self._set_text('Launching Artella App ...')
                artellalib.launch_artella_app()
                self.progress_bar.setValue(3)
                QApplication.instance().processEvents()
                time.sleep(1)

            install_path = cfg.value(self._updater.envvar_name)
            if not install_path or not os.path.exists(install_path):
                self._set_text(
                    'Current installation path does not exists: {}. Reinstalling {} Tools ...'.format(
                        install_path, self._project.name.title()))
                install_path = self.set_installation_path()
                if not install_path:
                    sys.exit()

                install_path = path_utils.clean_path(os.path.abspath(install_path))
                id_path = path_utils.clean_path(self._project.id_path)
                if id_path in install_path:
                    qtutils.show_warning(
                        None, 'Selected installation folder is not valid!',
                        'Folder {} is not a valid installation folder. '
                        'Please select a folder that is not inside Artella Project folder please!'.format(install_path))
                    sys.exit()

                cfg.setValue(self._updater.envvar_name, path_utils.clean_path(os.path.abspath(install_path)))

            self.progress_bar.setValue(4)
            self._set_text('Setting {} environment variables ...'.format(selected_dcc.title()))

            env_var = self._updater.envvar_name
            folders_to_register = self.project.get_folders_to_register(full_path=False)
            if folders_to_register:
                if os.environ.get('PYTHONPATH'):
                    os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ';' + cfg.value(env_var)
                    for p in folders_to_register:
                        p = path_utils.clean_path(os.path.join(install_path, p))
                        LOGGER.debug('Adding path to PYTHONPATH: {}'.format(p))
                        os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ';' + p
                else:
                    os.environ['PYTHONPATH'] = cfg.value(env_var)
                    for p in folders_to_register:
                        p = path_utils.clean_path(os.path.join(install_path, p))
                        LOGGER.debug('Adding path to PYTHONPATH: {}'.format(p))
                        os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ';' + p

            self.progress_bar.setValue(5)
            self._set_text('Checking {} tools version ...'.format(self._project.name.title()))
            self.main_layout.addWidget(self._updater)
            self._updater.show()
            self._updater.raise_()
            QApplication.instance().processEvents()
        #     need_to_update = self._updater.check_tools_version()
        #     os.environ[self._project.get_clean_name()+'_show'] = 'show'
        #
        #     self._updater.close()
        #     self._updater.progress_bar.setValue(0)
        #     QApplication.instance().processEvents()
        #     time.sleep(1)
        #
        #     if need_to_update:
        #         self.progress_bar.setValue(6)
        #         self._set_text('Updating {} Tools ...'.format(self._project.name.title()))
        #         self._updater.show()
        #         QApplication.instance().processEvents()
        #         self._updater.update_tools()
        #         time.sleep(1)
        #         self._updater.close()
        #         self._updater.progress_bar.setValue(0)
        #         QApplication.instance().processEvents()
        #
        #     self._updater.console.write_ok('{} Tools setup completed, launching: {}'.format(self._
        #     project.name.title(), exec_))
        #     QApplication.instance().processEvents()
        #
        #     # We need to import this here because this path maybe is not available until we update Artella paths
        #     try:
        #         import spigot
        #     except ImportError:
        #         self._updater.console.write_error(
        #         'Impossible to import Artella Python modules!
        #         Maybe Artella is not installed properly. Contact TD please!')
        #         return
        #
        #     launch_fn = self._dccs[selected_dcc].launch_fn
        #     if not launch_fn:
        #         self._updater.console.write_error(
        #         'Selected DCC: {} has no launch function!'.format(selected_dcc.name))
        #         QApplication.instance().processEvents()
        #         return
        except Exception as e:
            self._updater.close()
            self._splash.close()
            raise exceptions.ArtellaPipeException(self._project, msg=e)

        # self._splash.close()
        # self._updater.console.close()
        #
        # time.sleep(1)
        #
        # # Search for userSetup.py file
        # setup_path = None
        # for dir, _, files in os.walk(install_path):
        #     if setup_path:
        #         break
        #     for f in files:
        #         if f.endswith('userSetup.py'):
        #             setup_path = path_utils.clean_path(os.path.join(dir, f))
        #             break
        #
        # launch_fn(exec_=exec_, setup_path=setup_path)
