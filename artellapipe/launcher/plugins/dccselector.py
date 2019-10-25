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
import random
import logging
import argparse
import importlib
from distutils import util

from Qt.QtCore import *
from Qt.QtWidgets import *

from tpPyUtils import path as path_utils

from tpQtLib.core import base, qtutils
from tpQtLib.widgets import grid


from artellapipe.utils import exceptions, resource
from artellapipe.launcher.core import defines, plugin

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

    COLUMNS_COUNT = 4

    def __init__(self, project, launcher, parent=None):

        self._dccs = dict()
        self._splash = None
        self._departments = dict()
        self._selected_dcc = None
        self._selected_version = None

        super(DCCSelector, self).__init__(project=project, launcher=launcher, parent=parent)

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

    def ui(self):
        super(DCCSelector, self).ui()

        self._departments_tab = QTabWidget()
        self.main_layout.addWidget(self._departments_tab)
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
        splash_dir = os.path.dirname(splash_path)
        splash_files = [f for f in os.listdir(splash_dir) if
                        f.startswith('splash') and os.path.isfile(os.path.join(splash_dir, f))]
        if splash_files or not os.path.isfile(splash_path):
            splash_index = random.randint(0, len(splash_files) - 1)
            splash_name, splash_extension = os.path.splitext(splash_files[splash_index])
            splash_pixmap = resource.ResourceManager().pixmap(
                splash_name, extension=splash_extension[1:], key='project')
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
        progress_colors = (self.project.progress_bar_color0, self.project.progress_bar_color1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar {border: 0px solid grey; border-radius:4px; padding:0px} "
            "QProgressBar::chunk {background: qlineargradient(x1: 0, y1: 1, x2: 1, y2: 1, stop: 0 rgb(" + str(
                progress_colors[0]) + "), stop: 1 rgb(" + str(progress_colors[1]) + ")); }")
        self.main_layout.addWidget(self.progress_bar)
        self.progress_bar.setMaximum(6)
        self.progress_bar.setTextVisible(False)

        self._progress_text = QLabel('Loading {} Tools ...'.format(self.project.name.title()))
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

        self._splash.show()
        self._splash.raise_()

    def _set_text(self, msg):
        """
        Internal function that sets given text
        :param msg: str
        """

        self._progress_text.setText(msg)
        LOGGER.info('> {}'.format(msg))
        QApplication.instance().processEvents()

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

            self._progress_text.setText('Creating {} Launcher Configuration ...'.format(self.project.name.title()))
            LOGGER.info('> Creating {} Launcher Configuration ...'.format(self.project.name.title()))
            QApplication.instance().processEvents()

            parser = argparse.ArgumentParser(
                description='{} Launcher allows to setup a custom initialization for DCCs. '
                            'This allows to setup specific paths in an easy way.'.format(self.project.name.title())
            )
            parser.add_argument(
                '-e', '--edit',
                action='store_true',
                help='Edit configuration file'
            )

            exec_ = os.path.abspath(installation_path)

            self.progress_bar.setValue(1)
            QApplication.instance().processEvents()
            time.sleep(1)

            install_path = self.launcher.install_path
            if not install_path or not os.path.isdir(install_path):
                msg = 'Current installation path does not exists: {}. Aborting DCC launch ...'.format(install_path)
                self._set_text(msg)
                LOGGER.error(msg)
                sys.exit()

            install_path = path_utils.clean_path(os.path.abspath(install_path))
            id_path = path_utils.clean_path(self.project.id_path)
            if id_path in install_path:
                qtutils.show_warning(
                    None, 'Installation folder is not valid!',
                    'Folder {} is not a valid installation folder. '
                    'Install tools in a folder that is not inside Artella Project folder please!'.format(install_path))
                sys.exit()

            self.progress_bar.setValue(4)
            self._set_text('Setting {} environment variables ...'.format(selected_dcc.title()))

            bootstrap_path = None

            # We force the addition of bootstrap and external module
            folders_to_register = list()
            mods_to_register = self.project.modules_to_register
            for mod_name in mods_to_register:
                try:
                    imported_mod = importlib.import_module(
                        '{}.{}'.format(self.project.get_clean_name(), mod_name))
                    if imported_mod:
                        mod_path = os.path.dirname(imported_mod.__file__)
                        if mod_name == 'bootstrap':
                            mod_path = os.path.join(mod_path, self._selected_dcc.lower())
                            if os.path.isdir(mod_path):
                                bootstrap_path = mod_path

                        if os.path.isdir(mod_path):
                            if mod_path not in folders_to_register:
                                folders_to_register.append(mod_path)
                            else:
                                LOGGER.warning(
                                    'Impossible to register Bootstrap Path for Project "{}" and DCC "{}"'.format(
                                        self.project.get_clean_name(), self._selected_dcc))
                except ImportError:
                    continue

            project_folders_to_register = self.project.get_folders_to_register(full_path=False)
            if project_folders_to_register:
                for p in project_folders_to_register:
                    if p not in folders_to_register:
                        folders_to_register.append(p)

            for p in self.launcher.paths_to_register:
                if p not in folders_to_register:
                    folders_to_register.append(p)
                    if self.launcher.dev:
                        for f_name in os.listdir(p):
                            f_path = path_utils.clean_path(os.path.join(p, f_name))
                            if f_path.endswith('-link') and os.path.isfile(f_path):
                                with open(f_path, 'r') as f:
                                    mod_path = str(path_utils.clean_path(f.readline()))
                                    if mod_path and os.path.isdir(mod_path):
                                        folders_to_register.append(mod_path)

            if folders_to_register:

                LOGGER.info("Registering following paths: \n")
                for f in folders_to_register:
                    LOGGER.info(f)

                if os.environ.get('PYTHONPATH'):
                    os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ';' + self.launcher.install_path
                    for p in folders_to_register:
                        p = path_utils.clean_path(os.path.join(install_path, p))
                        LOGGER.debug('Adding path to PYTHONPATH: {}'.format(p))
                        os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ';' + p
                else:
                    os.environ['PYTHONPATH'] = self.launcher.install_path
                    for p in folders_to_register:
                        p = path_utils.clean_path(os.path.join(install_path, p))
                        LOGGER.debug('Adding path to PYTHONPATH: {}'.format(p))
                        os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ';' + p

            self.progress_bar.setValue(5)
            self._set_text('Checking {} tools version ...'.format(self.project.name.title()))

        #     os.environ[self.project.get_clean_name()+'_show'] = 'show'

            time.sleep(1)

            # We need to import this here because this path maybe is not available until we update Artella paths
            try:
                import spigot
            except ImportError:
                LOGGER.error('Impossible to import Artella Python modules! Maybe Artella is not installed properly.')

            launch_fn = self._dccs[selected_dcc].launch_fn
            if not launch_fn:
                LOGGER.error('Selected DCC: {} has no launch function!'.format(selected_dcc.name))
                return
        except Exception as e:
            self._splash.close()
            raise exceptions.ArtellaPipeException(self.project, msg=e)

        self._splash.close()

        time.sleep(1)

        if not bootstrap_path or not os.path.isdir(bootstrap_path):
            QMessageBox.warning(
                None, 'Bootstrap Directory not found!',
                'Bootstrap folder for Project "{}" and DCC "{}" not found. Tools will not load. '
                'Please contact TD!'.format(self.project.get_clean_name, self._selected_dcc))

        launch_fn(exec_=exec_, setup_path=bootstrap_path)

        self.launcher.close()
        QApplication.instance().quit()
