#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation for Artella Launcher Console
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

from io import StringIO
import logging

from Qt.QtWidgets import *
from Qt.QtGui import *


class ArtellaLauncherConsole(QTextEdit, object):
    def __init__(self, logger, parent=None):
        super(ArtellaLauncherConsole, self).__init__(parent=parent)

        self._buffer = StringIO()
        self.setReadOnly(True)

        self.setStyleSheet(
            """
            QTextEdit { background-color : rgba(0, 0, 0, 180); color : white; }
            """
        )

        self.logger = logger

    def write(self, msg):
        """
        Add message to the console's output, on a new line
        :param msg: str
        """

        self.insertPlainText(msg + '\n')
        self.moveCursor(QTextCursor.End)
        self._update_buffer(msg)
        self.logger.debug('{}\n'.format(msg))

    def write_error(self, msg):
        """
        Adds an error message to the console
        :param msg: str
        """

        msg_html = "<font color=\"Red\">ERROR: " + msg + "\n</font><br>"
        msg = 'ERROR: ' + msg
        self.insertHtml(msg_html)
        self.moveCursor(QTextCursor.End)
        self._update_buffer(msg)
        self.logger.debug('{}\n'.format(msg))

    def write_ok(self, msg):
        """
        Adds an ok green message to the console
        :param msg: str
        """

        msg_html = "<font color=\"Lime\">: " + msg + "\n</font><br>"
        self.insertHtml(msg_html)
        self.moveCursor(QTextCursor.End)
        self._update_buffer(msg)
        self.logger.debug('{}\n'.format(msg))

    def set_info_level(self):
        """
        Sets console logging level to info
        """

        self.logger.setLevel(logging.INFO)

    def set_debug_level(self):
        """
        Sets console logging level to debug
        """

        self.logger.setLevel(logging.DEBUG)

    def __getattr__(self, attr):
        """
        Fall back to the buffer object if an attribute cannot be found
        """

        return getattr(self._buffer, attr)

    def output_buffer_to_file(self, filepath):
        """
        Stores the console output buffer into a file
        :param filepath: str
        """

        raise NotImplemented('output_buffer_to_file not implemented yet!')

    def _update_buffer(self, msg):
        """
        Internal function that updates buffer
        :param msg: str
        """

        try:
            self._buffer.write(unicode(msg))
        except Exception:
            pass
