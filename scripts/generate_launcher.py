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


def is_windows():
    return sys.platform.startswith('win')


def is_mac():
    return sys.platform == 'darwin'


def is_linux():
    return 'linux' in sys.platform


class LauncherGenerator(object):
    def __init__(self, project_name, version, repository, app_path, clean_env, clean_env_after, update_requirements,
                 icon_path, splash_path, install_path, windowed, one_file, dev):

        self._project_name = project_name
        self._version = version
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
        self._install_path = install_path if install_path and os.path.isdir(install_path) else os.path.dirname(
            os.path.abspath(__file__))
        self._folder_name = os.path.splitext(os.path.basename(self._app_path))[0]
        self._exe_name = '{}.exe'.format(self._folder_name)
        self._spec_name = '{}.spec'.format(self._folder_name)
        self._dist_folder = os.path.join(self._install_path, 'dist')
        self._build_folder = os.path.join(self._install_path, 'build')

        os.chdir(self._install_path)

        self._cleanup()

        copied_files = self._copy_resources()

        try:
            if is_mac():
                self._check_brew()
            venv_info = self._setup_environment()
            if not venv_info:
                raise RuntimeError('Error while setting up virtual environment: {}!'.format(self._get_venv_name()))
            self._install_requirements(venv_info)

            self._generate_exe(venv_info)

            if self._clean_env_after:
                venv_folder = venv_info['venv_folder']
                if os.path.isdir(venv_folder):
                    shutil.rmtree(venv_folder)

            # self._cleanup()
        except Exception as exc:
            raise Exception(traceback.format_exc())
        finally:
            self._clean_resources(copied_files)

    def _get_clean_name(self):
        """
        Internal function that returns a clean version of the project name
        :return: str
        """

        return self._project_name.replace(' ', '').lower()

    def _get_venv_name(self):
        """
        Internal function that returns the name of the virtual environment
        :return: str
        """

        return '{}_dev'.format(self._get_clean_name())

    def _copy_resources(self):
        """
        Internal function that copies resources into resources folder
        :return: list(str)
        """

        copied_resources = list()

        paths_to_check = {
            self._get_default_splash_path(): self._splash_path,
            self._get_default_icon_path(): self._icon_path
        }

        for def_path, res_path in paths_to_check.items():
            if def_path != res_path:
                target_dir = os.path.dirname(def_path)
                splash_name = os.path.basename(res_path)
                new_path = os.path.join(target_dir, splash_name)
                if not os.path.isfile(new_path):
                    shutil.copy(res_path, new_path)
                    if os.path.isfile(new_path):
                        copied_resources.append(new_path)

        return copied_resources

    def _clean_resources(self, resources_to_clean):
        """
        Internal function that deletes all the given resource paths
        :param resources_to_clean: list(str)
        """

        for res in resources_to_clean:
            if res and os.path.isfile(res):
                os.remove(res)

    def _setup_environment(self):
        """
        Setup virtual environment for launcher generation
        :return: dict
        """

        if is_windows():
            return self._setup_environment_windows()
        elif is_mac():
            return self._setup_environment_mac()
        else:
            raise NotImplementedError('System Platform "{}" is not supported!'.format(sys.platform))

    def _setup_environment_windows(self):
        """
        Setup virtual environment for launcher generation in Windows
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

        venv_folder = os.path.join(self._install_path, self._get_venv_name())

        if self._clean_env:
            if os.path.isdir(venv_folder):
                print('> Removing {} folder ...'.format(venv_folder))
                shutil.rmtree(venv_folder)

        venv_scripts = os.path.join(self._install_path, self._get_venv_name(), 'Scripts')
        venv_python = os.path.join(venv_scripts, 'python.exe')
        if not os.path.isfile(venv_python):
            venv_cmd = 'virtualenv {}'.format(self._get_venv_name())
            process = subprocess.Popen(venv_cmd)
            process.wait()

        venv_info = {
            'root_path': self._install_path,
            'venv_folder': venv_folder,
            'venv_scripts': venv_scripts,
            'venv_python': venv_python
        }

        return venv_info

    def _setup_environment_mac(self):
        """
        Setup virtual environment for launcher generation in MacOS
        """

        path_env = os.environ['PATH']
        env_paths = path_env.split(':')
        virtual_env = None
        for env_path in env_paths:
            virtual_env = env_path + os.sep + 'virtualenv'
            if os.path.isfile(virtual_env):
                break

        if not virtual_env or not os.path.isfile(virtual_env):
            print('Python {} has no virtualenv installed!'.format(sys.executable))
            pip_exe = None
            for env_path in env_paths:
                pip_exe = env_path + os.sep + 'pip'
                if os.path.isfile(pip_exe):
                    break
            if not pip_exe or not os.path.isfile(pip_exe):
                raise RuntimeError(
                    'pip is not available in your Python installation: {}. Aborting ...'.format(sys.executable))
            print('>>> Installing virtualenv dependency ...')
            pip_cmd = '{} install virtualenv'.format(pip_exe)
            process = subprocess.Popen(pip_cmd)
            process.wait()
            print('>>> virtualenv installed successfully!')

        venv_folder = os.path.join(self._install_path, self._get_venv_name())

        if self._clean_env:
            if os.path.isdir(venv_folder):
                print('> Removing {} folder ...'.format(venv_folder))
                shutil.rmtree(venv_folder)

        venv_bin = os.path.join(self._install_path, self._get_venv_name(), 'bin')
        venv_python = os.path.join(venv_bin, 'python')
        if not os.path.isfile(venv_python):
            venv_cmd = 'virtualenv -p "{}" {}'.format(sys.executable, self._get_venv_name())
            process = subprocess.Popen(venv_cmd, shell=True)
            process.wait()

        venv_info = {
            'root_path': self._install_path,
            'venv_folder': venv_folder,
            'venv_scripts': venv_bin,
            'venv_python': venv_python
        }

        return venv_info

    def _check_brew(self):
        """
        Installs hombrevew for Mac if its not available
        """

        if not is_mac():
            return

        path_env = os.environ['PATH']
        env_paths = path_env.split(':')
        brew_path = None
        for env_path in env_paths:
            brew_path = env_path + os.sep + 'brew'
            if os.path.isfile(brew_path):
                break

        if not brew_path or not os.path.isfile(brew_path):
            raise Exception(
                'brew is not installed in your machine. Follow the instructions found here: https://brew.sh/')

    def _install_requirements(self, venv_info):
        """
        Installs requirements in virtual environment
        :param venv_info: dict
        """

        if is_windows():
            return self._install_requirements_windows(venv_info)
        elif is_mac():
            return self._install_requirements_mac(venv_info)
        else:
            raise NotImplementedError('System Platform "{}" is not supported!'.format(sys.platform))

    def _install_requirements_windows(self, venv_info):
        """
        Installs requirements in virtual environment in Windows
        """

        root_path = os.path.dirname(os.path.abspath(__file__))
        venv_scripts = venv_info['venv_scripts']

        print('> Installing requirements ...')
        if self._dev:
            requirements_file = os.path.join(root_path, 'requirements_dev_win.txt')
        else:
            requirements_file = os.path.join(root_path, 'requirements_win.txt')
        if not os.path.isfile(requirements_file):
            raise RuntimeError(
                'Impossible to install dependencies because requirements file was not found: {}'.format(
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

    def _install_requirements_mac(self, venv_info):
        """
        Installs requirements in virtual environment in MacOS
        """

        root_path = os.path.dirname(os.path.abspath(__file__))
        venv_scripts = venv_info['venv_scripts']

        print('> Installing requirements ...')
        if self._dev:
            requirements_file = os.path.join(root_path, 'requirements_dev_mac.txt')
        else:
            requirements_file = os.path.join(root_path, 'requirements_mac.txt')
        if not os.path.isfile(requirements_file):
            raise RuntimeError(
                'Impossible to install dependencies because requirements.txt was not found: {}'.format(
                    requirements_file))

        venv_pip = os.path.join(venv_scripts, 'pip')

        if self._update_requirements:
            pip_cmd = '"{}" install --upgrade -r "{}"'.format(venv_pip, requirements_file)
        else:
            pip_cmd = '"{}" install -r "{}"'.format(venv_pip, requirements_file)

        try:
            process = subprocess.Popen(pip_cmd, shell=True)
            process.wait()
        except Exception as e:
            raise RuntimeError(
                'Error while installing requirements from: {} | {} | {}'.format(
                    requirements_file, e, traceback.format_exc()))

    def _get_config_path(self):
        return os.path.join(self._install_path, 'config.json')

    def _get_launcher_script_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'launcher.py')

    def _get_default_app_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')

    def _get_updater_logging_path(self):
        logging_name = '__logging__.ini'
        logging_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), logging_name)
        if not os.path.isfile(logging_path):
            logging_path = os.path.join(os.path.dirname(sys.executable), logging_name)
            if not os.path.isfile(logging_path):
                if hasattr(sys, '_MEIPASS'):
                    logging_path = os.path.join(sys._MEIPASS, 'resources', logging_name)

        return logging_path

    def _get_resources_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

    def _get_default_icon_path(self):
        return os.path.join(self._get_resources_path(), 'artella_icon.ico')

    def _get_default_splash_path(self):
        return os.path.join(self._get_resources_path(), 'splash.png')

    def _cleanup(self):
        exe_path = os.path.join(self._install_path, '{}.exe'.format(self._project_name))
        spec_path = os.path.join(self._install_path, self._spec_name)
        folder_path = os.path.join(self._install_path, self._project_name)
        config_file = os.path.join(self._install_path, 'config.json')
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
            shutil.move(exe_path, os.path.join(self._install_path, '{}.exe'.format(self._project_name)))
        else:
            folder_path = os.path.join(self._dist_folder, self._folder_name)
            if os.path.isdir(folder_path):
                exe_path = os.path.join(folder_path, self._exe_name)
                if os.path.isfile(exe_path):
                    os.rename(exe_path, os.path.join(folder_path, '{}.exe'.format(self._project_name)))
                shutil.move(folder_path, os.path.join(self._install_path, self._project_name))
        if os.path.isdir(self._dist_folder):
            shutil.rmtree(self._dist_folder)
        if os.path.isdir(self._build_folder):
            shutil.rmtree(self._build_folder)

    def _generate_config_file(self):
        config_data = {
            'name': self._project_name,
            'version': self._version,
            'repository': self._repository,
            'splash': os.path.basename(self._splash_path),
            'icon': os.path.basename(self._icon_path)
        }

        config_path = self._get_config_path()
        with open(config_path, 'w') as config_file:
            json.dump(config_data, config_file)

    def _generate_spec_file(self, venv_info):
        """
        Generates spec file used by PyInstaller
        """

        if not is_windows() and not is_mac():
            return

        python_exe = venv_info['venv_python']
        if is_windows():
            makespec_exe = os.path.join(os.path.dirname(python_exe), 'pyi-makespec.exe')
            if not os.path.isfile(makespec_exe):
                makespec_exe = os.path.join(os.path.dirname(python_exe), 'Scripts', 'pyi-makespec.exe')
        elif is_mac():
            makespec_exe = os.path.join(os.path.dirname(python_exe), 'pyi-makespec')
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
            if is_windows():
                process = subprocess.Popen(spec_cmd)
            elif is_mac():
                process = subprocess.Popen(spec_cmd, shell=True)
            process.wait()
        except Exception as e:
            raise RuntimeError('Error while generate Launcher Spec file | {} - {}'.format(e, traceback.format_exc()))

        spec_file = os.path.join(self._install_path, spec_name)
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
            self._get_default_icon_path(),
            self._get_config_path(),
            self._get_launcher_script_path(),
            self._get_resources_path(),
            self._get_updater_logging_path()
        ]

        for data in data_files:
            cmd += '{}="{}{}resources" '.format(add_data_cmd, data, os.pathsep)

        return cmd

    def _generate_exe(self, venv_info):
        """
        Generates launcher executable
        """

        if not is_windows() and not is_mac():
            return

        python_exe = venv_info['venv_python']

        self._generate_config_file()
        specs_file_name = self._generate_spec_file(venv_info)

        pyinstaller_exe = None
        if is_windows():
            pyinstaller_exe = os.path.join(os.path.dirname(python_exe), 'pyinstaller.exe')
            if not os.path.isfile(pyinstaller_exe):
                pyinstaller_exe = os.path.join(os.path.dirname(python_exe), 'Scripts', 'pyinstaller.exe')
        elif is_mac():
            pyinstaller_exe = os.path.join(os.path.dirname(python_exe), 'pyinstaller')
        if not pyinstaller_exe or not os.path.isfile(pyinstaller_exe):
            raise RuntimeError('pyinstaller.exe not found in Python Scripts folder: {}'.format(pyinstaller_exe))

        pyinstaller_cmd = '"{}" --clean {}'.format(pyinstaller_exe, specs_file_name)

        try:
            if is_windows():
                process = subprocess.Popen(pyinstaller_cmd)
            elif is_mac():
                process = subprocess.Popen(pyinstaller_cmd, shell=True)
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
        '--version', required=False, default='0.0.0', help='Version of the Launcher Tool')
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
        '--install-path', required=False, default=None,
        help='Path where launcher will be generated')
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
        version=args.version,
        repository=args.repository,
        app_path=args.app_path,
        clean_env=args.clean,
        clean_env_after=args.clean_after,
        update_requirements=args.update_requirements,
        icon_path=args.icon_path,
        splash_path=args.splash_path,
        install_path=args.install_path,
        windowed=args.windowed,
        one_file=args.onefile,
        dev=args.dev
    )
