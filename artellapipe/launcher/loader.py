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
import inspect
import logging.config


def init(do_reload=False):
    """
    Initializes module
    :param do_reload: bool, Whether to reload modules or not
    """

    logging.config.fileConfig(get_logging_config(), disable_existing_loggers=False)

    import sentry_sdk
    try:
        sentry_sdk.init("https://c329025c8d5a4e978dd7a4117ab6281d@sentry.io/1770788")
    except RuntimeError:
        sentry_sdk.init("https://c329025c8d5a4e978dd7a4117ab6281d@sentry.io/1770788", default_integrations=False)

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

    launcher_importer = importer.init_importer(importer_class=ArtellaLauncher, do_reload=False)
    launcher_importer.import_packages(order=packages_order, only_packages=False)
    if do_reload:
        launcher_importer.reload_all()

    create_logger_directory()

    from artellapipe.utils import resource
    resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
    resource.ResourceManager().register_resource(resources_path, 'launcher')


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

    return os.environ.get('ARTELLAPIPE_LAUNCHER_LOG_LEVEL', 'DEBUG')


def get_artella_launcher_configurations_folder():
    """
    Returns path where artella configurations folder are located
    :return: str
    """

    from artellapipe.launcher.core import defines

    if os.environ.get(defines.ARTELLA_LAUNCHER_CONFIGURATION_DEV, None):
        return os.environ[defines.ARTELLA_LAUNCHER_CONFIGURATION_DEV]
    else:
        import artellapipe.config as cfg
        return cfg.ArtellaConfigs().get_configurations_path()


def get_launcher_config_path():
    """
    Returns path where default Artella launcher config is located
    :return: str
    """

    from tpPyUtils import path as path_utils
    from artellapipe.launcher.core import defines

    cfg_path = get_artella_launcher_configurations_folder()

    return path_utils.clean_path(os.path.join(cfg_path, defines.ARTELLA_LAUNCHER_CONFIG_FILE_NAME))
