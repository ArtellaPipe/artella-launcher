#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation to create Artella launchers
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import re
import json
import shutil
import logging
import tempfile
import traceback
import requests
from bs4 import BeautifulSoup
from packaging.version import Version, InvalidVersion
try:
    from urlparse import urlparse
except Exception:
    from urllib.parse import urlparse

from Qt.QtCore import *
from Qt.QtWidgets import *

from tpQtLib.core import base
from tpQtLib.core import qtutils

from artellapipe import launcher
from artellapipe.launcher.core import defines, config
from artellapipe.launcher.widgets import console
from artellapipe.launcher.utils import download

LOGGER = logging.getLogger()


class ArtellaUpdater(base.BaseWidget, object):

    UPDATER_CONFIG_PATH = launcher.get_updater_config_path()

    def __init__(self, project, dccselector, parent=None):

        self._dccselector = dccselector
        self._project = project
        self._version = None
        self._console = None
        self._tools_env_var = None
        self._release_extension = None
        self._repository_url = None
        self._repository_folder = None
        self._last_version_file_name = None
        self._version_file_name = None
        self._progress_colors = list()

        self.init_config()

        super(ArtellaUpdater, self).__init__(parent=parent)

        self._console = console.ArtellaLauncherConsole(logger=self._project.logger)
        self._console.setWindowFlags(Qt.FramelessWindowHint)
        self._config = config.create_config(
            launcher_name=self._project.get_clean_name(), console=None, window=self, dcc_install_path=None)

    def closeEvent(self, event):
        self._console.close()
        super(ArtellaUpdater, self).closeEvent(event)

    def get_main_layout(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 2, 5, 2)
        main_layout.setSpacing(2)
        return main_layout

    def ui(self):
        super(ArtellaUpdater, self).ui()

        self.setWindowFlags(Qt.FramelessWindowHint)

        self._progress_bar = QProgressBar()
        self.main_layout.addWidget(self._progress_bar)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setTextVisible(False)
        if self.progress_colors:
            self._progress_bar.setStyleSheet(
                "QProgressBar {border: 0px solid grey; border-radius:4px; padding:0px} "
                "QProgressBar::chunk {background: qlineargradient(x1: 0, y1: 1, x2: 1, y2: 1, stop: 0 rgb(" + str(
                    self.progress_colors[0]) + "), stop: 1 rgb(" + str(self.progress_colors[1]) + ")); }")

        self._progress_text = QLabel('Downloading {} Tools ...'.format(self._project.name.title()))
        self._progress_text.setAlignment(Qt.AlignCenter)
        self._progress_text.setStyleSheet("QLabel { background-color : rgba(0, 0, 0, 180); color : white; }")
        font = self._progress_text.font()
        font.setPointSize(10)
        self._progress_text.setFont(font)
        self.main_layout.addWidget(self._progress_text)

    @property
    def project(self):
        """
        Returns project linked to this updater
        :return: ArtellaProject
        """

        return self._project

    @property
    def progress_bar(self):
        """
        Returns updater progress bar
        :return: QProgressBar
        """

        return self._progress_bar

    @property
    def version(self):
        """
        Returns Artella launcher version
        :return: str
        """

        return self._version

    @property
    def envvar_name(self):
        """
        Returns the environment variable named used by updater to store installation path
        :return: str
        """

        return self._tools_env_var

    @property
    def progress_colors(self):
        """
        Returns progress colors
        :return: list(str)
        """

        return self._progress_colors

    @property
    def console(self):
        """
        Returns the console used by Artella launcher
        """

        return self._console

    def init_config(self):
        """
        Function that reads updater configuration and initializes launcher variables properly
        This function can be extended in new updaters
        """

        if not self.UPDATER_CONFIG_PATH or not os.path.isfile(self.UPDATER_CONFIG_PATH):
            LOGGER.error(
                'Updater Configuration File for Artella Launcher not found! {}'.format(self.UPDATER_CONFIG_PATH))
            return

        with open(self.UPDATER_CONFIG_PATH, 'r') as f:
            updater_config_data = json.load(f)
        if not updater_config_data:
            LOGGER.error(
                'Updater Configuration File for Artella Project is empty! {}'.format(self.LAUNCHER_CONFIG_PATH))
            return

        self._version = updater_config_data.get(defines.ARTELLA_CONFIG_UPDATER_VERSION, defines.DEFAULT_VERSION)
        self._tools_env_var = updater_config_data.get(defines.UPDATER_TOOLS_ENVIRONMENT_VARIABLE_ATTRIBUTE_NAME, '')
        self._release_extension = updater_config_data.get(defines.UPDATER_RELEASE_EXTENSION, 'tar.gz')
        self._repository_url = updater_config_data.get(defines.UPDATER_REPOSITORY_URL_ATTRIBUTE_NAME, '')
        self._repository_folder = updater_config_data.get(defines.UPDATER_REPOSITORY_FOLDER_ATTRIBUTE_NAME, '')
        self._last_version_file_name = updater_config_data.get(defines.UPDATER_LAST_VERSION_FILE_NAME, '')
        self._version_file_name = updater_config_data.get(defines.UPDATER_VERSION_FILE_NAME, '')
        self._progress_colors.append(updater_config_data.get(defines.UPDATER_PROGRESS_BAR_COLOR_0_ATTRIBUTE_NAME,
                                                             defines.DEFAULT_PROGRESS_BAR_COLOR_0))
        self._progress_colors.append(updater_config_data.get(defines.UPDATER_PROGRESS_BAR_COLOR_1_ATTRIBUTE_NAME,
                                                             defines.DEFAULT_PROGRESS_BAR_COLOR_1))

        if not self._tools_env_var:
            self._tools_env_var = '{}_install'.format(self._project.get_clean_name())

    def get_default_installation_path(self, full_path=False):
        """
        Returns default installation path for tools
        :param full_path: bool
        :return: str
        """

        return ""

    def get_installation_path(self):
        """
        Returns tools installation path
        :return: str
        """

        try:
            if self._dccselector.config:
                install_path = self._dccselector.config.value(self.envvar_name)
            else:
                install_path = self.get_default_installation_path()
                self._dccselector.config.setValue(self.envvar_name, install_path)
        except Exception:
            install_path = self.get_default_installation_path()
            if self._dccselector.config:
                self._dccselector.config.setValue(self.envvar_name, install_path)

        return install_path

    def set_installation_path(self):
        """
        Sets tools installation path
        """

        selected_dir = qtutils.get_folder(
            title='Select folder where you want to install {} tools'.format(self._project.name.title()))
        if not selected_dir or not os.path.exists(selected_dir):
            qtutils.show_warning(
                None, 'Installation cancelled', '{} tools intallation cancelled!'.format(self._project.name.title()))
            return

        return os.path.abspath(selected_dir)

    def _get_latest_github_released_version(self, sniff=True, validate=True, format='version', pre=False):
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

        repository = self._repository_url
        if not repository:
            self._console.write_error(
                '> Project {} GitHub repository is not valid! {}'.format(self._project.name.title(), repository))
            QApplication.instance().processEvents()
            return None

        if repository.startswith('https://github.com/'):
            repository = "/".join(repository.split('/')[3:5])

        if sniff:
            release_url = "https://github.com/{}/releases".format(repository)
            response = requests.get(release_url, headers={'Connection': 'close'})
            html = response.text
            LOGGER.debug('Parsing HTML of {} GitHub release page ...'.format(self._project.name.title()))

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
                                QApplication.instance().processEvents()
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
            self._console.write_error(
                'Impossible to retrieve {} lastest release version from GitHub!'.format(self._project.name.title()))
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

    def check_tools_version(self):
        """
        Checks the current installed version, returns True if the user don't have the last
        tools installed version or False otherwise.
        This function can be override in child updaters to implement specific functionality
        :return: bool, True if tools need to be updated or False otherwise
        """

        install_path = self.get_installation_path()
        if install_path is None or not os.path.exists(install_path):
            self._console.write_error(
                '> Installation path {} does not exists! '
                'Check that tools are installed in your system!\n'.format(install_path))
            return
        else:
            self._console.write('> Installation Path detected: {}\n'.format(install_path))
        QApplication.instance().processEvents()

        last_version = str(self.get_latest_github_released_version())
        if not last_version:
            self._console.write('Impossible to retrieve latest {} version!'.format(self.project.name.title()))
            QApplication.instance().processEvents()
            return

        self._console.write_ok(
            'Latest {} Tools deployed version found: {}'.format(self.project.name.title(), last_version))
        self._console.write(
            'Checking current {} Tools installed version on {}'.format(self._project.name.title(), install_path))
        QApplication.instance().processEvents()

        last_version_file = None
        if os.listdir(install_path):
            if self._version_file_name:
                for d, _, files in os.walk(install_path):
                    if last_version_file:
                        break
                    for f in files:
                        if f == self._version_file_name:
                            last_version_file = os.path.join(d, f)
                            break
        else:
            return True

        if not last_version_file:
            return True

        self._console.write(
            '{} Tools Last Version File found: {}'.format(self.project.name.title(), last_version_file))
        QApplication.instance().processEvents()

        try:
            ext = os.path.splitext(last_version_file)[1]
            if ext == '.json':
                with open(last_version_file, 'r') as f:
                    install_info = json.loads(f.read())
                    installed_version = install_info.get('version', None)
            elif ext == '.py':
                with open(last_version_file, 'r') as f:
                    version_info = f.readline()
                    if not version_info.startswith('__version__'):
                        installed_version = None
                    else:
                        exec(version_info)
                        installed_version = __version__

            if not installed_version:
                self._console.write_error(
                    'Impossible to get {} Tools installed version ...'.format(self.project.name.title()))
                QApplication.instance().processEvents()
                return

            self._console.write_ok('\n\nCurrent installed version: {}\n'.format(installed_version))
            QApplication.instance().processEvents()

            if installed_version == last_version:
                self._console.write(
                    '\nCurrent installed {} Tools: {} are up-to-date (last deployed version {})!'.format(
                        self.project.name.title(), installed_version, last_version))
                QApplication.instance().processEvents()
                return False

            return True
        except Exception as e:
            self._console.write_error('Error while retrieving {} Tools version!'.format(self.project.name.title()))
            self._console.write_error('{} | {}'.format(e, traceback.format_exc()))
            QApplication.instance().processEvents()
            return False

    def get_tools_version_status(self):
        """
        Returns information of the current version status
        :return: list(int, int, bool)
        """

        install_path = self.get_installation_path()
        if install_path is None or not os.path.exists(install_path):
            return None, None, True

        last_version = self.get_latest_github_released_version()
        if not last_version:
            self._console.write('Impossible to retrieve latest {} version!'.format(self.project.name.title()))
            QApplication.instance().processEvents()
            return None, None, True

        self._console.write_ok(
            'Latest {} Tools deployed version found: {}'.format(self.project.name.title(), last_version))
        self._console.write(
            'Checking current {} Tools installed version on {}'.format(self._project.name.title(), install_path))
        QApplication.instance().processEvents()

        installed_version = None
        last_version_file = None
        if os.listdir(install_path):
            for d, _, files in os.walk(install_path):
                if last_version_file:
                    break
                for f in files:
                    if f == self._version_file_name:
                        last_version_file = os.path.join(d, f)
                        break
        else:
            return last_version, installed_version, True

        if not last_version_file:
            return last_version, installed_version, True

        try:
            ext = os.path.splitext(last_version_file)[1]
            if ext == '.json':
                with open(last_version_file, 'r') as f:
                    install_info = json.loads(f.read())
                    installed_version = install_info.get('version', None)
            elif ext == '.py':
                with open(last_version_file, 'r') as f:
                    version_info = f.readline()
                    if not version_info.startswith('__version__'):
                        installed_version = None
                    else:
                        exec version_info
                        installed_version = __version__

            if not installed_version:
                return last_version, installed_version, True

            if installed_version == last_version:
                return last_version, installed_version, False
            else:
                return last_version, installed_version, True
        except Exception:
            return last_version, installed_version, True

    def update_tools(self):
        """
        Updates tools to the last available version
        """

        try:
            temp_path = tempfile.mkdtemp()
            last_version, installed_version, need_to_update = self.get_tools_version_status()
            if not last_version:
                return

            if need_to_update:
                install_path = self.get_installation_path()
                if install_path is None or not os.path.exists(install_path):
                    self._console.write_error('Install Path {} does not exists!'.format(install_path))
                    return
                else:
                    self._console.write('Install Path detected: {}'.format(install_path))
                QCoreApplication.instance().processEvents()

                self._console.write('=' * 15)
                self._console.write_ok(
                    'Current installed {} Tools are outdated {}!'.format(self._project.name.title(), installed_version))
                self._console.write_ok('Installing new tools ... {}!!'.format(last_version))
                self._console.write('=' * 15)
                QCoreApplication.instance().processEvents()

                repository = self._repository_url
                repository = repository[:-1]
                repository_name = urlparse(repository).path.rsplit("/", 1)[-1]
                tools_file = '{}-{}'.format(repository_name, last_version)
                tools_zip = '{}.{}'.format(tools_file, self._release_extension)
                tools_url = '{}/releases/download/{}/{}.{}'.format(
                    repository, last_version, tools_file, self._release_extension)
                tools_install_path = os.path.join(temp_path, last_version, tools_zip)
                self._console.write('{} Tools File: {}'.format(self._project.name.title(), tools_zip))
                self._console.write('{} Tools URL: {}'.format(self._project.name.title(), tools_url))
                self._console.write('{} Tools Install Path: {}'.format(self._project.name.title(), tools_install_path))
                QApplication.instance().processEvents()

                if not download.download_file(
                        filename=tools_url, destination=tools_install_path, console=self._console, updater=self):
                    self._console.write_error(
                        '{} is not accessible! Maybe GitHub is down or your internet connection is down!'.format(
                            tools_url))
                    return

                self._console.write_ok(
                    'Installing {} Tools on: {}'.format(self._project.name.title(), tools_install_path))
                QApplication.instance().processEvents()

                self._progress_text.setText('Installing {} Tools ...'.format(self._project.name.title()))
                QApplication.instance().processEvents()

                download.unzip_file(
                    filename=tools_install_path, destination=temp_path, console=self._console, remove_sub_folders=[])

                repo_folder = os.path.join(temp_path, self._repository_folder)
                extracted_files = os.listdir(repo_folder)

                for f in os.listdir(install_path):
                    if f in extracted_files:
                        fld = os.path.join(install_path, f)
                        shutil.rmtree(fld)

                if os.path.isdir(repo_folder):
                    for f in os.listdir(repo_folder):
                        fld = os.path.join(repo_folder, f)
                        if not os.path.isdir(fld):
                            continue
                        shutil.move(fld, install_path)

                self._console.write('=' * 15)
                self._console.write_ok(
                    '{} Tools {} installed successfully!'.format(self._project.name.title(), last_version))
                self._console.write('=' * 15)
                QCoreApplication.processEvents()

                return True
        except Exception as e:
            self._console.write_error('Error while updating {} Tools version!')
            self._console.write_error('{} | {}'.format(e, traceback.format_exc()))
            QApplication.instance().processEvents()
            return False
        finally:
            try:
                shutil.rmtree(temp_path)
            except Exception:
                pass
