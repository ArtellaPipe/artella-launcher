#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions to handle Houdini functionality
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import platform
import subprocess
import logging

from tpQtLib.core import qtutils

LOGGER = logging.getLogger()


DEFAULT_DCC = 'houdini.exe'


def get_executables_from_installation_path(installation_path):
    """
    Returns Houdini executable from its installation path
    :param installation_path: str
    """

    if os.path.exists(installation_path):
        bin_path = os.path.join(installation_path, 'bin')

        if not os.path.exists(bin_path):
            return None
        houdini_files = os.listdir(bin_path)
        if DEFAULT_DCC in houdini_files:
            return os.path.join(bin_path, DEFAULT_DCC)

    return None


def get_installation_paths(houdini_versions):
    """
    Returns the installation folder of Houdini
    :return:
    """

    versions = dict()
    locations = dict()

    if platform.system().lower() == 'windows':
        try:
            from _winreg import ConnectRegistry, OpenKey, QueryValueEx, HKEY_LOCAL_MACHINE
            for houdini_version in houdini_versions:
                a_reg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
                a_key = OpenKey(a_reg, r"SOFTWARE\Side Effects Software\Houdini {}".format(houdini_version))
                value = QueryValueEx(a_key, 'InstallPath')
                houdini_location = value[0]
                locations['{}'.format(houdini_version)] = houdini_location
        except Exception:
            pass

    if not locations:
        LOGGER.warning('Houdini installations not found in your computer. Maya cannot be launched!')
        return None

    for houdini_version, houdini_location in locations.items():
        houdini_executable = get_executables_from_installation_path(houdini_location)
        if houdini_executable is None or not os.path.isfile(houdini_executable):
            LOGGER.warning('Houdini {} installation path: {} is not valid!'.format(houdini_version, houdini_location))
            continue

        versions['{}'.format(houdini_version)] = houdini_executable

    return versions


def launch(exec_, setup_path):
    """
    Launches Houdini application with proper configuration
    :param exec_: str
    :param setup_path: str
    """

    if not exec_:
        return None

    setup_root = os.path.dirname(setup_path)

    hou_dcc_path = os.path.join(setup_root, 'dcc', 'houdini')
    if not os.path.isdir(hou_dcc_path):
        qtutils.show_warning(
            None, 'No valid Houdini DCC folder found!',
            'Launcher cannot launch Houdini. Houdini DCC folder not found: {}!'.format(hou_dcc_path))
        return None
    hou_bootstrap = os.path.join(hou_dcc_path, 'houdini_bootstrap.bat')
    if not os.path.isfile(hou_bootstrap):
        qtutils.show_warning(
            None, 'No valid Houdini Bootstrap found!',
            'Launcher cannot launch Houdini. Bootstrap not found: {}!'.format(hou_bootstrap))
        return None
    cmd = [hou_bootstrap]
    cmd.extend([exec_, hou_dcc_path, setup_path])

    subprocess.Popen(cmd)
