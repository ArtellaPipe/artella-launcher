#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for artellapipe-launcher
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import sys
import inspect

# =================================================================================

current_project = None

# =================================================================================


def init(do_reload=False):
    """
    Initializes module
    :param do_reload: bool, Whether to reload modules or not
    """

    import sentry_sdk
    sentry_sdk.init("https://c329025c8d5a4e978dd7a4117ab6281d@sentry.io/1770788")

    from tpPyUtils import importer

    class ArtellaLauncher(importer.Importer, object):
        def __init__(self):
            super(ArtellaLauncher, self).__init__(module_name='artellapipe.launcher')

        def get_module_path(self):
            """
            Returns path where tpNameIt module is stored
            :return: str
            """

            try:
                mod_dir = os.path.dirname(inspect.getframeinfo(inspect.currentframe()).filename)
            except Exception:
                try:
                    mod_dir = os.path.dirname(__file__)
                except Exception:
                    try:
                        import tpDccLib
                        mod_dir = tpDccLib.__path__[0]
                    except Exception:
                        return None

            return mod_dir

    packages_order = []

    update_paths()
    launcher_importer = importer.init_importer(importer_class=ArtellaLauncher, do_reload=False)
    launcher_importer.import_packages(order=packages_order, only_packages=False)
    if do_reload:
        launcher_importer.reload_all()

    create_logger_directory()

    from artellapipe.utils import resource
    resources_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources')
    resource.ResourceManager().register_resource(resources_path)


def update_paths():
    """
    Adds to sys.path necessary modules
    :return:
    """

    dccs_path = get_dccs_path()
    if dccs_path and os.path.isdir(dccs_path):
        sys.path.append(dccs_path)


def create_logger_directory():
    """
    Creates artellapipe logger directory
    """

    artellapipe_logger_dir = os.path.normpath(os.path.join(os.path.expanduser('~'), 'artellapipe', 'logs'))
    if not os.path.isdir(artellapipe_logger_dir):
        os.makedirs(artellapipe_logger_dir)


def get_logging_config():
    """
    Returns logging configuration file path
    :return: str
    """

    create_logger_directory()

    return os.path.normpath(os.path.join(os.path.dirname(__file__), '__logging__.ini'))


def get_logging_level():
    """
    Returns logging level to use
    :return: str
    """

    if os.environ.get('ARTELLAPIPE_LAUNCHER_LOG_LEVEL', None):
        return os.environ.get('ARTELLAPIPE_LAUNCHER_LOG_LEVEL')

    return os.environ.get('ARTELLAPIPE_LAUNCHER_LOG_LEVEL', 'WARNING')


def get_dccs_path():
    """
    Returns path where DCCs are located
    :return: str
    """

    from tpPyUtils import path
    return path.clean_path(os.path.join(os.path.dirname(__file__), 'dccs'))


def get_launcher_config_path():
    """
    Returns path where default Artella launcher config is located
    :return: str
    """

    from tpPyUtils import path
    from artellapipe.launcher.core import defines
    return path.clean_path(os.path.join(os.path.dirname(__file__), defines.ARTELLA_LAUNCHER_CONFIG_FILE_NAME))


def get_updater_config_path():
    """
    Returns path where default Artella updater config is located
    :return: str
    """

    from tpPyUtils import path
    from artellapipe.launcher.core import defines
    return path.clean_path(os.path.join(os.path.dirname(__file__), defines.ARTELLA_UPDATER_CONFIG_FILE_NAME))
