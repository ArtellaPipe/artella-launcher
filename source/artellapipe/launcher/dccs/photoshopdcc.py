#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions to handle Photoshop functionality
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import platform


DEFAULT_DCC = 'photoshop.exe'


def get_executables_from_installation_path(installation_path):
    """
    Returns Maya executable from its installation path
    :param installation_path: str
    """

    return None


def get_installation_paths(photoshop_versions):
    """
    Returns the installation paths folder where Photoshop is located in the user computer
    :param photoshop_versions: list(str)
    :return: str
    """

    return {'2018': 'C://Program Files//Adobe//Adobe Photoshop CC 2018//Photoshop.exe'}
