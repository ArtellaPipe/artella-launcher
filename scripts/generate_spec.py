#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation to generate PyInstall .spec files for Artella Launchers automatically
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import sys
import os
import json
import argparse
import importlib
import traceback
import subprocess

import tpPyUtils
tpPyUtils.init()
import tpDccLib
tpDccLib.init()
import tpQtLib
tpQtLib.init()

from tpPyUtils import path as path_utils

import artellapipe
artellapipe.init()
import artellapipe.launcher
artellapipe.launcher.init()

paths_to_add = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'source')
]
for p in paths_to_add:
    if p not in sys.path:
        if not os.path.isdir(p):
            continue
        sys.path.append(p)

json_path = path_utils.clean_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
with open(json_path, 'r') as f:
    config_data = json.loads(f.read())

project_name = config_data.get('MODULE_NAME')
project_icon = config_data.get('ICON_NAME')
launcher_name = config_data.get('LAUNCHER_NAME')
project_mod = importlib.import_module(project_name)
if not hasattr(project_mod, 'init'):
    raise RuntimeError('Module {} does not implement init function!'.format(project_mod))
project_mod.init()


def retrieve_hidden_imports():
    """
    Returns cmd that defines the hidden imports
    :return: str
    """

    hidden_import_cmd = '--hidden-import'
    dccs_module_name = 'artellalauncher.artelladccs'
    hidden_imports = list()
    dccs_module = importlib.import_module(dccs_module_name)
    dccs_path = os.path.dirname(os.path.abspath(dccs_module.__file__))
    for f in os.listdir(dccs_path):
        if not f.endswith('.py') or '__init__' in f:
            continue
        hidden_imports.append('{}.{}'.format(dccs_module_name, f[:-3]))

    cmd = ''
    for mod in hidden_imports:
        cmd += '{} {} '.format(hidden_import_cmd, mod)

    return cmd


def retrieve_data():
    """
    Returns cmd that defines the data used by installer
    :return: str
    """

    # Retrieve project data
    add_data_cmd = '--add-data'

    # Retrieve JSON files
    json_files = list()
    project_path = os.path.dirname(os.path.abspath(project_mod.__file__))
    for f in os.listdir(project_path):
        if not f.endswith('.json'):
            continue
        json_files.append(path_utils.clean_path(os.path.join(project_path, f)))

    cmd = ''
    for data in json_files:
        cmd += '{}="{};{}" '.format(add_data_cmd, data, project_name)

    # Resources valid folders
    resource_folders = ['icons', 'images', 'styles']
    qtlib_resources = ['default.css', 'close.png']
    resources_folder_name = 'resources'
    supported_formats = ['png', 'css', 'py', 'qrc']

    # Retrieve resource files
    data_files = list()

    for mod in [project_mod, artellapipe, artellapipe.launcher, tpQtLib]:
        mod_path = os.path.dirname(os.path.abspath(mod.__file__))
        resources_path = path_utils.clean_path(os.path.join(mod_path, resources_folder_name))
        for root, dirs, files in os.walk(resources_path):
            for f in files:
                if any(d in root for d in resource_folders):

                    # We only include necessary icons from tpQtLib
                    if mod == tpQtLib:
                        if os.path.basename(f) not in qtlib_resources:
                            continue

                    for supported_format in supported_formats:
                        if f.endswith('.{}'.format(supported_format)) and '__init__' not in f:
                            data_to_add = path_utils.clean_path(os.path.join(root, f))
                            if not os.path.isfile(data_to_add):
                                print('Resource path not valid: {}'.format(data_to_add))
                                continue

                            rel_path = path_utils.clean_path(os.path.join(mod.__name__, os.path.dirname(os.path.relpath(data_to_add, mod_path))))
                            data_files.append([data_to_add, rel_path])
                            continue

    for data in data_files:
        cmd += '{}="{};{}" '.format(add_data_cmd, data[0], data[1])

    return cmd


def retrieve_paths():
    """
    Returns paths where dependencies modules are located
    :return: str
    """

    paths_cmd = '--paths'

    mod_paths = list()
    for mod in [tpPyUtils, tpDccLib, tpQtLib, artellapipe, artellapipe.launcher, project_mod]:
        mod_path = path_utils.clean_path(os.path.dirname(os.path.dirname(os.path.abspath(mod.__file__))))
        mod_paths.append(mod_path)

    cmd = ''
    for p in mod_paths:
        cmd += '{}={} '.format(paths_cmd, p)

    return cmd


def generate_spec(one_file=True, windowed=True):
    """
    Function used to generate spec with proper settings for the installer
    """

    makespec_exe = os.path.join(os.path.dirname(sys.executable), 'pyi-makespec.exe')
    if not os.path.isfile(makespec_exe):
        makespec_exe = os.path.join(os.path.dirname(sys.executable), 'Scripts', 'pyi-makespec.exe')

    print('adsfasfd')
    print(makespec_exe)

    if not os.path.isfile(makespec_exe):
        raise RuntimeError('pyi-makespec.exe not found in Python Scripts folder: {}'.format(makespec_exe))

    print('specc ckadsf')

    spec_cmd = '"{}"'.format(makespec_exe)

    if one_file:
        spec_cmd += ' --onefile'

    if windowed:
        spec_cmd += ' --windowed'

    if project_icon:
        spec_cmd += ' --icon={}'.format(project_icon)

    hidden_imports_cmd = retrieve_hidden_imports()
    spec_cmd += ' {}'.format(hidden_imports_cmd)

    data_cmd = retrieve_data()
    spec_cmd += ' {}'.format(data_cmd)

    paths_cmd = retrieve_paths()
    spec_cmd += ' {}'.format(paths_cmd)

    spec_cmd += 'launcher.py'

    return spec_cmd


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate Launcher Specs')
    parser.add_argument('--windowed', required=False, default=False, action='store_true', help='Whether generated executable is windowed or not')
    parser.add_argument('--onefile', required=False, default=False, action='store_true', help='Whether generated executable is stored in a unique .exe or not')
    args = parser.parse_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    spec_cmd = generate_spec(one_file=args.onefile, windowed=args.windowed)

    try:
        process = subprocess.Popen(spec_cmd)
        process.wait()
    except Exception as e:
        raise RuntimeError('Error while generate Launcher Spec file | {} - {}'.format(e, traceback.format_exc()))
