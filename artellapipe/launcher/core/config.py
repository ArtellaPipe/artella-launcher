#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation to create Artella Launcher configuration file
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import platform
import subprocess
from pathlib2 import Path


from Qt.QtCore import *


class ArtellaLauncherConfig(QSettings, object):
    """
    Configuration file for Artella Launcher
    """

    # Sections
    EXECUTABLES = 'executables'
    ENVIRONMENTS = 'environments'

    def __init__(self, filename, window, console):
        super(ArtellaLauncherConfig, self).__init__(str(filename), QSettings.IniFormat, window)
        self.config_file = filename
        if console:
            console.write('> {} Configuration File: {}\n'.format(window.name, filename))

    def edit(self):
        """
        Edit file with default OS application
        """

        if platform.system().lower() == 'windows':
            os.startfile(str(self.config_file))
        else:
            if platform.system().lower() == 'darwin':
                call = 'open'
            else:
                call = 'xdg-open'
            subprocess.call(call, self.config_file)


def get_system_config_directory(launcher_name, console=None, as_path=False):
    """
    Returns platform specific configuration directory
    """

    if platform.system().lower() == 'windows':
        config_directory = Path(os.getenv('APPDATA') or '~')
    elif platform.system().lower() == 'darwin':
        config_directory = Path('~', 'Library', 'Preferences')
    else:
        config_directory = Path(os.getenv('XDG_CONFIG_HOME') or '~/.config')

    if console:
        console.write('> Fetching configuration directory for {}'.format(platform.system()))
        console.write('> Getting Installed {} version ...'.format(launcher_name))

    if as_path:
        return config_directory.joinpath(Path(launcher_name))
    else:
        return config_directory.joinpath(Path('{}/.config'.format(launcher_name)))


def create_config(launcher_name, console, window, dcc_install_path, config_file=None):
    """
    Construct the Launcher configuration object from necessary elements
    """

    if config_file is None:
        config_file = get_system_config_directory(launcher_name=launcher_name, console=console)
    config = ArtellaLauncherConfig(filename=config_file, window=window, console=console)

    if not dcc_install_path:
        if console:
            console.write('Dcc Location not found: {} Launcher will not launch DCC!'.format(launcher_name))
        return config

    # for item in application_versions.items():
    config.setValue('executable', os.path.abspath(dcc_install_path))

    return config
