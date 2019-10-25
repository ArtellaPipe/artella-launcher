#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions to handle Maya functionality
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

LOGGER = logging.getLogger()


DEFAULT_DCC = 'maya.exe'


def get_executables_from_installation_path(installation_path):
    """
    Returns Maya executable from its installation path
    :param installation_path: str
    """

    if os.path.exists(installation_path):
        bin_path = os.path.join(installation_path, 'bin')

        if not os.path.exists(bin_path):
            return None
        maya_files = os.listdir(bin_path)
        if DEFAULT_DCC in maya_files:
            return os.path.join(bin_path, DEFAULT_DCC)

    return None


def get_installation_paths(maya_versions):
    """
    Returns the installation paths folder where Maya is located in the user computer
    :param maya_versions: list(str)
    :return: str
    """

    versions = dict()
    locations = dict()

    if platform.system().lower() == 'windows':
        try:
            from _winreg import *
            for maya_version in maya_versions:
                a_reg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
                a_key = OpenKey(a_reg, r"SOFTWARE\Autodesk\Maya\{}\Setup\InstallPath".format(maya_version))
                value = QueryValueEx(a_key, 'MAYA_INSTALL_LOCATION')
                maya_location = value[0]
                locations['{}'.format(maya_version)] = maya_location
        except Exception:
            # maya_location = os.getenv('MAYA_LOCATION')
            # if not maya_location:
            for maya_version in maya_versions:
                path = 'C:/Program Files/Autodesk/Maya{}'.format(maya_version)
                if os.path.exists(path):
                    maya_location = path
                    locations['{}'.format(maya_version)] = maya_location

    if not locations:
        LOGGER.warning('Maya installations not found in your computer. Maya cannot be launched!')
        return None

    for maya_version, maya_location in locations.items():
        maya_executable = get_executables_from_installation_path(maya_location)
        if maya_executable is None or not os.path.isfile(maya_executable):
            LOGGER.warning('Maya {} installation path: {} is not valid!'.format(maya_version, maya_location))
            continue

        versions['{}'.format(maya_version)] = maya_executable

    return versions


def launch(exec_, setup_path=None):
    """
    Launches Maya application with proper configuration
    :param exec_: str
    :param setup_path: str
    """

    if not exec_:
        return None

    cmd = [exec_]

    curr_env = dict()
    for k, v in os.environ.items():
        curr_env[k] = str(v)

    subprocess.Popen(cmd, close_fds=True, env=curr_env)
