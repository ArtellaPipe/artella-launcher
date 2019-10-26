#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains core implementation for Artella Launcher Plugins
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import sys
import types
import inspect
import logging
import traceback

from Qt.QtCore import *

from tpPyUtils import python, decorators, path as path_utils
from tpQtLib.core import base

from artellapipe.utils import resource

LOGGER = logging.getLogger()


class ArtellaLauncherPlugin(base.BaseWidget, object):

    LABEL = 'Plugin'
    HIDDEN = False
    ID = python.classproperty(lambda cls: cls.__name__)
    ORDER = 0
    ICON = 'plugin'

    launched = Signal(object)

    def __init__(self, project, launcher=None, parent=None, **kwargs):

        self._project = project
        self._launcher = launcher

        self.init_config()

        super(ArtellaLauncherPlugin, self).__init__(parent=parent)

    def __str__(self):
        return self.LABEL

    def __repr__(self):
        return '{}.{}({})'.format(self.__name__, type(self).__name__, self.__str__())

    def __eq__(self, other):
        if issubclass(other, ArtellaLauncherPlugin):
            return self.ID == other.ID

        return False

    @property
    def project(self):
        """
        Returns project this plugin belongs to
        :return: ArtellaProject
        """

        return self._project

    @property
    def launcher(self):
        """
        Returns launcher this plugin belongs to
        :return: ArtellaLauncher
        """

        return self._launcher

    @property
    def config(self):
        """
        Returns the config associated to this launcher
        :return: ArtellaConfig
        """

        return self._config

    def init_config(self):
        """
        Function that reads Plugin configuration
        This function can be extended in new launchers
        """

        pass

    @decorators.abstractmethod
    def initialize(self):
        """
        Initializes plugin
        :return:
        """

        pass

    @decorators.abstractmethod
    def uninitialize(self):
        """
        Uninitialize plugin
        """

        pass

    @classmethod
    def get_icon(cls):
        """
        Returns icon resource of the current plugin
        :return: QIcon
        """

        plugin_icon = cls.ICON
        icon_split = plugin_icon.split('/')
        if len(icon_split) == 1:
            theme = 'color'
        elif len(icon_split) > 1:
            theme = icon_split[0]
        else:
            theme = 'color'
        icon_path = resource.ResourceManager().get('icons', theme, '{}.png'.format(cls.ICON), key='project')
        if not icon_path or not os.path.isfile(icon_path):
            icon_path = resource.ResourceManager().get('icons', theme, '{}.png'.format(cls.ICON))
            if not icon_path or not os.path.isfile(icon_path):
                plugin_icon = resource.ResourceManager().icon('plugin')
            else:
                plugin_icon = resource.ResourceManager().icon(cls.ICON, theme=theme)
        else:
            plugin_icon = resource.ResourceManager().icon(cls.ICON, theme=theme, key='project')

        return plugin_icon


class PluginManager(object):

    PLUGIN_CLASS = ArtellaLauncherPlugin

    def __init__(self, plugin_paths):
        self._registered_paths = list()
        self._registered_plugins = dict()

        plugin_paths = python.force_list(plugin_paths)
        for p in plugin_paths:
            if not os.path.exists(p):
                LOGGER.warning(
                    'Impossible to register Artella Launcher Plugin Path because it does not exists: {}!'.format(p))
                continue
            self._register_plugin_path(p)

    @staticmethod
    def sort_plugins(plugins_list):
        """
        Sorts loaded Artella Launcher plugins taking into account their order attribute
        :param plugins_list: list(ArtellaLauncherPlugin)
        :return: list(ArtellaLauncherPlugin)
        """

        if not isinstance(plugins_list, list):
            raise TypeError('Artella Launcher Plugins must be of type list!')

        plugins_list.sort(key=lambda p: p.ORDER)

        return plugins_list

    @property
    def registered_plugin_paths(self):
        """
        Returns a list with all registered plugin paths
        :return: list(str)
        """

        return list(self._registered_paths)

    @property
    def registered_plugins(self):
        """
        Returns a list with all registered Artella Launcher plugins
        :return: list(ArtellaLauncherPlugin)
        """

        return self._registered_plugins.values()

    def check_plugin_validity(self, plugin_to_check):
        """
        Returns whether given plugin is a valid ArtellaLauncherPlugin or not
        :param plugin_to_check: ArtellaLauncherPlugin
        :return: bool
        """

        if not plugin_to_check:
            return False

        return True

    def get_plugin_from_module(self, module):
        """
        Returns Artella Launcher plugins from a given module
        :param module: Module, Python module
        :return: list(ArtellaLauncherPlugin), list of Artella Launcher plugins stored in given module
        """

        plugins_found = list()
        for plugin_name in dir(module):
            if plugin_name.startswith('_'):
                continue
            module_obj = getattr(module, plugin_name)
            if not inspect.isclass(module_obj):
                continue
            if not issubclass(module_obj, self.PLUGIN_CLASS):
                continue
            if not self.check_plugin_validity(module_obj):
                LOGGER.warning('Artella Launcher Plugin "{}" is not valid!'.format(module_obj))
                continue
            plugins_found.append(module_obj)

        return plugins_found

    def get_plugins(self):
        """
        Find and returns available Artella Launcher plugins on given paths
        :return: dict(str, ArtellaLauncherPlugin)
        """

        plugins_found = dict()

        if not self._registered_paths:
            LOGGER.warning('No Artella Launcher Paths registered yet!')
            return plugins_found

        for p in self.registered_plugin_paths:
            p = path_utils.clean_path(p)
            if not path_utils.is_dir(p):
                LOGGER.warning('Path "{}" is not a valid Artella Launcher Plugin path!'.format(p))
                continue

            for file_name in path_utils.get_files(root=p, file_extension='py'):
                if file_name.startswith('_'):
                    continue
                mod_name, mod_ext = os.path.splitext(file_name)
                if not mod_ext == '.py':
                    continue
                plugin_path = path_utils.clean_path(path_utils.join_path(p, file_name))
                if not path_utils.is_file(plugin_path):
                    LOGGER.warning('File "{}" is not a valid Artella Launcher Plugin File!'.format(plugin_path))
                    continue

                plugin_module = types.ModuleType(str(mod_name))
                plugin_module.__file__ = plugin_path

                try:
                    execfile(plugin_path, plugin_module.__dict__)
                    sys.modules[mod_name] = plugin_module
                except Exception as e:
                    LOGGER.error('Artella Launcher Skipped: {} | {} | {}'.format(mod_name, e, traceback.format_exc()))
                    continue

                for plug in self.get_plugin_from_module(plugin_module):
                    if plug.ID in plugins_found:
                        LOGGER.warning('Duplicated Artella Launcher Plug found: {}!'.format(plug))
                        continue
                    plugins_found[plug.ID] = plug

        for name, plug in self._registered_plugins.items():
            if name in plugins_found:
                LOGGER.warning('Duplicated Artella Launcher Plugin found: {}!'.format(plug))
                continue
            plugins_found[name] = plug

        plugins_found = list(plugins_found.values())
        self.sort_plugins(plugins_found)

        return plugins_found

    def _register_plugin_path(self, plugin_path):
        """
        Internal function that registers plugin path, so the plugin located in that path is loaded at run-time during
        Artella Launcher initialization
        :param plugin_path: str, path to add where Artella Launcher Plugin is located
        :return: str
        """

        if plugin_path in self._registered_paths:
            LOGGER.warning('Artella Launcher Plugin Path "{}" is already registered!'.format(plugin_path))
            return

        LOGGER.debug('Registering Artella Launcher Plugin Path: "{}"'.format(plugin_path))
        self._registered_paths.append(plugin_path)

        return plugin_path
