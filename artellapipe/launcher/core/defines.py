#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains all constant definitions used by artellapipe library
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"


# Defines environment variable name that can setup to define folder where configuration files are located
ARTELLA_LAUNCHER_CONFIGURATION_DEV = 'ARTELLA_LAUNCHER_CONFIGURATIONS_FOLDER'

# Defines the name of the configuration file used by Artella Launcher
ARTELLA_LAUNCHER_CONFIG_FILE_NAME = 'launcher.json'

# Defines the name of the configure file used by Artella Updater
ARTELLA_UPDATER_CONFIG_FILE_NAME = 'updater.json'

# Defines the name of the attribute that defines the Artella launcher name
ARTELLA_CONFIG_LAUNCHER_NAME = 'name'

# Defines the name of the attribute that defines the Artella launcher version
ARTELLA_CONFIG_LAUNCHER_VERSION = 'version'

# Defines the name of the attribute that defines the Artella Plugins section
ARTELLA_CONFIG_LAUNCHER_PLUGINS = 'plugins'

# Defines the name of the attribute that defines the Artella updater version
ARTELLA_CONFIG_UPDATER_VERSION = 'UPDATER_VERSION'

# Defines the name of the attribute that defines environment variables that updater should used
UPDATER_TOOLS_ENVIRONMENT_VARIABLE_ATTRIBUTE_NAME = "TOOLS_ENVIRONMENT_VARIABLE"

# Defines the name of the attribute that defines release package extension
UPDATER_RELEASE_EXTENSION = "RELEASE_EXTENSION"

# Defines the name of the attribute that defines URL used by updater
UPDATER_REPOSITORY_URL_ATTRIBUTE_NAME = "REPOSITORY_URL"

# Defines the name of the attribute that defines folder where tools folder is located inside repository
UPDATER_REPOSITORY_FOLDER_ATTRIBUTE_NAME = "REPOSITORY_FOLDER"

# Defines the name of the attribute that defines the name of the updater publish version file
UPDATER_LAST_VERSION_FILE_NAME = "LAST_VERSION_FILE_NAME"

# Defines the name of the attribute that defines the name of the version file used by tools
UPDATER_VERSION_FILE_NAME = "VERSION_FILE_NAME"

# Defines the mae of the attributes that defines the first gradient color of the progress bar
UPDATER_PROGRESS_BAR_COLOR_0_ATTRIBUTE_NAME = "PROGRESS_BAR_COLOR_0"

# Defines the mae of the attributes that defines the second gradient color of the progress bar
UPDATER_PROGRESS_BAR_COLOR_1_ATTRIBUTE_NAME = "PROGRESS_BAR_COLOR_1"

# Defines the name of the attribute used to set if DCC icon (theme/name)
LAUNCHER_DCC_ICON_ATTRIBUTE_NAME = 'icon'

# Defines the name of the attribute used to set if DCC should be enabled or not
LAUNCHER_DCC_ENABLED_ATTRIBUTE_NAME = 'enabled'

# Defines the name of the attribute used to define the supported DCC versions
LAUNCHER_DCC_SUPPORTED_VERSIONS_ATTRIBUTE_NAME = 'supported_versions'

# Defines the name of the attribute used to set the default DCC version
LAUNCHER_DCC_DEFAULT_VERSION_ATTRIBUTE_NAME = 'default_version'

# Defines the name of the attribute used to set the departments that will use the DCC
LAUNCHER_DCC_DEPARTMENTS_ATTRIBUTE_NAME = 'departments'

# Defines the name of the attribute used to set the plugins names used by a specific DCC
LAUNCHER_DCC_PLUGINS_ATTRIBUTE_NAME = 'plugins'

# Defines the default name used by Artella launcher
ARTELLA_DEFAULT_LAUNCHER_NAME = 'Artella'

# Defines the default version used by Artella launcher/updater
DEFAULT_VERSION = '0.0.0'

# Defines the default value of the first color of the progress bar
DEFAULT_PROGRESS_BAR_COLOR_0 = '255, 255, 255'

# Defines the default value of the second color of the progress bar
DEFAULT_PROGRESS_BAR_COLOR_1 = '255, 255, 255'
