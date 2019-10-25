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
import json
import shutil
import argparse
import traceback
import subprocess


class LauncherGenerator(object):
    def __init__(self, project_name, repository, app_path, clean_env, clean_env_after, update_requirements,
                 icon_path, splash_path, windowed, one_file, dev):

        self._project_name = project_name
        self._repository = repository
        self._clean_env = clean_env
        self._clean_env_after = clean_env_after
        self._update_requirements = update_requirements
        self._windowed = windowed
        self._one_file = one_file
        self._dev = dev
        self._app_path = app_path if app_path and os.path.isfile(app_path) else self._get_default_app_path()
        self._icon_path = icon_path if icon_path and os.path.isfile(icon_path) else self._get_default_icon_path()
        self._splash_path = splash_path if splash_path and os.path.isfile(
            splash_path) else self._get_default_splash_path()
        self._folder_name = os.path.splitext(os.path.basename(self._app_path))[0]
        self._exe_name = '{}.exe'.format(self._folder_name)
        self._spec_name = '{}.spec'.format(self._folder_name)
        self._dist_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
        self._build_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')

        self._cleanup()

        venv_info = self._setup_environment()
        if not venv_info:
            raise RuntimeError('Error while setting up virtual environment: {}!'.format(self._get_venv_name()))
        self._install_requirements(venv_info)

        self._generate_exe(venv_info)

        if self._clean_env_after:
            venv_folder = venv_info['venv_folder']
            if os.path.isdir(venv_folder):
                shutil.rmtree(venv_folder)

        self._cleanup()

    def _get_clean_name(self):
        return self._project_name.replace(' ', '').lower()

    def _get_venv_name(self):
        return '{}_dev'.format(self._get_clean_name())

    def _setup_environment(self):
        """
        Setup virtual environment for launcher generation
        :return: dict
        """

        virtual_env = os.path.dirname(sys.executable) + os.sep + 'Scripts' + os.sep + 'virtualenv.exe'
        if not os.path.isfile(virtual_env):
            print('Python {} has no virtualenv installed!'.format(sys.executable))
            pip_exe = os.path.dirname(sys.executable) + os.sep + 'Scripts' + os.sep + 'pip.exe'
            if not os.path.isfile(pip_exe):
                raise RuntimeError(
                    'pip is not available in your Python installation: {}. Aborting ...'.format(sys.executable))
            print('>>> Installing virtualenv dependency ...')
            pip_cmd = '{} install virtualenv'.format(pip_exe)
            process = subprocess.Popen(pip_cmd)
            process.wait()
            print('>>> virtualenv installed successfully!')

        root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        venv_folder = os.path.join(root_path, self._get_venv_name())

        if self._clean_env:
            if os.path.isdir(venv_folder):
                print('> Removing {} folder ...'.format(venv_folder))
                shutil.rmtree(venv_folder)

        venv_scripts = os.path.join(root_path, self._get_venv_name(), 'Scripts')
        venv_python = os.path.join(venv_scripts, 'python.exe')
        if not os.path.isfile(venv_python):
            venv_cmd = 'virtualenv -p "{}" {}'.format(sys.executable, self._get_venv_name())
            process = subprocess.Popen(venv_cmd)
            process.wait()

        venv_info = {
            'root_path': root_path,
            'venv_folder': venv_folder,
            'venv_scripts': venv_scripts,
            'venv_python': venv_python
        }

        return venv_info

    def _install_requirements(self, venv_info):
        """
        Intstall requirements in virtual environment
        :param venv_info: dict
        """

        root_path = venv_info['root_path']
        venv_scripts = venv_info['venv_scripts']

        print('> Installing requirements ...')
        if self._dev:
            requirements_file = os.path.join(root_path, 'requirements_dev.txt')
        else:
            requirements_file = os.path.join(root_path, 'requirements.txt')
        if not os.path.isfile(requirements_file):
            raise RuntimeError(
                'Impossible to install dependencies because requirements.txt was not found: {}'.format(
                    requirements_file))

        venv_pip = os.path.join(venv_scripts, 'pip.exe')

        if self._update_requirements:
            pip_cmd = '"{}" install --upgrade -r "{}"'.format(venv_pip, requirements_file)
        else:
            pip_cmd = '"{}" install -r "{}"'.format(venv_pip, requirements_file)

        try:
            process = subprocess.Popen(pip_cmd)
            process.wait()
        except Exception as e:
            raise RuntimeError(
                'Error while installing requirements from: {} | {} | {}'.format(
                    requirements_file, e, traceback.format_exc()))

    def _get_config_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

    def _get_launcher_script_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'launcher.py')

    def _get_default_app_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')

    def _get_resources_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

    def _get_default_icon_path(self):
        return os.path.join(self._get_resources_path(), 'artella_icon.ico')

    def _get_default_splash_path(self):
        return os.path.join(self._get_resources_path(), 'splash.png')

    def _cleanup(self):
        exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '{}.exe'.format(self._project_name))
        spec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self._spec_name)
        folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self._project_name)
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        if os.path.isfile(spec_path):
            os.remove(spec_path)
        if os.path.isfile(config_file):
            os.remove(config_file)
        if os.path.isfile(exe_path):
            os.remove(exe_path)
        if os.path.isdir(folder_path):
            shutil.rmtree(folder_path)

        exe_path = os.path.join(self._dist_folder, self._exe_name)
        if os.path.isfile(exe_path):
            shutil.move(exe_path, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               '{}.exe'.format(self._project_name)))
        else:
            folder_path = os.path.join(self._dist_folder, self._folder_name)
            if os.path.isdir(folder_path):
                exe_path = os.path.join(folder_path, self._exe_name)
                if os.path.isfile(exe_path):
                    os.rename(exe_path, os.path.join(folder_path, '{}.exe'.format(self._project_name)))
                shutil.move(folder_path, os.path.join(os.path.dirname(os.path.abspath(__file__)), self._project_name))
        if os.path.isdir(self._dist_folder):
            shutil.rmtree(self._dist_folder)
        if os.path.isdir(self._build_folder):
            shutil.rmtree(self._build_folder)

    def _generate_config_file(self):
        config_data = {
            'name': self._project_name,
            'repository': self._repository,
            'splash': self._splash_path
        }

        config_path = self._get_config_path()
        with open(config_path, 'w') as config_file:
            json.dump(config_data, config_file)

    def _generate_launcher_script(self):
        """
        Internal function that creates the output file used to generate launcher app
        :return: str
        """

        launcher_script = """#!/usr/bin/env python
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
    parser.add_argument('--install-path', required=True)
    args = parser.parse_args()

    with application() as app:
        from {0} import launcher
        launcher.init()
        from {0}.launcher import launcher
        launcher.run(install_path=args.install_path)
""".format(self._get_clean_name())

        script_path = self._get_launcher_script_path()
        with open(script_path, 'w') as script_file:
            script_file.write(launcher_script)

        return script_path

    def _generate_spec_file(self, venv_info):
        python_exe = venv_info['venv_python']
        makespec_exe = os.path.join(os.path.dirname(python_exe), 'pyi-makespec.exe')
        if not os.path.isfile(makespec_exe):
            makespec_exe = os.path.join(os.path.dirname(python_exe), 'Scripts', 'pyi-makespec.exe')
        if not os.path.isfile(makespec_exe):
            raise RuntimeError('pyi-makespec.exe not found in Python Scripts folder: {}'.format(makespec_exe))

        spec_cmd = '"{}"'.format(makespec_exe)
        if self._one_file:
            spec_cmd += ' --onefile'
        if self._windowed:
            spec_cmd += ' --windowed'

        spec_cmd += ' --icon={}'.format(self._icon_path)

        hidden_imports_cmd = self._retrieve_hidden_imports()
        spec_cmd += ' {}'.format(hidden_imports_cmd)

        data_cmd = self._retrieve_data()
        spec_cmd += ' {}'.format(data_cmd)

        spec_cmd += "{}".format(self._app_path)
        spec_name = '{}.spec'.format(os.path.splitext(os.path.basename(self._app_path))[0])

        try:
            process = subprocess.Popen(spec_cmd)
            process.wait()
        except Exception as e:
            raise RuntimeError('Error while generate Launcher Spec file | {} - {}'.format(e, traceback.format_exc()))

        spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), spec_name)
        if not os.path.isfile(spec_file):
            raise RuntimeError(
                'Launcher Spec file does not exists. Please execute generate_launcher using --generate-spec argument'
                ' to generate Launcher Spec File')

        return spec_name

    def _retrieve_hidden_imports(self):
        """
        Returns cmd that defines the hidden imports
        :return: str
        """

        hidden_import_cmd = '--hidden-import'
        hidden_imports = ['pythonjsonlogger', 'pythonjsonlogger.jsonlogger', 'Qt']
        cmd = ''
        for mod in hidden_imports:
            cmd += '{} {} '.format(hidden_import_cmd, mod)

        return cmd

    def _retrieve_data(self):

        cmd = ''
        add_data_cmd = '--add-data'
        data_files = [
            self._get_default_splash_path(),
            self._get_config_path(),
            self._get_launcher_script_path(),
            self._get_resources_path()
        ]

        for data in data_files:
            cmd += '{}="{};resources" '.format(add_data_cmd, data)

        return cmd

    def _generate_exe(self, venv_info):
        python_exe = venv_info['venv_python']

        self._generate_config_file()
        self._generate_launcher_script()
        specs_file_name = self._generate_spec_file(venv_info)

        pyinstaller_exe = os.path.join(os.path.dirname(python_exe), 'pyinstaller.exe')
        if not os.path.isfile(pyinstaller_exe):
            pyinstaller_exe = os.path.join(os.path.dirname(python_exe), 'Scripts', 'pyinstaller.exe')
        if not os.path.isfile(pyinstaller_exe):
            raise RuntimeError('pyinstaller.exe not found in Python Scripts folder: {}'.format(pyinstaller_exe))

        pyinstaller_cmd = '"{}" --clean {}'.format(pyinstaller_exe, specs_file_name)

        try:
            process = subprocess.Popen(pyinstaller_cmd)
            process.wait()
        except Exception as e:
            raise RuntimeError(
                'Error while generating Launcher: \n\tPyInstaller: {}\n\tSpecs File Name: {}\n{} | {}'.format(
                    pyinstaller_exe,
                    specs_file_name,
                    e, traceback.format_exc()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Python Virtual Environment to generate launcher')
    parser.add_argument(
        '--name', required=False, default='artella', help='Name of the Python environment')
    parser.add_argument(
        '--repository', required=False, default='', help='URL where GitHub deployment repository is located')
    parser.add_argument(
        '--app-path', required=False, default=None, help='File Path where app file is located')
    parser.add_argument(
        '--clean',
        required=False, default=False, action='store_true',
        help='Whether to delete already created venv')
    parser.add_argument(
        '--clean-after',
        required=False, default=False, action='store_true',
        help='Whether to delete venv after process is completed')
    parser.add_argument(
        '--icon-path', required=False, default=None,
        help='Path where launcher icon is located')
    parser.add_argument(
        '--splash-path', required=False, default=None,
        help='Path where splash image is located')
    parser.add_argument(
        '--update-requirements',
        required=False, default=True, action='store_true',
        help='Whether update venv requirements')
    parser.add_argument(
        '--windowed',
        required=False, default=False, action='store_true',
        help='Whether generated executable is windowed or not')
    parser.add_argument(
        '--onefile',
        required=False, default=False, action='store_true',
        help='Whether generated executable is stored in a unique .exe or not')
    parser.add_argument(
        '--dev',
        required=False, default=False, action='store_true',
        help='Whether dev or production launcher should be build')
    args = parser.parse_args()

    launcher_generator = LauncherGenerator(
        project_name=args.name,
        repository=args.repository,
        app_path=args.app_path,
        clean_env=args.clean,
        clean_env_after=args.clean_after,
        update_requirements=args.update_requirements,
        icon_path=args.icon_path,
        splash_path=args.splash_path,
        windowed=args.windowed,
        one_file=args.onefile,
        dev=args.dev
    )
