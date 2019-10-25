#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import sys
import argparse
import contextlib

from Qt.QtWidgets import QApplication


@contextlib.contextmanager
def application():
    app = QApplication.instance()

    if not app:
        app = QApplication(sys.argv)
        yield app
        app.exec_()
    else:
        yield app


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate Python Virtual Environment to generate launcher')
    parser.add_argument('--install-path', type=str, required=True)
    parser.add_argument('--paths-to-register', nargs='+', type=str, required=False)
    parser.add_argument('--dev', required=False, default=False, action='store_true')
    args = parser.parse_args()

    with application() as app:
        from solstice import launcher
        launcher.init()
        from solstice.launcher import launcher
        launcher.run(install_path=args.install_path, paths_to_register=args.paths_to_register, dev=args.dev)
