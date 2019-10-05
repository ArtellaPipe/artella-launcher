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
import argparse
import importlib
import traceback
import logging.config
from distutils import util

from Qt.QtCore import *
from Qt.QtWidgets import *

from tpPyUtils import path as path_utils
from tpQtLib.core import qtutils

from artellapipe.utils import resource, exceptions
from artellapipe.core import artellalib

import artellapipe.launcher
from artellapipe.launcher.core import defines, config, updater, dccselector
from artellapipe.launcher.widgets import console

logging.config.fileConfig(artellapipe.launcher.get_logging_config(), disable_existing_loggers=False)
logger = logging.getLogger(__name__)
logger.setLevel(artellapipe.launcher.get_logging_level())


class DccData(object):
    def __init__(self,
                 name,
                 icon,
                 enabled,
                 default_version,
                 supported_versions,
                 installation_paths,
                 departments,
                 plugins,
                 launch_fn=None):
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


class ArtellaLauncher(QObject, object):

    DCC_SELECTOR_CLASS = dccselector.DCCSelector
    UPDATER_CLASS = updater.ArtellaUpdater
    LAUNCHER_CONFIG_PATH = artellapipe.launcher.get_launcher_config_path()

    def __init__(self, project, resource):
        super(ArtellaLauncher, self).__init__()

        self._logger = None
        self._name = None
        self._version = None
        self._config = None
        self._console = None
        self._dccs = dict()
        self._splash = None
        self._updater = None
        self._resource = resource
        self._project = project

        self.init_config()
        self._logger = self.create_logger()[1]

    @property
    def name(self):
        """
        Returns the name of the Artella launcher
        :return: str
        """

        return self._name

    @property
    def version(self):
        """
        Returns the version of the Artella launcher
        :return: str
        """

        return self._version

    @property
    def icon(self):
        """
        Returns the icon associated to this launcher
        :return: str
        """

        return self._resource.icon(self._name.lower().replace(' ', ''), theme=None)

    @property
    def config(self):
        """
        Returns the config associated to this launcher
        :return: ArtellaConfig
        """

        return self._config

    @property
    def resource(self):
        """
        Returns the resource of the Artella launcher
        :return: Resource
        """

        return self._resource

    @property
    def project(self):
        """
        Returns the project of the Artella launcher
        :return: ArtelalProject
        """

        return self._project

    @property
    def dccs(self):
        """
        Returns dict of current DCCs data
        :return: dict
        """

        return self._dccs

    @property
    def logger(self):
        """
        Returns the logger used by the Artella launcher
        :return: Logger
        """

        return self._logger

    @property
    def console(self):
        """
        Returns the console used by Artella launcher
        """

        return self._console

    @property
    def updater(self):
        """
        Retunrs the updater used by Artella Luancher
        :return: ArtellaUpdater
        """

        return self._updater

    def init(self):
        """
        Function that initializes Artella launcher
        """

        self._console = console.ArtellaLauncherConsole(logger=self.logger)
        self._console.setWindowFlags(Qt.FramelessWindowHint)
        self._config = config.create_config(
            launcher_name=self.name.replace(' ', ''), console=None, window=self, dcc_install_path=None)
        self._updater = self.UPDATER_CLASS(project=self.project, launcher=self)

        dcc_selector = self.DCC_SELECTOR_CLASS(launcher=self)
        dcc_selector.setWindowModality(Qt.ApplicationModal)
        dcc_selector.show()
        dcc_selector.dccSelected.connect(self._on_dcc_selected)

    def create_logger(self):
        """
        Creates and initializes Artella launcher logger
        """

        from tpPyUtils import log as log_utils

        log_path = self.get_data_path()
        if not os.path.exists(log_path):
            raise RuntimeError('{} Log Path {} does not exists!'.format(self.name, log_path))

        log = log_utils.create_logger(logger_name=self.get_clean_name(), logger_path=log_path)
        logger = log.logger

        if '{}_DEV'.format(self.get_clean_name().upper()) in os.environ and os.environ.get(
                '{}_DEV'.format(self.get_clean_name().upper())) in ['True', 'true']:
            logger.setLevel(log_utils.LoggerLevel.DEBUG)
        else:
            logger.setLevel(log_utils.LoggerLevel.WARNING)

        return log, logger

    def init_config(self):
        """
        Function that reads launcher configuration and initializes launcher variables properly
        This function can be extended in new launchers
        """

        if not self.LAUNCHER_CONFIG_PATH or not os.path.isfile(self.LAUNCHER_CONFIG_PATH):
            logger.error(
                'Launcher Configuration File for Artella Launcher not found! {}'.format(self.LAUNCHER_CONFIG_PATH))
            return

        with open(self.LAUNCHER_CONFIG_PATH, 'r') as f:
            launcher_config_data = json.load(f)
        if not launcher_config_data:
            logger.error(
                'Launcher Configuration File for Artella Project is empty! {}'.format(self.LAUNCHER_CONFIG_PATH))
            return

        self._name = launcher_config_data.get(
            defines.ARTELLA_CONFIG_LAUNCHER_NAME, defines.ARTELLA_DEFAULT_LAUNCHER_NAME)
        self._version = launcher_config_data.get(defines.ARTELLA_CONFIG_LAUNCHER_VERSION, defines.DEFAULT_VERSION)
        dccs = launcher_config_data.get(defines.LAUNCHER_DCCS_ATTRIBUTE_NAME, dict())
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
            logger.warning('No DCCs enabled!')
            return

        for dcc_name, dcc_data in self._dccs.items():
            if dcc_data.enabled and not dcc_data.supported_versions:
                logger.warning(
                    '{0} DCC enabled but no supported versions found in launcher settings. '
                    '{0} DCC has been disabled!'.format(dcc_name.title()))

            try:
                dcc_module = importlib.import_module(
                    'artellalauncher.artelladccs.{}dcc'.format(dcc_name.lower().replace(' ', '')))
            except ImportError:
                logger.warning('DCC Python module {}dcc not found!'.format(dcc_name.lower().replace(' ', '')))
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
                logger.warning('DCC {} has not launch function implemented. Disabling it ...'.format(dcc_data.name))
                dcc_data.enabled = False

    def get_clean_name(self):
        """
        Returns a cleaned version of the launcher name (without spaces and in lowercase)
        :return: str
        """

        return self.name.replace(' ', '').lower()

    def get_data_path(self):
        """
        Returns path where user data for Artella launcher should be located
        This path is mainly located to store tools configuration files and log files
        :return: str
        """

        data_path = os.path.join(os.getenv('APPDATA'), self.get_clean_name())
        if not os.path.isdir(data_path):
            os.makedirs(data_path)

        return data_path

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
        Sets tools intallation path
        :return: str
        """

        return self._updater.set_installation_path()

    def _get_splash_pixmap(self):
        """
        Returns pixmap to be used as splash background
        :return: Pixmap
        """

        splash_path = self.resource.get('images', 'splash.png')
        if not os.path.isfile(splash_path):
            splash_dir = os.path.dirname(splash_path)
            splash_files = [
                f for f in os.listdir(splash_dir) if f.startswith('splash') and os.path.isfile(
                    os.path.join(splash_dir, f))]
            if splash_files:
                splash_index = random.randint(0, len(splash_files) - 1)
                splash_name, splash_extension = os.path.splitext(splash_files[splash_index])
                splash_pixmap = self.resource.pixmap(splash_name, extension=splash_extension[1:])
            else:
                splash_pixmap = resource.ResourceManager().pixmap('splash')
        else:
            splash_pixmap = self.resource.pixmap('splash')

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
            "QProgressBar::chunk {background: qlineargradient(x1: 0, y1: 1, x2: 1, y2: 1, stop: 0 "
            "rgb(" + str(progress_colors[0]) + "), stop: 1 rgb(" + str(progress_colors[1]) + ")); }")
        self.main_layout.addWidget(self.progress_bar)
        self.progress_bar.setMaximum(6)
        self.progress_bar.setTextVisible(False)

        self._progress_text = QLabel('Loading {} Tools ...'.format(self.name))
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
        console_btn.clicked.connect(self._on_toggle_console)

        self._splash.show()
        self._splash.raise_()

    def _set_text(self, msg):
        """
        Internal function that sets given text
        :param msg: str
        """

        self._progress_text.setText(msg)
        self._console.write('> {}'.format(msg))
        QApplication.instance().processEvents()

    def _on_toggle_console(self):
        """
        Internal callback function that is called when the user presses console button
        """

        self._console.hide() if self._console.isVisible() else self._console.show()

    def _on_dcc_selected(self, selected_dcc, selected_version):
        """
        Internal callback function that is called when the user selects a DCC to launch in DCCSelector window
        :param selected_dcc: str
        """

        try:
            if not selected_dcc:
                qtutils.show_warning(
                    None, 'DCC installations not found',
                    '{} Launcher cannot found any DCC installed in your computer.'.format(self.name))
                sys.exit()

            if selected_dcc not in self._dccs:
                qtutils.show_warning(
                    None,
                    '{} not found in your computer'.format(
                        selected_dcc.title()), '{} Launcher cannot launch {} because no version is '
                                               'installed in your computer.'.format(self.name, selected_dcc.title()))
                sys.exit()

            installation_paths = self._dccs[selected_dcc].installation_paths
            if not installation_paths:
                return

            if selected_version not in installation_paths:
                qtutils.show_warning(
                    None,
                    '{} {} installation path not found'.format(
                        selected_dcc.title(), selected_version),
                    '{} Launcher cannot launch {} {} because it is not installed in your computer.'.format(
                        self.name, selected_dcc.title(), selected_version))
                return

            installation_path = installation_paths[selected_version]

            self._setup_splash(selected_dcc)

            self._console.move(self._splash.geometry().center())
            self._console.move(300, 405)
            self._console.show()

            self._progress_text.setText('Creating {} Launcher Configuration ...'.format(self.name))
            self._console.write('> Creating {} Launcher Configuration ...'.format(self.name))
            QApplication.instance().processEvents()
            cfg = config.create_config(
                launcher_name=self.name.replace(' ', ''),
                console=self._console, window=self, dcc_install_path=installation_path)
            if not cfg:
                self._splash.close()
                self._console.close()
                qtutils.show_warning(
                    None, '{} location not found'.format(
                        selected_dcc.title()), '{} Launcher cannot launch {}!'.format(self.name, selected_dcc.title()))
                return
            QApplication.instance().processEvents()
            self._config = cfg

            parser = argparse.ArgumentParser(
                description='{} Launcher allows to setup a custom initialization for DCCs.'
                            ' This allows to setup specific paths in an easy way.'.format(self.name)
            )
            parser.add_argument(
                '-e', '--edit',
                action='store_true',
                help='Edit configuration file'
            )

            args = parser.parse_args()
            if args.edit:
                self._console.write('Opening {} Launcher Configuration file to edit ...'.format(self.name))
                return cfg.edit()

            exec_ = cfg.value('executable')

            self.progress_bar.setValue(1)
            QApplication.instance().processEvents()
            time.sleep(1)

            self._set_text('Updating Artella Paths ...')
            artellalib.update_artella_paths()

            self._set_text('Closing Artella App instances ...')
            valid_close = artellalib.close_all_artella_app_processes(console=self._console)
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
                        install_path, self.name))
                install_path = self.set_installation_path()
                if not install_path:
                    sys.exit()

                install_path = path_utils.clean_path(os.path.abspath(install_path))
                id_path = path_utils.clean_path(self.project.id_path)
                if id_path in install_path:
                    qtutils.show_warning(
                        None,
                        'Selected installation folder is not valid!',
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
                        logger.debug('Adding path to PYTHONPATH: {}'.format(p))
                        os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ';' + p
                else:
                    os.environ['PYTHONPATH'] = cfg.value(env_var)
                    for p in folders_to_register:
                        p = path_utils.clean_path(os.path.join(install_path, p))
                        logger.debug('Adding path to PYTHONPATH: {}'.format(p))
                        os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ';' + p

            self.progress_bar.setValue(5)
            self._set_text('Checking {} tools version ...'.format(self.name.title()))
            self.main_layout.addWidget(self._updater)
            self._updater.show()
            self._updater.raise_()
            QApplication.instance().processEvents()
            need_to_update = self._updater.check_tools_version()
            os.environ[self.get_clean_name() + '_show'] = 'show'

            self._updater.close()
            self._updater.progress_bar.setValue(0)
            QApplication.instance().processEvents()
            time.sleep(1)

            if need_to_update:
                self.progress_bar.setValue(6)
                self._set_text('Updating {} Tools ...'.format(self.name.title()))
                self._updater.show()
                QApplication.instance().processEvents()
                self._updater.update_tools()
                time.sleep(1)
                self._updater.close()
                self._updater.progress_bar.setValue(0)
                QApplication.instance().processEvents()

            self.console.write_ok('{} Tools setup completed, launching: {}'.format(self.name.title(), exec_))
            QApplication.instance().processEvents()

            # We need to import this here because this path maybe is not available until we update Artella paths
            try:
                import spigot
            except ImportError:
                self._console.write_error(
                    'Impossible to import Artella Python modules! Maybe Artella is not installed properly. '
                    'Contact TD please!')
                return

            launch_fn = self._dccs[selected_dcc].launch_fn
            if not launch_fn:
                self._console.write_error('Selected DCC: {} has no launch function!'.format(selected_dcc.name))
                QApplication.instance().processEvents()
                return
        except Exception as e:
            exceptions.capture_sentry_exception(e)
            logger.error('Error while running {} launcher ...'.format(self.project.name.title()))
            logger.error('{} | {}'.format(e, traceback.format_exc()))
            return

        self._splash.close()
        self._console.close()

        time.sleep(1)

        # Search for userSetup.py file
        setup_path = None
        for dir, _, files in os.walk(install_path):
            if setup_path:
                break
            for f in files:
                if f.endswith('userSetup.py'):
                    setup_path = path_utils.clean_path(os.path.join(dir, f))
                    break

        launch_fn(exec_=exec_, setup_path=setup_path)
