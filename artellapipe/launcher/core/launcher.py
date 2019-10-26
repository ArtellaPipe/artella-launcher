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
import logging
import importlib

from Qt.QtWidgets import *

from tpQtLib.widgets import tabs

from artellapipe.gui import window
from artellapipe.core import artellalib, config
from artellapipe.utils import exceptions, resource
from artellapipe.launcher.core import defines, plugin as core_plugin
from artellapipe.launcher.widgets import pluginspanel

LOGGER = logging.getLogger()


class ArtellaLauncher(window.ArtellaWindow, object):

    VERSION = '0.0.1'
    LOGO_NAME = 'launcher_logo'

    def __init__(self, project, install_path, paths_to_register=None, dev=False):

        self._logger = None
        self._name = None
        self._version = None
        self._plugins = None
        self._install_path = install_path
        self._paths_to_register = paths_to_register if paths_to_register else list()
        self._dev = dev

        super(ArtellaLauncher, self).__init__(
            project=project,
            name='ArtellaLauncherWindow',
            title='Launcher'
        )

        self._config = config.ArtellaConfiguration(
            project_name=self._project.get_clean_name(),
            config_name='artellapipe-launcher'
        )

        self.init_config()
        self._logger = self.create_logger()[1]

        self.init()

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
    def dev(self):
        """
        Returns whether or not launcher has been launched in dev mode or not
        :return: bool
        """

        return self._dev

    @property
    def icon(self):
        """
        Returns the icon associated to this launcher
        :return: str
        """

        return resource.ResourceManager().icon(self._name.lower().replace(' ', ''), theme=None, key='project')

    @property
    def config(self):
        """
        Returns the config associated to this launcher
        :return: ArtellaConfig
        """

        return self._config

    @property
    def project(self):
        """
        Returns the project of the Artella launcher
        :return: ArtelalProject
        """

        return self._project

    @property
    def logger(self):
        """
        Returns the logger used by the Artella launcher
        :return: Logger
        """

        return self._logger

    @property
    def install_path(self):
        """
        Returns path where pipeline tools are installed
        :return: str
        """

        return self._install_path

    @property
    def paths_to_register(self):
        """
        Returns list of paths that should be added to sys.path during DCC launching
        :return: list(str)
        """

        return self._paths_to_register

    def ui(self):
        super(ArtellaLauncher, self).ui()

        self._plugins_tab = tabs.BaseEditableTabWidget()
        self._plugins_tab.tabBar().add_tab_btn.setVisible(False)
        self.main_layout.addWidget(self._plugins_tab)

        self._plugins_panel = pluginspanel.PluginsPanel(project=self._project)
        self._plugins_tab.addTab(self._plugins_panel, 'HOME')
        self._plugins_tab.tabBar().tabButton(0, QTabBar.RightSide).resize(0, 0)
        self._plugins_tab.tabBar().set_is_editable(False)

    def setup_signals(self):
        self._plugins_panel.openPlugin.connect(self._on_open_plugin)

    def init(self):
        """
        Function that initializes Artella launcher
        """

        plugin_paths = self._get_plugin_paths()
        self._plugin_manager = core_plugin.PluginManager(plugin_paths=plugin_paths)
        loaded_plugins = self._plugin_manager.get_plugins()
        if not loaded_plugins:
            LOGGER.warning('No Artella Launcher Plugins found!')
            return

        for plugin in loaded_plugins:
            self._add_plugin(plugin)

    def _get_plugin_paths(self):

        plugin_paths = list()

        if not self._plugins:
            return plugin_paths

        for p in self._plugins:
            plugin_mod = None
            try:
                plugin_mod = importlib.import_module(p)
            except ImportError:
                try:
                    plugin_mod = importlib.import_module(
                        '{}.launcher.plugins.{}'.format(self._project.get_clean_name(), p))
                except ImportError:
                    try:
                        plugin_mod = importlib.import_module(
                            'artella.launcher.plugins.{}'.format(self._project.get_clean_name(), p))
                    except ImportError:
                        LOGGER.warning('Impossible to load ArtellaPipe Launcher Plugin: {}'.format(p))
            if not plugin_mod:
                continue

            if hasattr(plugin_mod, 'init'):
                plugin_mod.init()

            plugin_paths.append(os.path.dirname(plugin_mod.__file__))

        return plugin_paths

    def _add_plugin(self, plugin):
        """
        Adds given Artella Launcher plugin into UI
        :param plugin: ArtellaLauncherPlugin
        """

        if not plugin:
            return

        if plugin.HIDDEN:
            LOGGER.warning('Plugin "{}" is not enabled. Skipping loading ...!'.format(plugin.LABEL))
            return

        self._plugins_panel.add_plugin(plugin)

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

        self._name = self._config.data.get(defines.ARTELLA_CONFIG_LAUNCHER_NAME, defines.ARTELLA_DEFAULT_LAUNCHER_NAME)
        self._version = self._config.data.get(defines.ARTELLA_CONFIG_LAUNCHER_VERSION, defines.DEFAULT_VERSION)
        self._plugins = self._config.data.get(defines.ARTELLA_CONFIG_LAUNCHER_PLUGINS, list())

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

    def _on_toggle_console(self):
        """
        Internal callback function that is called when the user presses console button
        """

        self._console.hide() if self._console.isVisible() else self._console.show()

    def _on_open_plugin(self, plugin):
        for i in range(self._plugins_tab.count()):
            plugin_widget = self._plugins_tab.widget(i)
            if plugin_widget == plugin:
                self._plugins_tab.setCurrentWidget(plugin_widget)
                return

        try:
            plugin_widget = plugin(project=self._project, launcher=self)
            plugin_widget.launched.connect(self._on_launch_plugin)
            self._plugins_tab.addTab(plugin_widget, plugin_widget.LABEL)
            self._plugins_tab.setCurrentWidget(plugin_widget)
        except Exception as e:
            raise exceptions.ArtellaPipeException(self._project, e)

    def _on_launch_plugin(self, flag):
        if flag:
            self.close()
            artellalib.spigot_client._connected = False


def run(project, install_path, paths_to_register=None, dev=False):
    win = ArtellaLauncher(project=project,
                          install_path=install_path,
                          paths_to_register=paths_to_register, dev=dev)
    win.show()

    return win
