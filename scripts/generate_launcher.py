#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation to generate Artella Launcher using PyInstaller
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import sys
import json
import shutil
import argparse
import subprocess

paths_to_add = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'source')
]
for p in paths_to_add:
    if p not in sys.path:
        if not os.path.isdir(p):
            continue
        sys.path.append(p)


def cleanup():
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(json_path, 'r') as f:
        config_data = json.loads(f.read())

    project_name = config_data.get('PROJECT_NAME')
    launcher_name = config_data.get('LAUNCHER_NAME')

    root_dir = os.path.dirname(os.path.abspath(__file__))

    # Remove build temporary folder used by PyInstaller
    temp_build_folder = os.path.join(root_dir, 'build')
    if os.path.exists(temp_build_folder):
        print('Removing PyInstaller build folder: {}'.format(temp_build_folder))
        shutil.rmtree(temp_build_folder)

    # Rename generate exe
    exe_file = os.path.join(root_dir, 'dist', 'launcher.exe')
    if os.path.isfile(exe_file):
        new_exe_file = os.path.join(root_dir, 'dist', '{}.exe'.format(launcher_name))
        if exe_file != new_exe_file:
            os.rename(exe_file, new_exe_file)
            exe_file = new_exe_file

    # Move exe file to the root
    exe_file = os.path.join(root_dir, 'dist', '{}.exe'.format(launcher_name))
    if os.path.isfile(exe_file):
        to_dir = root_dir
        if os.path.isfile(os.path.join(to_dir, '{}.exe'.format(launcher_name))):
            print('Removing Current Generated {} Launcher EXE file'.format(project_name))
            os.remove(os.path.join(to_dir, '{}.exe'.format(launcher_name)))
        print('Moving {} Launcher EXE file from: {} to {}'.format(project_name, exe_file, to_dir))
        shutil.move(exe_file, to_dir)

    # Remove PyInstaller dist folder
    dist_folder = os.path.join(root_dir, 'dist')
    if os.path.exists(dist_folder):
        print('Removing PyInstaller dist folder: {}'.format(dist_folder))
        shutil.rmtree(dist_folder)

    # Remove __pycache__ folder (generated when using Python 3)
    pycache_folder = os.path.join(root_dir, '__pycache__')
    if os.path.exists(pycache_folder):
        print('Removing __pycache__ folder: {}'.format(pycache_folder))
        shutil.rmtree(pycache_folder)

    print(' ===> {} Launcher Executable generated successfully! <==='.format(project_name))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate Launcher')
    parser.add_argument('--generate-spec', required=False, default=False, action='store_true', help='Whether .spec file should be created or not')
    parser.add_argument('--windowed', required=False, default=False, action='store_true', help='Whether generated executable is windowed or not')
    parser.add_argument('--onefile', required=False, default=False, action='store_true', help='Whether generated executable is stored in a unique .exe or not')
    args = parser.parse_args()

    if args.generate_spec:
        print('> Generating spec file ...')
        cmd = '"{}" generate_spec.py'.format(sys.executable)
        if args.windowed:
            cmd += ' --windowed'
        if args.onefile:
            cmd += ' --onefile'

        print('Executing: {}'.format(cmd))

        process = subprocess.Popen(cmd)
        process.wait()

    spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'launcher.spec')
    if not os.path.isfile(spec_file):
        raise RuntimeError('Launcher Spec file does not exists. Please execute generate_launcher using --generate-spec argument to generate Launcher Spec File')

    pyinstaller_exe = os.path.join(os.path.dirname(sys.executable), 'pyinstaller.exe')
    if not os.path.isfile(pyinstaller_exe):
        pyinstaller_exe = os.path.join(os.path.dirname(sys.executable), 'Scripts', 'pyinstaller.exe')

    if not os.path.isfile(pyinstaller_exe):
        raise RuntimeError('pyinstaller.exe not found in Python Scripts folder: {}'.format(pyinstaller_exe))

    pyinstaller_cmd = '"{}" launcher.spec'.format(pyinstaller_exe)
    process = subprocess.Popen(pyinstaller_cmd)
    process.wait()

    cleanup()
