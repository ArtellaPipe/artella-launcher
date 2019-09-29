#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Artella launcher implementation for Plot Twist
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import sys

import tpPyUtils
tpPyUtils.init()
import tpDccLib
tpDccLib.init()
import tpQtLib
tpQtLib.init()

from PySide.QtGui import *

import artellapipe
artellapipe.init()
import artellalauncher
artellalauncher.init()

import plottwist
plottwist.init()

from plottwist.launcher import launcher


if __name__ == '__main__':
    app = QApplication(sys.argv)

    launcher = launcher.PlotTwistLauncher(plottwist.resource)
    launcher.init()
    app.exec_()

