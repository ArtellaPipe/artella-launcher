#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions to handle Nuke functionality
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import platform


DEFAULT_DCC = 'nuke.exe'


def get_executables_from_installation_path(installation_path):
    """
    Returns Nuke executable from its installation path
    :param installation_path: str
    """

    if os.path.exists(installation_path):
        nuke_files = os.listdir(installation_path)
        houdini_ex = os.path.basename(installation_path).split('v')[0] + '.exe'
        if houdini_ex in nuke_files:
            return os.path.join(installation_path, houdini_ex)

    return None


def get_installation_paths(nuke_versions):
    """
    Returns the installation folder of Nuke
    :param nuke_versions: list(str)
    :return:
    """

    versions = dict()

    if platform.system().lower() == 'windows':
        for nuke_version in nuke_versions:
            nuke_path = 'C://Program Files//Nuke{}'.format(nuke_version)
            if not os.path.exists(nuke_path):
                continue

            nuke_executable = get_executables_from_installation_path(nuke_path)
            if nuke_executable is None or not os.path.isfile(nuke_executable):
                continue

            versions['{}'.format(nuke_version)] = nuke_executable

    return versions
