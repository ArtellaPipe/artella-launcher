import os
import re
import sys
import json
import shutil
import appdirs
import logging
import zipfile
import tarfile
import argparse
import platform
import requests
import traceback
import subprocess
import webbrowser
from pathlib2 import Path
from bs4 import BeautifulSoup
from backports import tempfile
from packaging.version import Version, InvalidVersion
try:
    from urlparse import urlparse
except Exception:
    from urllib.parse import urlparse
try:
    from urllib2 import Request, urlopen
except ImportError:
    from urllib.request import Request, urlopen

try:
    import PySide
    from PySide.QtCore import *
    from PySide.QtGui import *
except ImportError:
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
    from PySide.QtGui import *

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


class ArtellaUpdater(QWidget, object):
    def __init__(
            self, project_name, deployment_repository, environment='production', documentation_url=None,
            deploy_tag=None, install_env_var=None, requirements_file_name=None,
            force_venv=False, splash_path=None,
            parent=None):
        super(ArtellaUpdater, self).__init__(parent=parent)

        self._config_data = self._read_config()

        self._project_name = project_name if project_name else self._get_config('name')
        self._repository = deployment_repository if deployment_repository else self._get_config('repository')
        self._splash_path = splash_path if splash_path and os.path.isfile(splash_path) else self._get_config('splash')
        self._force_venv = force_venv
        self._venv_info = dict()

        self._setup_logger()
        self._setup_config()

        self._install_path = None
        self._requirements_path = None
        self._documentation_url = documentation_url if documentation_url else self._get_default_documentation_url()
        self._install_env_var = install_env_var if install_env_var else self._get_default_install_env_var()
        self._requirements_file_name = requirements_file_name if requirements_file_name else 'requirements.txt'
        self._deploy_tag = deploy_tag if deploy_tag else self._get_latest_deploy_tag()

        self._setup_ui()

        self.init()

    @property
    def project_name(self):
        return self._project_name

    @property
    def repository(self):
        return self._repository

    @property
    def install_env_var(self):
        return self._install_env_var

    def get_clean_name(self):
        """
        Return name of the project without spaces and lowercase
        :return: str
        """

        return self._project_name.replace(' ', '').lower()

    def get_current_os(self):
        """
        Return current OS the scrip is being executed on
        :return:
        """

        os_platform = platform.system()
        if os_platform == 'Windows':
            return 'Windows'
        elif os_platform == 'Darwin':
            return 'MacOS'
        elif os_platform == 'Linux':
            return 'Linux'
        else:
            raise Exception('No valid OS platform detected: {}!'.format(os_platform))

    def get_config_data(self):
        """
        Returns data in the configuration file
        :return: dict
        """

        data = dict()

        config_path = self._get_config_path()
        if not os.path.isfile(config_path):
            return data

        with open(config_path, 'r') as config_file:
            try:
                data = json.load(config_file)
            except Exception:
                data = dict()

        return data

    def is_python_installed(self):
        """
        Returns whether current system has Python installed or not
        :return: bool
        """

        process = subprocess.Popen(['python', '-c', 'quit()'], stdout=subprocess.PIPE, shell=True)
        process.wait()

        return True if process.returncode == 0 else False

    def is_pip_installed(self):
        """
        Returns whether pip is installed or not
        :return: bool
        """

        process = subprocess.Popen(['pip', '-V'], stdout=subprocess.PIPE, shell=True)
        process.wait()

        return True if process.returncode == 0 else False

    def is_virtualenv_installed(self):
        """
        Returns whether virtualenv is intsalled or not
        :return: bool
        """

        process = subprocess.Popen(['virtualenv', '--version'], stdout=subprocess.PIPE, shell=True)
        process.wait()

        return True if process.returncode == 0 else False

    def _read_config(self):
        """
        Internal function that retrieves config data stored in executable
        :return: dict
        """

        data = {}
        config_file_name = 'config.json'
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'scripts', config_file_name)
        if not os.path.isfile(config_path):
            config_path = os.path.join(os.path.dirname(sys.executable), 'resources', config_file_name)
            if not os.path.isfile(config_path):
                if hasattr(sys, '_MEIPASS'):
                    config_path = os.path.join(sys._MEIPASS, 'resources', config_file_name)

        if not os.path.isfile(config_path):
            return data

        try:
            with open(config_path) as config_file:
                data = json.load(config_file)
        except RuntimeError:
            pass

        return data

    def _get_config(self, config_name):
        """
        Returns configuration parameter stored in configuration, if exists
        :param config_name: str
        :return: str
        """

        if not self._config_data:
            return None

        return self._config_data.get(config_name, None)

    def _set_splash_text(self, new_text):
        self._progress_text.setText(new_text)
        QApplication.instance().processEvents()

    def _setup_ui(self):
        splash_pixmap = QPixmap(self._splash_path)
        self._splash = QSplashScreen(splash_pixmap)
        self._splash.setWindowFlags(Qt.FramelessWindowHint)
        self._splash.setEnabled(False)
        splash_layout = QVBoxLayout()
        splash_layout.setContentsMargins(5, 2, 5, 2)
        splash_layout.setSpacing(2)
        splash_layout.setAlignment(Qt.AlignBottom)
        self._splash.setLayout(splash_layout)

        self._install_path_lbl = QLabel()
        self._progress_text = QLabel('Setting {} ...'.format(self._project_name.title()))
        self._progress_text.setAlignment(Qt.AlignCenter)
        self._progress_text.setStyleSheet("QLabel { background-color : rgba(0, 0, 0, 180); color : white; }")
        font = self._progress_text.font()
        font.setPointSize(10)
        self._progress_text.setFont(font)

        install_path_layout = QHBoxLayout()
        install_path_layout.addWidget(self._install_path_lbl)
        install_path_layout.addItem(QSpacerItem(10, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        splash_layout.addLayout(install_path_layout)
        splash_layout.addWidget(self._progress_text)

        self._splash.show()
        self._splash.raise_()

    def _setup_environment(self):

        if not self._install_path:
            LOGGER.error('Impossible to setup virtual environment because install path is not defined!')
            return False

        LOGGER.info("Setting Virtual Environment")
        venv_path = self._get_venv_folder_path()
        if self._force_venv or not os.path.isdir(venv_path):
            self._create_venv(force=True)

        root_path = os.path.dirname(venv_path)
        venv_scripts = os.path.join(venv_path, 'Scripts')
        venv_python = os.path.join(venv_scripts, 'python.exe')
        pip_exe = os.path.join(venv_scripts, 'pip.exe')

        venv_info = dict()
        venv_info['root_path'] = root_path
        venv_info['venv_folder'] = venv_path
        venv_info['venv_scripts'] = venv_scripts
        venv_info['venv_python'] = venv_python
        venv_info['pip_exe'] = pip_exe

        self._venv_info = venv_info

        LOGGER.info("Virtual Environment Info: {}".format(venv_info))

        # TODO: Check that all info contained in venv_info is valid

        return True

    def _get_app_name(self):
        """
        Returns name of the app
        :return: str
        """

        return '{}_app'.format(self.get_clean_name())

    def _get_app_folder(self):
        """
        Returns folder where app data is located
        :return: str
        """

        logger_name = self._get_app_name()
        logger_path = os.path.dirname(appdirs.user_data_dir(logger_name))
        if not os.path.isdir(logger_path):
            os.makedirs(logger_path)

        if not os.path.isdir(logger_path):
            QMessageBox.critical(
                self,
                'Impossible to retrieve app data folder',
                'Impossible to retrieve app data folder.\n\n'
                'Please contact TD.'
            )
            return

        return logger_path

    def _check_setup(self):
        """
        Internal function that checks if environment is properly configured
        """

        self._set_splash_text('Checking if Python is installed ...')

        if not self.is_python_installed():
            LOGGER.warning('No Python Installation found!')
            QMessageBox.warning(
                self,
                'No Python Installation found in {}'.format(self.get_current_os()),
                'No valid Python installation found in your computer.\n\n'
                'Please follow instructions in {0} Documentation to install Python in your computer\n\n'
                'Click "Ok" to open {0} Documentation in your web browser'.format(self._project_name)
            )
            webbrowser.open(self._get_default_documentation_url())
            return False

        self._set_splash_text('Checking if pip is installed ...')

        if not self.is_pip_installed():
            LOGGER.warning('No pip Installation found!')
            QMessageBox.warning(
                self,
                'No pip Installation found in {}'.format(self.get_current_os()),
                'No valid pip installation found in your computer.\n\n'
                'Please follow instructions in {0} Documentation to install Python in your computer\n\n'
                'Click "Ok" to open {0} Documentation in your web browser'.format(self._project_name)
            )
            webbrowser.open(self._get_default_documentation_url())
            return False

        self._set_splash_text('Checking if virtualenv is installed ...')

        if not self.is_virtualenv_installed():
            LOGGER.warning('No virtualenv Installation found!')
            LOGGER.info('Installing virtualenv ...')
            process = subprocess.Popen(['pip', 'install', 'virtualenv'], stdout=subprocess.PIPE, shell=True)
            process.wait()
            if not self.is_virtualenv_installed():
                LOGGER.error('Impossible to install virtualenv using pip.')
                QMessageBox.warning(
                    self,
                    'Impossible to install virtualenv in {}'.format(self.get_current_os()),
                    'Was not possible to install virtualenv in your computer.\n\n'
                    'Please contact your project TD.'
                )
                return False
            LOGGER.info('virtualenv installed successfully!')

        return True

    def init(self):
        """
        Internal function that initializes Artella App
        """

        valid_check = self._check_setup()
        if not valid_check:
            return

        install_path = self._set_installation_path()
        if not install_path:
            return
        self._install_path_lbl.setText('Install Path: {}'.format(install_path))

        valid_venv = self._setup_environment()
        if not valid_venv:
            return
        if not self._venv_info:
            LOGGER.warning('No Virtual Environment info retrieved ...')
            return
        valid_install = self._setup_deployment()
        if not valid_install:
            return

        self._launch()

        self._splash.close()

    def _launch(self):

        if not self._venv_info:
            LOGGER.warning(
                'Impossible to launch {} Launcher because Virtual Environment Setup is not valid!'.format(
                    self._project_name))
            return False

        script_to_launch = self._create_launcher_script()

        py_exe = self._venv_info['venv_python']

        # cmd = '"{}" -c "import artellapipe; print(artellapipe);"'.format(py_exe)
        # process = subprocess.call(cmd, shell=True)

    def _create_launcher_script(self):
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

from Qt.QtWidgets import QApplication

if __name__ == '__main__':
    app = QApplication(sys.argv)
    from {0} import launcher
    launcher.init()
    from {0}.launcher import launcher
    launcher.run()
""".format(self.get_clean_name())

        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '{}_launcher.py'.format(self.get_clean_name()))
        with open(script_path, 'w') as script_file:
            script_file.write(launcher_script)

        return script_path

    def _check_installation_path(self, install_path):
        """
        Returns whether or not given path is valid
        :param install_path: str
        :return: bool
        """

        if not install_path or not os.path.isdir(install_path):
            return False

        return True

    def _set_installation_path(self):
        """
        Returns installation path is if it already set by user; Otherwise a dialog to select it will appear
        :return: str
        """

        path_updated = False
        install_path = self._get_installation_path()
        if not install_path or not os.path.isdir(install_path):
            self._set_splash_text('Select {} installation folder ...'.format(self._project_name))
            install_path = QFileDialog.getExistingDirectory(
                None, 'Select Installation Path for {}'.format(self._project_name))
            if not install_path:
                LOGGER.info('Installation cancelled by user')
                QMessageBox.information(
                    self,
                    'Installation cancelled',
                    'Installation cancelled by user')
                return False
            if not os.path.isdir(install_path):
                LOGGER.error('Selected Path does not exists!')
                QMessageBox.information(
                    self,
                    'Selected Path does nto exists',
                    'Selected Path: "{}" does not exists. '
                    'Installation cancelled!'.foramt(install_path))
                return False
            path_updated = True

        self._set_splash_text('Checking if Install Path is valid ...')
        LOGGER.info('>>>>>> Checking Install Path: {}'.format(install_path))
        valid_path = self._check_installation_path(install_path)
        if not valid_path:
            LOGGER.warning('Selected Install Path is not valid!')
            return

        if path_updated:
            self._set_splash_text('Registering new intall path ...')
            valid_update_config = self._set_config(self.install_env_var, install_path)
            if not valid_update_config:
                return

        self._set_splash_text('Install Path: {}'.format(install_path))
        LOGGER.info('>>>>>> Install Path: {}'.format(install_path))

        self._install_path = install_path

        return install_path

    def _setup_logger(self):
        """
        Setup logger used by the app
        """

        logger_name = self._get_app_name()
        logger_path = self._get_app_folder()
        logger_file = os.path.normpath(os.path.join(logger_path, '{}.log'.format(logger_name)))

        fh = logging.FileHandler(logger_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        LOGGER.addHandler(fh)

        print('{} Logger: "{}"'.format(self._project_name, logger_file))
        LOGGER.info('\n\n\n')
        LOGGER.info("=" * 50)
        LOGGER.debug('Starting {} App'.format(self._project_name))
        LOGGER.info("=" * 50)

    def _clean_old_config(self):
        """
        Function used to clean
        """

        current_os = self.get_current_os()

        if current_os == 'Windows':
            config_directory = Path(os.getenv('APPDATA') or '~')
        elif current_os == 'MacOS':
            config_directory = Path('~', 'Library', 'Preferences')
        else:
            config_directory = Path(os.getenv('XDG_CONFIG_HOME') or '~/.config')

        old_config_path = config_directory.joinpath(Path('{}/.config'.format(self.get_clean_name())))
        if old_config_path.exists():
            LOGGER.info('Old Configuration found in "{}". Removing ...'.format(str(old_config_path)))
            try:
                os.remove(str(old_config_path))
            except RuntimeError as exc:
                LOGGER.error('Impossible to remove old configuration file: {} | {}'.format(exc, traceback.format_exc()))
                return False
            LOGGER.info('Old Configuration file removed successfully!')

        return True

    def _setup_config(self):
        """
        Internal function that creates an empty configuration file if it is not already created
        :return: str
        """

        self._clean_old_config()

        config_file = self._get_config_path()
        if not os.path.isfile(config_file):
            LOGGER.info('Creating {} App Configuration File: {}'.format(self._project_name, config_file))
            with open(config_file, 'w') as cfg:
                json.dump({}, cfg)
            if not os.path.isfile(config_file):
                QMessageBox.critical(
                    self,
                    'Impossible to create configuration file',
                    'Impossible to create configuration file.\n\n'
                    'Please contact TD.'
                )
                return

        LOGGER.info('Configuration File found: "{}"'.format(config_file))

        return config_file

    def _get_installation_path(self):
        """
        Returns current installation path stored in config file
        :return: str
        """

        config_data = self.get_config_data()
        install_path = config_data.get(self.install_env_var, '')

        return install_path

    def _get_default_documentation_url(self):
        """
        Internal function that returns a default value for the documentation URL taking into account the project name
        :return: str
        """

        return 'https://{}-short-film.github.io/{}-docs/pipeline/'.format(self._project_name, self.get_clean_name())

    def _get_deploy_repository_url(self, release=False):
        """
        Internal function that returns a default path for the deploy repository taking int account the project name
        :param release: bool, Whether to retrieve releases path or the package to download
        :return: str
        """

        if release:
            return 'https://github.com/{}/releases'.format(self._repository)
        else:
            return 'https://github.com/{}/archive/{}.tar.gz'.format(self._repository, self._deploy_tag)

    def _get_latest_deploy_tag(self, sniff=True, validate=True, format='version', pre=False):
        """
        Returns last deployed version of the given repository in GitHub
        :return: str
        """

        def sanitize_version(version):
            """extract what appears to be the version information"""
            s = re.search(r'([0-9]+([.][0-9]+)+(rc[0-9]?)?)', version)
            if s:
                return s.group(1)
            else:
                return version.strip()

        version = None
        description = None
        data = None

        repository = self._get_deploy_repository_url(release=True)
        if not repository:
            LOGGER.error(
                '> Project {} GitHub repository is not valid! {}'.format(self._project_name.title(), repository))
            return None

        if repository.startswith('https://github.com/'):
            repository = "/".join(repository.split('/')[3:5])

        if sniff:
            release_url = "https://github.com/{}/releases".format(repository)
            response = requests.get(release_url, headers={'Connection': 'close'})
            html = response.text
            LOGGER.debug('Parsing HTML of {} GitHub release page ...'.format(self._project_name.title()))

            soup = BeautifulSoup(html, 'lxml')

            r = soup.find(class_='release-entry')
            while r:
                break_out = False
                if 'release-timeline-tags' in r['class']:
                    for release in r.find_all(class_='release-entry', recursive=False):
                        release_a = release.find("a")
                        if not release_a:
                            continue
                        the_version = release_a.text
                        the_version = sanitize_version(the_version)
                        if validate:
                            try:
                                LOGGER.debug("Trying version {}.".format(the_version))
                                v = Version(the_version)
                                if not v.is_prerelease or pre:
                                    LOGGER.debug("Good version {}.".format(the_version))
                                    version = the_version
                                    break_out = True
                                    break
                            except InvalidVersion:
                                # move on to next thing to parse it
                                LOGGER.error("Encountered invalid version {}.".format(the_version))
                        else:
                            version = the_version
                            break
                    if break_out:
                        break
                else:
                    LOGGER.debug("Inside formal release")
                    # formal release
                    if pre:
                        label_latest = r.find(class_='label-prerelease', recursive=False)
                    else:
                        label_latest = r.find(class_='label-latest', recursive=False)
                    if label_latest:
                        the_version = r.find(class_='css-truncate-target').text
                        the_version = sanitize_version(the_version)
                        # check if version is ok and not a prerelease; move on to next tag otherwise
                        if validate:
                            try:
                                v = Version(the_version)
                                if not v.is_prerelease or pre:
                                    version = the_version
                                    # extra info for json output
                                    if format == 'json':
                                        description = r.find(class_='markdown-body')
                                        if not description:
                                            description = r.find(class_='commit-desc')
                                            if description:
                                                description = description.text
                                    break
                                else:
                                    LOGGER.debug("Found a pre-release version: {}. Trying next.".format(the_version))
                            except InvalidVersion:
                                # move on to next thing to parse it
                                LOGGER.error("Encountered invalid version {}.".format(the_version))
                        else:
                            version = the_version
                            break

                r = r.find_next_sibling(class_='release-entry', recursive=False)

        if not version:
            LOGGER.error(
                'Impossible to retrieve {} lastest release version from GitHub!'.format(self._project_name.title()))
            return None

        if validate:
            try:
                Version(version)
            except InvalidVersion:
                LOGGER.error('Got invalid version: {}'.format(version))
                return None

        # return the release if we've reached far enough:
        if format == 'version':
            return version
        elif format == 'json':
            if not data:
                data = {}
            if description:
                description = description.strip()
            data['version'] = version
            data['description'] = description
            return json.dumps(data)

    def _get_default_install_env_var(self):
        """
        Internal function that returns a default env var
        :return: str
        """

        return '{}_install'.format(self.get_clean_name())

    def _get_config_path(self):
        """
        Internal function that returns path where configuration file is located
        :return: str
        """

        config_name = self._get_app_name()
        config_path = self._get_app_folder()
        config_file = os.path.normpath(os.path.join(config_path, '{}.cfg'.format(config_name)))

        return config_file

    def _set_config(self, config_name, config_value):
        """
        Sets configuration and updates the file
        :param config_name: str
        :param config_value: object
        """

        config_path = self._get_config_path()
        if not os.path.isfile(config_path):
            LOGGER.warning(
                'Impossible to update configuration file because it does not exists: "{}"'.format(config_path))
            return False

        config_data = self.get_config_data()
        config_data[config_name] = config_value
        with open(config_path, 'w') as config_file:
            json.dump(config_data, config_file)

        return True

    def _create_venv(self, force=False):
        """
        Internal function that creates virtual environment
        :param force: bool
        :return: bool
        """

        venv_path = self._get_venv_folder_path()

        if self._check_venv_folder_exists() and not force:
            LOGGER.info('Virtual Environment already exists: "{}"'.format(venv_path))
            return True

        if force and self._check_venv_folder_exists() and os.path.isdir(venv_path):
            LOGGER.info('Forcing the removal of Virtual Environment folder: "{}"'.format(venv_path))
            self._set_splash_text('Removing already existing virtual environment ...')
            shutil.rmtree(venv_path)

        self._set_splash_text('Creating Virtual Environment: "{}"'.format(venv_path))
        process = subprocess.Popen(['virtualenv', venv_path], stdout=subprocess.PIPE, shell=True)
        process.wait()

        return True if process.returncode == 0 else False

    def _get_venv_folder_path(self):
        """
        Returns path where virtual environment folder should be located
        :return: str
        """

        if not self._install_path:
            return

        return os.path.normpath(os.path.join(self._install_path, self.get_clean_name()))

    def _check_venv_folder_exists(self):
        """
        Returns whether or not virtual environment folder for this project exists or not
        :return: bool
        """

        venv_path = self._get_default_install_env_var()
        if not venv_path:
            return False

        return os.path.isdir(venv_path)

    def _download_deployment_requirements(self, dirname):
        """
        Internal function that downloads the current deployment requirements
        """

        self._set_splash_text('Downloading {} Deployment Information ...'.format(self._project_name))
        deployment_url = self._get_deploy_repository_url()
        if not deployment_url:
            LOGGER.error('Deployment URL not found!')
            return False

        response = requests.get(deployment_url, headers={'Connection': 'close'})
        if response.status_code != 200:
            LOGGER.error('Deployment URL is not valid: "{}"'.format(deployment_url))
            return False

        repo_name = urlparse(deployment_url).path.rsplit("/", 1)[-1]
        download_path = os.path.join(dirname, repo_name)

        valid_download = self._download_file(deployment_url, download_path)
        if not valid_download:
            LOGGER.error('Something went wrong during the download of: {}'.format(deployment_url))
            return False

        self._set_splash_text('Unzipping Deployment Data ...')
        valid_unzip = self._unzip_file(filename=download_path, destination=dirname, remove_sub_folders=[])
        if not valid_unzip:
            LOGGER.error('Something went wrong during the unzip of: {}'.format(download_path))
            return False

        self._set_splash_text('Searching Requirements File: {}'.format(self._requirements_file_name))
        requirement_path = None
        for root, dirs, files in os.walk(dirname):
            for name in files:
                if name == self._requirements_file_name:
                    requirement_path = os.path.join(root, name)
                    break
        if not requirement_path:
            LOGGER.error('No file named: {} found in deployment repository!'.format(self._requirements_file_name))
            return False
        LOGGER.debug('Requirements File for Deployment "{}" found: "{}"'.format(deployment_url, requirement_path))
        self._requirements_path = requirement_path

        return True

    def _install_deployment_requirements(self):
        if not self._venv_info:
            LOGGER.error('Impossible to install Deployment Requirements because Virtual Environment is not configured!')
            return False

        if not self._requirements_path or not os.path.isfile(self._requirements_path):
            LOGGER.error(
                'Impossible to install Deployment Requirements because file does not exists: "{}"'.format(
                    self._requirements_path)
            )
            return False

        pip_exe = self._venv_info.get('pip_exe', None)
        if not pip_exe or not os.path.isfile(pip_exe):
            LOGGER.error(
                'Impossible to install Deployment Requirements because pip not found installed in '
                'Virtual Environment: "{}"'.format(pip_exe)
            )
            return False

        self._set_splash_text('Installing Deployment Requirements ...')
        LOGGER.info('Installing Deployment Requirements with PIP: {}'.format(pip_exe))

        pip_cmd = '"{}" install --upgrade -r "{}"'.format(pip_exe, self._requirements_path)
        LOGGER.info('Launching pip command: {}'.format(pip_cmd))

        try:
            process = subprocess.Popen(pip_cmd)
            process.wait()
        except Exception as exc:
            LOGGER.error('Error while installing requirements from: {} | {} | {}'.format(
                self._requirements_path, exc, traceback.format_exc()))
            return False

        return True

    def _setup_deployment(self):
        if not self._venv_info:
            return False

        with tempfile.TemporaryDirectory() as temp_dirname:
            valid_download = self._download_deployment_requirements(temp_dirname)
            if not valid_download or not self._requirements_path or not os.path.isfile(self._requirements_path):
                return False
            valid_install = self._install_deployment_requirements()
            if not valid_install:
                return False

        return True

    def _download_file(self, filename, destination):
        """
        Downloads given file into given target path
        :param filename: str
        :param destination: str
        :param console: ArtellaConsole
        :param updater: ArtellaUpdater
        :return: bool
        """

        def _chunk_report(bytes_so_far, total_size):
            """
            Function that updates progress bar with current chunk
            :param bytes_so_far: int
            :param total_size: int
            :param console: ArtellaConsole
            :param updater: ArtellaUpdater
            :return:
            """

            percent = float(bytes_so_far) / total_size
            percent = round(percent * 100, 2)
            msg = "Downloaded %d of %d bytes (%0.2f%%)" % (bytes_so_far, total_size, percent)
            self._set_splash_text(msg)
            LOGGER.info(msg)

        def _chunk_read(response, destination, chunk_size=8192, report_hook=None):
            """
            Function that reads a chunk of a dowlnoad operation
            :param response: str
            :param destination: str
            :param console: ArtellaLauncher
            :param chunk_size: int
            :param report_hook: fn
            :param updater: ArtellaUpdater
            :return: int
            """

            with open(destination, 'ab') as dst_file:
                rsp = response.info().getheader('Content-Length')
                if not rsp:
                    return
                total_size = rsp.strip()
                total_size = int(total_size)
                bytes_so_far = 0
                while 1:
                    chunk = response.read(chunk_size)
                    dst_file.write(chunk)
                    bytes_so_far += len(chunk)
                    if not chunk:
                        break
                    if report_hook:
                        report_hook(bytes_so_far=bytes_so_far, total_size=total_size)
            dst_file.close()
            return bytes_so_far

        LOGGER.info('Downloading file {} to temporary folder -> {}'.format(os.path.basename(filename), destination))
        try:
            dst_folder = os.path.dirname(destination)
            if not os.path.exists(dst_folder):
                LOGGER.info('Creating Download Folder: "{}"'.format(dst_folder))
                os.makedirs(dst_folder)

            hdr = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) '
                              'Chrome/23.0.1271.64 Safari/537.11',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                'Accept-Encoding': 'none',
                'Accept-Language': 'en-US,en;q=0.8',
                'Connection': 'keep-alive'}
            req = Request(filename, headers=hdr)
            data = urlopen(req)
            _chunk_read(response=data, destination=destination, report_hook=_chunk_report)
        except Exception as e:
            raise RuntimeError('{} | {}'.format(e, traceback.format_exc()))

        if os.path.exists(destination):
            LOGGER.info('Files downloaded succesfully!')
            return True
        else:
            LOGGER.error('Error when downloading files. Maybe server is down! Try it later')
            return False

    def _unzip_file(self, filename, destination, remove_first=True, remove_sub_folders=None):
        """
        Unzips given file in given folder
        :param filename: str
        :param destination: str
        :param console: ArtellaConsole
        :param remove_first: bool
        :param remove_sub_folders: bool
        """

        LOGGER.info('Unzipping file {} to --> {}'.format(filename, destination))
        try:
            if remove_first and remove_sub_folders:
                LOGGER.info('Removing old installation ...')
                for sub_folder in remove_sub_folders:
                    p = os.path.join(destination, sub_folder)
                    LOGGER.info('\t{}'.format(p))
                    if os.path.exists(p):
                        shutil.rmtree(p)
            if not os.path.exists(destination):
                LOGGER.info('Creating destination folders ...')
                QApplication.instance().processEvents()
                os.makedirs(destination)

            if filename.endswith('.tar.gz'):
                zip_ref = tarfile.open(filename, 'r:gz')
            elif filename.endswith('.tar'):
                zip_ref = tarfile.open(filename, 'r:')
            else:
                zip_ref = zipfile.ZipFile(filename, 'r')
            zip_ref.extractall(destination)
            zip_ref.close()
            return True
        except Exception as e:
            LOGGER.error('{} | {}'.format(e, traceback.format_exc()))
            return False


if __name__ == '__main__':

    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser()
    parser.add_argument('--project-name', required=False)
    parser.add_argument('--repository', required=False)
    parser.add_argument('--environment', default='production')
    parser.add_argument('--splash-path', required=False, default=None)
    args = parser.parse_args()

    try:
        new_app = ArtellaUpdater(
            project_name=args.project_name,
            deployment_repository=args.repository,
            environment=args.environment,
            splash_path=args.splash_path
        )
    except Exception as exc:
        msg = '{} | {}'.format(exc, traceback.format_exc())
        LOGGER.exception(msg)
        traceback.print_exc()
        QMessageBox.critical(None, 'Error', msg)
    finally:
        app.quit()
