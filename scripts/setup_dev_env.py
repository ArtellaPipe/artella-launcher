#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation to generate Python Virtual Environment with proper deps to generate launcher
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import sys
import shutil
import argparse
import subprocess

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate Python Virtual Environment to generate launcher')
    parser.add_argument('--name', required=False, default='artella_dev', help='Name of the Python environment')
    parser.add_argument('--clean', required=False, default=False, action='store_true', help='Whether to delete already created venv')
    parser.add_argument('--clean-after', required=False, default=False, action='store_true', help='Whether to delete venv after process is completed')
    parser.add_argument('--update', required=False, default=False, action='store_true', help='Whether update venv requirements')
    parser.add_argument('--generate-launcher', required=False, default=False, action='store_true', help='Whether to generate launcher using venv')
    parser.add_argument('--generate-spec', required=False, default=False, action='store_true', help='Whether .spec file should be created or not')
    parser.add_argument('--windowed', required=False, default=False, action='store_true', help='Whether generated executable is windowed or not')
    parser.add_argument('--onefile', required=False, default=False, action='store_true', help='Whether generated executable is stored in a unique .exe or not')
    args = parser.parse_args()

    venv_name = args.name

    virtual_env = os.path.dirname(sys.executable) + os.sep + 'Scripts' + os.sep + 'virtualenv.exe'
    if not os.path.isfile(virtual_env):
        print('Python {} has no virtualenv installed!'.format(sys.executable))
        pip_exe = os.path.dirname(sys.executable) + os.sep + 'Scripts' + os.sep + 'pip.exe'
        if not os.path.isfile(pip_exe):
            raise RuntimeError('pip is not available in your Python installation: {}. Aborting ...'.format(sys.executable))
        print('>>> Installing virtualenv dependency ...')
        pip_cmd = '{} install virtualenv'.format(pip_exe)
        process = subprocess.Popen(pip_cmd)
        process.wait()
        print('>>> virtualenv installed successfully!')

    root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    venv_folder = os.path.join(root_path, venv_name)

    if args.clean:
        if os.path.isdir(venv_folder):
            print('> Removing {} folder ...'.format(venv_folder))
            shutil.rmtree(venv_folder)

    venv_scripts = os.path.join(root_path, venv_name, 'Scripts')
    venv_python = os.path.join(venv_scripts, 'python.exe')
    if not os.path.isfile(venv_python):
        venv_cmd = 'virtualenv -p "{}" {}'.format(sys.executable, venv_name)
        process = subprocess.Popen(venv_cmd)
        process.wait()

    requirements_file = os.path.join(root_path, 'requirements.txt')
    if not os.path.isfile(requirements_file):
        raise RuntimeError('Impossible to install dependencies because requirements.txt was not found: {}'.format(requirements_file))

    venv_pip = os.path.join(venv_scripts, 'pip.exe')

    if args.update:
        pip_cmd = '"{}" install --upgrade -r "{}"'.format(venv_pip, requirements_file)
    else:
        pip_cmd = '"{}" install -r "{}"'.format(venv_pip, requirements_file)
    process = subprocess.Popen(pip_cmd)
    process.wait()

    if args.generate_launcher:
        installer_py = os.path.join(root_path, 'generate_launcher.py')
        if not os.path.isfile(installer_py):
            raise RuntimeError('Impossible to generate launcher because generate_launcher.py was not found: {}'.format(installer_py))
        installer_cmd = '"{}" "{}"'.format(venv_python, installer_py)
        if args.generate_spec:
            installer_cmd += ' --generate-spec'
        if args.windowed:
            installer_cmd += ' --windowed'
        if args.onefile:
            installer_cmd += ' --onefile'
        print('> Generating Launcher ...')
        process = subprocess.Popen(installer_cmd)
        process.wait()

    if args.clean_after:
        if os.path.isdir(venv_folder):
            print('> Removing {} folder ...'.format(venv_folder))
            shutil.rmtree(venv_folder)
