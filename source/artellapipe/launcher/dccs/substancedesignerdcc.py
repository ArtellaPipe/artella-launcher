#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions to handle Substance Designer functionality
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import platform


DEFAULT_DCC = 'painter.exe'


def get_executables_from_installation_path(installation_path):
    """
    Returns Substance Designer executable from its installation path
    :param installation_path: str
    """

    return None


def get_installation_paths(designer_versions):
    """
    Returns the installation folder of Substance Designer
    :param designer_versions: list(str)
    :return:
    """

    versions = dict()

    return {'4R8': 'C://Program Files//Pixologic//ZBrush 4R8//ZBrush.exe'}
