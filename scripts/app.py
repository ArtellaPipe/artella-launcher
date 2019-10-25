import os
import re
import sys
import time
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
import contextlib
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

ARTELLA_APP_NAME = 'lifecycler'
ARTELLA_NEXT_VERSION_FILE_NAME = 'version_to_run_next'


class ArtellaUpdaterException(Exception, object):
    def __init__(self, exc):
        if type(exc) in [str, unicode]:
            exc = Exception(exc)
        msg = '{} | {}'.format(exc, traceback.format_exc())
        LOGGER.exception(msg)
        traceback.print_exc()
        QMessageBox.critical(None, 'Error', msg)


class ArtellaUpdater(QWidget, object):
    def __init__(
            self, project_name, app_version, deployment_repository, documentation_url=None,
            deploy_tag=None, install_env_var=None, requirements_file_name=None,
            force_venv=False, splash_path=None, script_path=None, dev=False,
            parent=None):
        super(ArtellaUpdater, self).__init__(parent=parent)

        self._config_data = self._read_config()

        self._dev = dev
        self._project_name = project_name if project_name else self._get_app_config('name')
        self._app_version = app_version if app_version else '0.0.0'
        self._repository = deployment_repository if deployment_repository else self._get_app_config('repository')
        self._splash_path = splash_path if splash_path and os.path.isfile(splash_path) else \
            self._get_app_config('splash')
        self._force_venv = force_venv
        self._venv_info = dict()

        self._setup_logger()
        self._setup_config()

        self._setup_ui()
        QApplication.instance().processEvents()

        self._install_path = None
        self._selected_tag_index = None
        self._requirements_path = None
        self._documentation_url = documentation_url if documentation_url else self._get_default_documentation_url()
        self._install_env_var = install_env_var if install_env_var else self._get_default_install_env_var()
        self._requirements_file_name = requirements_file_name if requirements_file_name else 'requirements.txt'
        self._all_tags = list()
        self._deploy_tag = deploy_tag if deploy_tag else self._get_deploy_tag()
        self._script_path = script_path if script_path and os.path.isfile(script_path) else self._get_script_path()

        valid_load = self._load()
        if not valid_load:
            sys.exit()

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

        process = subprocess.Popen(['python', '-c', 'quit()'])
        process.wait()

        return True if process.returncode == 0 else False

    def is_pip_installed(self):
        """
        Returns whether pip is installed or not
        :return: bool
        """

        process = subprocess.Popen(['pip', '-V'])
        process.wait()

        return True if process.returncode == 0 else False

    def is_virtualenv_installed(self):
        """
        Returns whether virtualenv is intsalled or not
        :return: bool
        """

        process = subprocess.Popen(['virtualenv', '--version'])
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
        except RuntimeError as exc:
            raise Exception(exc)

        return data

    def _get_app_config(self, config_name):
        """
        Returns configuration parameter stored in configuration, if exists
        :param config_name: str
        :return: str
        """

        if not self._config_data:
            return None

        return self._config_data.get(config_name, None)

    def _get_script_path(self):
        script_path = None
        config_file_name = 'launcher.py'
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), config_file_name)
        if not os.path.isfile(script_path):
            script_path = os.path.join(os.path.dirname(sys.executable), 'resources', config_file_name)
            if not os.path.isfile(script_path):
                if hasattr(sys, '_MEIPASS'):
                    script_path = os.path.join(sys._MEIPASS, 'resources', config_file_name)

        LOGGER.info('Launcher Script: "{}"'.format(script_path))

        return script_path

    def _get_resource(self, resource_name):
        resource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', resource_name)
        if not os.path.isfile(resource_path):
            resource_path = os.path.join(os.path.dirname(sys.executable), 'resources', resource_name)
            if not os.path.isfile(resource_path):
                if hasattr(sys, '_MEIPASS'):
                    resource_path = os.path.join(sys._MEIPASS, 'resources', resource_name)

        return resource_path

    def _set_splash_text(self, new_text):
        self._progress_text.setText(new_text)
        QApplication.instance().processEvents()

    def _setup_ui(self):
        splash_pixmap = QPixmap(self._splash_path)
        self._splash = QSplashScreen(splash_pixmap)
        self._splash.mousePressEvent = self._splash_mouse_event_override
        self._splash.setWindowFlags(Qt.FramelessWindowHint)
        splash_layout = QVBoxLayout()
        splash_layout.setContentsMargins(5, 2, 5, 2)
        splash_layout.setSpacing(2)
        splash_layout.setAlignment(Qt.AlignBottom)
        self._splash.setLayout(splash_layout)

        label_style = """
        QLabel
        {
            background-color: rgba(100, 100, 100, 100);
            color: white;
            border-radius: 5px;
        }
        """

        self._version_lbl = QLabel('v0.0.0')
        self._version_lbl.setStyleSheet(label_style)
        version_font = self._version_lbl.font()
        version_font.setPointSize(10)
        self._version_lbl.setFont(version_font)

        self._artella_status_icon = QLabel()
        self._artella_status_icon.setPixmap(QPixmap(self._get_resource('artella_off.png')).scaled(QSize(30, 30)))

        install_path_icon = QLabel()
        install_path_icon.setPixmap(QPixmap(self._get_resource('disk.png')).scaled(QSize(25, 25)))
        self._install_path_lbl = QLabel('Install Path: ...')
        self._install_path_lbl.setStyleSheet(label_style)
        install_path_font = self._install_path_lbl.font()
        install_path_font.setPointSize(8)
        self._install_path_lbl.setFont(install_path_font)
        deploy_tag_icon = QLabel()
        deploy_tag_icon.setPixmap(QPixmap(self._get_resource('tag.png')).scaled(QSize(25, 25)))
        self._deploy_tag_combo = QComboBox()
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(10)

        buttons_style = """
        QPushButton:!hover
        {
            background-color: rgba(100, 100, 100, 100);
            color: white;
            border-radius: 5px;
        }
        QPushButton:hover
        {
            background-color: rgba(50, 50, 50, 100);
            color: white;
            border-radius: 5px;
        }
        QPushButton:pressed
        {
            background-color: rgba(15, 15, 15, 100);
            color: white;
            border-radius: 5px;
        }
        """

        self._launch_btn = QPushButton('Launch')
        self._launch_btn.setStyleSheet(buttons_style)
        self._launch_btn.setFixedWidth(150)
        self._launch_btn.setFixedHeight(30)
        self._launch_btn.setIconSize(QSize(40, 40))
        self._launch_btn.setIcon(QPixmap(self._get_resource('play.png')))
        self._close_btn = QPushButton('')
        self._close_btn.setFlat(True)
        self._close_btn.setFixedSize(QSize(30, 30))
        self._close_btn.setIconSize(QSize(25, 25))
        self._close_btn.setIcon(QPixmap(self._get_resource('close.png')))
        self._open_install_folder_btn = QPushButton('Open Install Folder')
        self._open_install_folder_btn.setStyleSheet(buttons_style)
        self._open_install_folder_btn.setFixedWidth(150)
        self._open_install_folder_btn.setFixedHeight(30)
        self._open_install_folder_btn.setIconSize(QSize(25, 25))
        self._open_install_folder_btn.setIcon(QPixmap(self._get_resource('search_folder.png')))
        self._uninstall_btn = QPushButton('Uninstall')
        self._uninstall_btn.setStyleSheet(buttons_style)
        self._uninstall_btn.setFixedWidth(150)
        self._uninstall_btn.setFixedHeight(30)
        self._uninstall_btn.setIconSize(QSize(30, 30))
        self._uninstall_btn.setIcon(QPixmap(self._get_resource('uninstall.png')))
        self._buttons_layout = QVBoxLayout()
        self._buttons_layout.setContentsMargins(5, 5, 5, 5)
        self._buttons_layout.setSpacing(2)
        self._buttons_layout.addWidget(self._launch_btn)
        self._buttons_layout.addWidget(self._open_install_folder_btn)
        self._buttons_layout.addWidget(self._uninstall_btn)

        self._progress_text = QLabel('Setting {} ...'.format(self._project_name.title()))
        self._progress_text.setAlignment(Qt.AlignCenter)
        self._progress_text.setStyleSheet("QLabel { background-color : rgba(0, 0, 0, 180); color : white; }")
        font = self._progress_text.font()
        font.setPointSize(10)
        self._progress_text.setFont(font)

        second_layout = QHBoxLayout()
        second_layout.setContentsMargins(5, 5, 5, 5)
        second_layout.setSpacing(5)
        second_layout.addItem(QSpacerItem(10, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        second_layout.addLayout(self._buttons_layout)
        second_layout.addItem(QSpacerItem(10, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))

        splash_layout.addLayout(second_layout)
        splash_layout.addWidget(self._progress_text)

        self._artella_status_icon.setParent(self._splash)
        self._version_lbl.setParent(self._splash)
        self._close_btn.setParent(self._splash)
        install_path_icon.setParent(self._splash)
        self._install_path_lbl.setParent(self._splash)
        deploy_tag_icon.setParent(self._splash)
        self._deploy_tag_combo.setParent(self._splash)

        self._artella_status_icon.setFixedSize(QSize(45, 45))
        self._version_lbl.setFixedSize(50, 20)
        install_path_icon.setFixedSize(QSize(35, 35))
        self._install_path_lbl.setFixedSize(QSize(200, 20))
        deploy_tag_icon.setFixedSize(QSize(35, 35))
        self._deploy_tag_combo.setFixedSize(QSize(150, 20))

        height = 5
        self._version_lbl.move(10, self._splash.height() - 48)
        # height += self._version_lbl.height()
        self._artella_status_icon.move(5, height)
        height += self._artella_status_icon.height() - 5
        install_path_icon.move(5, height)
        self._install_path_lbl.move(install_path_icon.width(), height + self._install_path_lbl.height() / 2 - 5)
        height += install_path_icon.height() - 5
        deploy_tag_icon.move(5, height)
        height = height + self._deploy_tag_combo.height() / 2 - 5
        self._deploy_tag_combo.move(deploy_tag_icon.width(), height)
        self._close_btn.move(self._splash.width() - self._close_btn.width() - 5, 0)

        self._deploy_tag_combo.setFocusPolicy(Qt.NoFocus)

        combo_width = 5
        if self._dev:
            self._deploy_tag_combo.setEnabled(False)
            # self._deploy_tag_combo.setFixedSize(QSize(30, 20))
            combo_width = 0

        self._deploy_tag_combo.setStyleSheet("""
        QComboBox:!editable
        {
            background-color: rgba(100, 100, 100, 100);
            color: white;
            border-radius: 5px;
            padding: 1px 0px 1px 3px;
        }
        QComboBox::drop-down:!editable
        {
            background: rgba(50, 50, 50, 100);
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
            image: none;
            width: %dpx;
        }
        """ % combo_width)

        self._close_btn.setVisible(False)
        self._launch_btn.setVisible(False)
        self._open_install_folder_btn.setVisible(False)
        self._uninstall_btn.setVisible(False)

        self._deploy_tag_combo.currentIndexChanged.connect(self._on_selected_tag)
        self._close_btn.clicked.connect(QApplication.instance().quit)
        self._open_install_folder_btn.clicked.connect(self._on_open_installation_folder)
        self._launch_btn.clicked.connect(self.launch)
        self._uninstall_btn.clicked.connect(self._on_uninstall)

        self._splash.show()
        self._splash.raise_()

    def _on_selected_tag(self, new_index):
        new_tag = self._deploy_tag_combo.itemText(new_index)
        if not new_tag:
            LOGGER.error('New Tag "{}" is not valid!'.format(new_tag))
            return

        res = QMessageBox.question(
            self._splash, 'Installing tag version: "{}"'.format(new_tag),
            'Are you sure you want to install this version: "{}"?'.format(new_tag),
            QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
        if res == QMessageBox.Yes:
            LOGGER.info("Installing tag version: {}".format(new_tag))
            self._deploy_tag = new_tag
            self._selected_tag_index = new_index
            self._set_config('tag', new_tag)
            self._load()
        else:
            try:
                self._deploy_tag_combo.blockSignals(True)
                self._deploy_tag_combo.setCurrentIndex(self._selected_tag_index)
            finally:
                self._deploy_tag_combo.blockSignals(False)

    def _on_open_installation_folder(self):
        """
        Internal callback function that is called when the user press Open Installation Folder button
        """

        install_path = self._get_installation_path()
        if install_path and os.path.isdir(install_path) and len(os.listdir(install_path)) != 0:
            self._open_folder(install_path)
        else:
            LOGGER.warning('{} environment not installed!'.format(self._project_name))

    def _open_folder(self, path=None):
        """
        Opens a folder in the explorer in a independent platform way
        If not path is passed the current directory will be opened
        :param path: str, folder path to open
        """

        if path is None:
            path = os.path.curdir
        if sys.platform == 'darwin':
            subprocess.check_call(['open', '--', path])
        elif sys.platform == 'linux2':
            subprocess.Popen(['xdg-open', path])
        elif sys.platform is 'windows' or 'win32' or 'win64':
            new_path = path.replace('/', '\\')
            try:
                subprocess.check_call(['explorer', new_path], shell=False)
            except Exception:
                pass

    def _on_uninstall(self):
        """
        Internal callback function that is called when the user press Uninstall button
        Removes environment variable and Tools folder
        :return:
        """

        question_flags = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

        install_path = self._get_installation_path()
        if install_path and os.path.isdir(install_path):
            dirs_to_remove = [os.path.join(install_path, self.get_clean_name())]
            res = QMessageBox.question(
                self._splash, 'Uninstalling {} Tools'.format(self._project_name),
                'Are you sure you want to uninstall {} Tools?\n\nFolder/s that will be removed \n\t{}'.format(
                    self._project_name, '\n\t'.join(dirs_to_remove)), question_flags)
            if res == QMessageBox.Yes:
                try:
                    for d in dirs_to_remove:
                        if os.path.isdir(d):
                            shutil.rmtree(d, ignore_errors=True)
                        elif os.path.isfile(d):
                            os.remove(d)
                    self._set_config(self._install_env_var, '')
                    QMessageBox.information(
                        self._splash, '{} Tools uninstalled'.format(self._project_name),
                        '{} Tools uninstalled successfully! App will be closed now!'.format(self._project_name))
                    QApplication.instance().quit()
                except Exception as e:
                    self._set_config(self._install_env_var, '')
                    QMessageBox.critical(
                        self._splash, 'Error during {} Tools uninstall process'.format(self._project_name),
                        'Error during {} Tools uninstall: {} | {}\n\n'
                        'You will need to remove following folders manually:\n\n{}'.format(
                            self._project_name, e, traceback.format_exc(), '\n\t'.join(dirs_to_remove)))
        else:
            LOGGER.warning('{} tools are not installed! Launch any DCC first!'.format(self._project_name))

    def _setup_environment(self):

        if not self._install_path:
            LOGGER.error('Impossible to setup virtual environment because install path is not defined!')
            return False

        if not hasattr(sys, 'real_prefix'):
            LOGGER.error('Current Python"{}" is not installed in a virtual environment!'.format(
                os.path.dirname(sys.executable)))

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
            process = subprocess.Popen(['pip', 'install', 'virtualenv'])
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

    def _init_tags_combo(self):
        all_releases = self._get_all_releases()
        try:
            self._deploy_tag_combo.blockSignals(True)
            for release in all_releases:
                self._deploy_tag_combo.addItem(release)
        finally:
            if self._deploy_tag:
                deploy_tag_index = [i for i in range(self._deploy_tag_combo.count())
                                    if self._deploy_tag_combo.itemText(i) == self._deploy_tag]
                if deploy_tag_index:
                    self._selected_tag_index = deploy_tag_index[0]
                    self._deploy_tag_combo.setCurrentIndex(self._selected_tag_index)

            if not self._selected_tag_index:
                self._selected_tag_index = self._deploy_tag_combo.currentIndex()
            self._deploy_tag_combo.blockSignals(False)

    def _load(self):
        """
        Internal function that initializes Artella App
        """

        valid_check = self._check_setup()
        if not valid_check:
            return False

        install_path = self._set_installation_path()
        if not install_path:
            return False
        self._version_lbl.setText(str('v{}'.format(self._app_version)))
        self._install_path_lbl.setText(install_path)
        self._install_path_lbl.setToolTip(install_path)

        self._init_tags_combo()

        valid_venv = self._setup_environment()
        if not valid_venv:
            return False
        if not self._venv_info:
            LOGGER.warning('No Virtual Environment info retrieved ...')
            return False
        valid_install = self._setup_deployment()
        if not valid_install:
            return False
        valid_artella = self._setup_artella()
        if not valid_artella:
            self._artella_status_icon.setPixmap(QPixmap(self._get_resource('artella_error.png')).scaled(QSize(30, 30)))
            self._artella_status_icon.setToolTip('Error while connecting to Artella server!')
            return False
        else:
            self._artella_status_icon.setPixmap(QPixmap(self._get_resource('artella_ok.png')).scaled(QSize(30, 30)))
            self._artella_status_icon.setToolTip('Artella Connected!')

        self._set_splash_text('{} Launcher is ready to lunch!'.format(self._project_name))

        self._close_btn.setVisible(True)

        # We check that stored config path exits
        stored_path = self._get_app_config(self._install_env_var)
        if stored_path and not os.path.isdir(stored_path):
            self._set_config(self._install_env_var, '')

        path_install = self._get_installation_path()
        is_installed = path_install and os.path.isdir(path_install)
        if is_installed:
            self._launch_btn.setVisible(True)
            if not self._dev:
                self._open_install_folder_btn.setVisible(True)
                self._uninstall_btn.setVisible(True)
        else:
            QMessageBox.warning(
                self,
                'Was not possible to install {} environment.'.format(self._project_name),
                'Was not possible to install {} environment.\n\n'
                'Relaunch the app. If the problem persists, please contact your project TD'.format(
                    self._project_name))

        return True

    def launch(self):

        if not self._venv_info:
            LOGGER.warning(
                'Impossible to launch {} Launcher because Virtual Environment Setup is not valid!'.format(
                    self._project_name))
            return False

        py_exe = self._venv_info['venv_python']
        if not self._script_path or not os.path.isfile(self._script_path):
            raise Exception('Impossible to find launcher script!')

        LOGGER.info('Executing {} Launcher ...'.format(self._project_name))

        paths_to_register = self._get_paths_to_register()

        process_cmd = '"{}" "{}" --install-path "{}" --paths-to-register "{}"'.format(
            py_exe, self._script_path, self._install_path, '"{0}"'.format(' '.join(paths_to_register)))
        if self._dev:
            process_cmd += ' --dev'
        process = subprocess.Popen(process_cmd, close_fds=True)

        self._splash.close()

        if not self._dev:
            time.sleep(3)
            QApplication.instance().quit()

    def _check_installation_path(self, install_path):
        """
        Returns whether or not given path is valid
        :param install_path: str
        :return: bool
        """

        if not install_path or not os.path.isdir(install_path):
            return False

        return True

    def _splash_mouse_event_override(self, event):
        pass

    def _set_installation_path(self):
        """
        Returns installation path is if it already set by user; Otherwise a dialog to select it will appear
        :return: str
        """

        path_updated = False
        install_path = self._get_installation_path()

        # Remove older installations
        self._set_splash_text('Searching old installation ...')
        old_installation = False
        if os.path.isdir(install_path):
            for d in os.listdir(install_path):
                if d == self.get_clean_name():
                    old_dir = os.path.join(install_path, d)
                    content = os.listdir(old_dir)
                    if 'Include' not in content or 'Lib' not in content or 'Scripts' not in content:
                        old_installation = True
                        break
        if old_installation:
            LOGGER.info("Old installation found. Removing ...")
            self._set_splash_text('Removing old installation ...')
            shutil.rmtree(install_path)

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
            self._set_splash_text('Registering new install path ...')
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

        if self._dev:
            if hasattr(sys, 'real_prefix'):
                install_path = os.path.dirname(os.path.dirname(sys.executable))
            else:
                install_path = os.path.dirname(sys.executable)
        else:
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

    def _sanitize_github_version(self, version):
        """extract what appears to be the version information"""
        s = re.search(r'([0-9]+([.][0-9]+)+(rc[0-9]?)?)', version)
        if s:
            return s.group(1)
        else:
            return version.strip()

    def _get_all_releases(self):
        """
        Internal function that returns a list with all released versions of the deploy repository taking into account
        the project name
        :return: list(str)
        """

        if self._dev:
            return ['DEV']

        all_versions = list()

        repository = self._get_deploy_repository_url(release=True)
        if not repository:
            LOGGER.error(
                '> Project {} GitHub repository is not valid! {}'.format(self._project_name.title(), repository))
            return None

        if repository.startswith('https://github.com/'):
            repository = "/".join(repository.split('/')[3:5])

        release_url = "https://github.com/{}/releases".format(repository)
        response = requests.get(release_url, headers={'Connection': 'close'})
        html = response.text
        LOGGER.debug('Parsing HTML of {} GitHub release page ...'.format(self._project_name.title()))

        soup = BeautifulSoup(html, 'lxml')

        releases = soup.findAll(class_='release-entry')
        for release in releases:
            release_a = release.find("a")
            if not release_a:
                continue
            the_version = release_a.text
            if 'Latest' in the_version:
                label_latest = release.find(class_='label-latest', recursive=False)
                if label_latest:
                    the_version = release.find(class_='css-truncate-target').text
                    the_version = self._sanitize_github_version(the_version)
            else:
                the_version = self._sanitize_github_version(the_version)

            if the_version not in all_versions:
                all_versions.append(the_version)

        return all_versions

    def _get_deploy_tag(self):
        """
        Internal function that returns the current tag that should be used for deployment
        :return: str
        """

        if self._dev:
            return 'DEV'

        config_data = self.get_config_data()
        deploy_tag = config_data.get('tag', '')
        latest_deploy_tag = self._get_latest_deploy_tag()
        if not deploy_tag:
            deploy_tag = latest_deploy_tag
        else:
            deploy_tag_v = Version(deploy_tag)
            latest_tag_v = Version(latest_deploy_tag)
            if latest_tag_v > deploy_tag_v:
                res = QMessageBox.question(
                    self._splash, 'Newer version found: {}'.format(latest_deploy_tag),
                    'Current Version: {}\nNew Version: {}\n\nDo you want to install new version?'.format(
                        deploy_tag, latest_deploy_tag), QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
                if res == QMessageBox.Yes:
                    self._set_config('tag', latest_deploy_tag)
                    deploy_tag = latest_deploy_tag

        LOGGER.info("Deploy Tag to use: {}".format(deploy_tag))

        return deploy_tag

    def _get_latest_deploy_tag(self, sniff=True, validate=True, format='version', pre=False):
        """
        Returns last deployed version of the given repository in GitHub
        :return: str
        """

        if self._dev:
            return 'DEV'

        self._all_tags = list()

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
                        the_version = self._sanitize_github_version(the_version)
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
                        the_version = self._sanitize_github_version(the_version)
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
        process = subprocess.Popen(['virtualenv', venv_path])
        process.wait()

        return True if process.returncode == 0 else False

    def _get_venv_folder_path(self):
        """
        Returns path where virtual environment folder should be located
        :return: str
        """

        if not self._install_path:
            return

        if self._dev:
            return os.path.normpath(self._install_path)
        else:
            return os.path.normpath(os.path.join(self._install_path, self.get_clean_name()))

    def _get_paths_to_register(self):
        """
        Returns paths that will be registered in sys.path during DCC environment loading
        :return: list(str)
        """

        paths_to_register = [self._get_installation_path()]

        lib_site_folder = os.path.join(self._install_path, 'Lib', 'site-packages')
        if os.path.isdir(lib_site_folder):
            paths_to_register.append(lib_site_folder)

        return paths_to_register

    def _check_venv_folder_exists(self):
        """
        Returns whether or not virtual environment folder for this project exists or not
        :return: bool
        """

        venv_path = self._get_default_install_env_var()
        if not venv_path:
            return False

        return os.path.isdir(venv_path)

    def _try_download_unizip_deployment_requirements(self, deployment_url, download_path, dirname):
        valid_download = self._download_file(deployment_url, download_path)
        if not valid_download:
            return False

        try:
            valid_unzip = self._unzip_file(filename=download_path, destination=dirname, remove_sub_folders=[])
        except Exception:
            valid_unzip = False
        if not valid_unzip:
            return False

        return True

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

        valid_status = False
        total_tries = 0
        self._set_splash_text('Downloading and Unzipping Deployment Data ...')
        while not valid_status:
            if total_tries > 10:
                break
            valid_status = self._try_download_unizip_deployment_requirements(deployment_url, download_path, dirname)
            total_tries += 1
            if not valid_status:
                LOGGER.warning('Retrying downloading and unzip deployment data: {}'.format(total_tries))
        if not valid_status:
            LOGGER.error('Something went wrong during the download and unzipping of: {}'.format(deployment_url))
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

        self._set_splash_text('Installing {} Requirements ...'.format(self._project_name))
        LOGGER.info('Installing Deployment Requirements with PIP: {}'.format(pip_exe))

        pip_cmd = '"{}" install --upgrade -r "{}"'.format(pip_exe, self._requirements_path)
        LOGGER.info('Launching pip command: {}'.format(pip_cmd))

        try:
            process = subprocess.Popen(pip_cmd)
            process.wait()
        except Exception as exc:
            raise Exception(exc)

        return True

    def _setup_deployment(self):
        if not self._venv_info:
            return False

        if self._dev:
            return True

        with tempfile.TemporaryDirectory() as temp_dirname:
            valid_download = self._download_deployment_requirements(temp_dirname)
            if not valid_download or not self._requirements_path or not os.path.isfile(self._requirements_path):
                return False
            valid_install = self._install_deployment_requirements()
            if not valid_install:
                return False

        return True

    def _setup_artella(self):
        self._set_splash_text('Updating Artella Paths ...')
        self._update_artella_paths()
        self._set_splash_text('Closing Artella App instances ...')
        # For now we do not check if Artella was closed or not
        self._close_all_artella_app_processes()
        self._set_splash_text('Launching Artella App ...')
        self._launch_artella_app()

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
        except Exception as exc:
            raise Exception(exc)

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
        except Exception as exc:
            raise Exception(exc)

    def _get_artella_data_folder(self):
        """
        Returns last version Artella folder installation
        :return: str
        """

        if platform.system() == 'Darwin':
            artella_folder = os.path.join(os.path.expanduser('~/Library/Application Support/'), 'Artella')
        elif platform.system() == 'Windows':
            artella_folder = os.path.join(os.getenv('PROGRAMDATA'), 'Artella')
        else:
            return None

        artella_app_version = None
        version_file = os.path.join(artella_folder, ARTELLA_NEXT_VERSION_FILE_NAME)
        if os.path.isfile(version_file):
            with open(version_file) as f:
                artella_app_version = f.readline()

        if artella_app_version is not None:
            artella_folder = os.path.join(artella_folder, artella_app_version)
        else:
            artella_folder = [
                os.path.join(artella_folder, name) for name in os.listdir(artella_folder) if os.path.isdir(
                    os.path.join(artella_folder, name)) and name != 'ui']
            if len(artella_folder) == 1:
                artella_folder = artella_folder[0]
            else:
                LOGGER.info('Artella folder not found!')

        LOGGER.debug('ARTELLA FOLDER: {}'.format(artella_folder))
        if not os.path.exists(artella_folder):
            QMessageBox.information(
                self._splash,
                'Artella Folder not found!',
                'Artella App Folder {} does not exists! Make sure that Artella is installed in your computer!')

        return artella_folder

    def _update_artella_paths(self):
        """
        Updates system path to add artella paths if they are not already added
        :return:
        """

        artella_folder = self._get_artella_data_folder()

        LOGGER.debug('Updating Artella paths from: {0}'.format(artella_folder))
        if artella_folder is not None and os.path.exists(artella_folder):
            for subdir, dirs, files in os.walk(artella_folder):
                if subdir not in sys.path:
                    LOGGER.debug('Adding Artella path: {0}'.format(subdir))
                    sys.path.append(subdir)

    def _close_all_artella_app_processes(self):
        """
        Closes all Artella app (lifecycler.exe) processes
        :return:
        """

        # TODO: This only works with Windows and has a dependency on psutil library
        # TODO: Find a cross-platform way of doing this

        psutil_available = True
        try:
            import psutil
        except ImportError:
            psutil_available = False

        if not psutil_available:
            LOGGER.warning('Impossible to close Artella app instance because psutil is not available!')
            return

        try:
            for proc in psutil.process_iter():
                if proc.name() == '{}.exe'.format(ARTELLA_APP_NAME):
                    LOGGER.debug('Killing Artella App process: {}'.format(proc.name()))
                    proc.kill()
            return True
        except RuntimeError:
            LOGGER.error('Impossible to close Artella app instances because psutil library is not available!')
            return False

    def _get_artella_app(self):
        """
        Returns path where Artella path is installed
        :return: str
        """

        artella_folder = os.path.dirname(self._get_artella_data_folder())
        return os.path.join(artella_folder, ARTELLA_APP_NAME)

    def _get_artella_program_folder(self):
        """
        Returns folder where Artella shortcuts are located
        :return: str
        """

        # TODO: This only works on Windows, find a cross-platform way of doing this

        return os.path.join(os.environ['PROGRAMDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Artella')

    def _get_artella_launch_shortcut(self):
        """
        Returns path where Launch Artella shortcut is located
        :return: str
        """

        # TODO: This only works on Windows, find a cross-platform way of doing this

        return os.path.join(self._get_artella_program_folder(), 'Launch Artella.lnk')

    def _launch_artella_app(self):
        """
        Executes Artella App
        """

        # TODO: This should not work in MAC, find a cross-platform way of doing this

        if os.name == 'mac':
            LOGGER.info('Launch Artella App: does not supports MAC yet')
            QMessageBox.information(
                None,
                'Not supported in MAC',
                'Artella Pipeline do not support automatically Artella Launch for Mac. '
                'Please close Maya, launch Artella manually, and start Maya again!')
            artella_app_file = self._get_artella_app() + '.bundle'
        else:
            #  Executing Artella executable directly does not work
            # artella_app_file = get_artella_app() + '.exe'
            artella_app_file = self._get_artella_launch_shortcut()

        artella_app_file = artella_app_file
        LOGGER.info('Artella App File: {0}'.format(artella_app_file))

        if os.path.isfile(artella_app_file):
            LOGGER.info('Launching Artella App ...')
            LOGGER.debug('Artella App File: {0}'.format(artella_app_file))
            os.startfile(artella_app_file.replace('\\', '//'))


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

    parser = argparse.ArgumentParser()
    parser.add_argument('--project-name', required=False)
    parser.add_argument('--version', required=False)
    parser.add_argument('--repository', required=False)
    parser.add_argument('--environment', default='production')
    parser.add_argument('--icon-path', required=False, default=None)
    parser.add_argument('--splash-path', required=False, default=None)
    parser.add_argument('--script-path', required=False, default=None)
    parser.add_argument('--dev', required=False, default=False, action='store_true')
    args = parser.parse_args()

    with application() as app:

        if args.icon_path:
            app.setWindowIcon(QIcon(args.icon_path))

        new_app = None
        valid_app = False
        try:
            new_app = ArtellaUpdater(
                project_name=args.project_name,
                app_version=args.version,
                deployment_repository=args.repository,
                environment=args.environment,
                splash_path=args.splash_path,
                script_path=args.script_path,
                dev=args.dev
            )
            valid_app = True
        except Exception as exc:
            raise ArtellaUpdaterException(exc)
