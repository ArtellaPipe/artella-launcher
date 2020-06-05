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
import logging.config

import tpDcc as tp

# =================================================================================

PACKAGE = 'artellapipe.launcher'

# =================================================================================


def init(dev=False):
    """
    Initializes module
    :param dev: bool, Whether artellapipe-launcher is initialized in dev mode or not
    """

    from tpDcc.libs.python import importer
    from artellapipe.launcher import register

    if dev:
        register.cleanup()

    logger = create_logger(dev=dev)

    register.register_class('logger', logger)

    if not dev:
        import sentry_sdk
        try:
            sentry_sdk.init("https://c329025c8d5a4e978dd7a4117ab6281d@sentry.io/1770788")
        except RuntimeError:
            sentry_sdk.init("https://c329025c8d5a4e978dd7a4117ab6281d@sentry.io/1770788", default_integrations=False)

    skip_modules = ['{}.{}'.format(PACKAGE, name) for name in ['loader']]
    importer.init_importer(package=PACKAGE, skip_modules=skip_modules)

    register_resources()


def create_logger(dev=False):
    """
    Returns logger of current module
    """

    logger_directory = os.path.normpath(os.path.join(os.path.expanduser('~'), 'artellapipe', 'logs'))
    if not os.path.isdir(logger_directory):
        os.makedirs(logger_directory)

    logging_config = os.path.normpath(os.path.join(os.path.dirname(__file__), '__logging__.ini'))

    logging.config.fileConfig(logging_config, disable_existing_loggers=False)
    logger = logging.getLogger('artellapipe-launcher')
    if dev:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    return logger


def register_resources():
    """
    Registers artellapipe-launcher resources
    """

    resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
    tp.ResourcesMgr().register_resource(resources_path, 'launcher')
