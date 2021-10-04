#  Copyright 2021 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
#
from __future__ import (absolute_import, division, print_function)


import logging
import os
import subprocess
import sys

from .constants import (
    YUM_GLOBAL_CONFIG_FILE_PATH,
    YUM_REPO_DIR,
    YUM_REPO_FILE_EXTENSION,
    YUM_REPO_SUPPORTED_OPTIONS,
)
from .exceptions import (
    TripleOYumConfigFileParseError,
    TripleOYumConfigInvalidOption,
    TripleOYumConfigInvalidSection,
    TripleOYumConfigNotFound,
)

py_version = sys.version_info.major
if py_version < 3:
    import ConfigParser as cfg_parser

    def save_section_to_file(file_path, config, section, updates):
        """Updates a specific 'section' in a 'config' and write to disk.

        :param file_path: Absolute path to the file to be updated.
        :param config: configparser object created from the file.
        :param section: section name to be updated.
        :param updates: dict with options to update in section.
        """

        for k, v in updates.items():
            config.set(section, k, v)
        with open(file_path, 'w') as f:
            config.write(f)

        # NOTE(dviroel) Need to manually remove whitespaces around "=", to
        #  avoid legacy scripts failing on parsing ini files.
        with open(file_path, 'r+') as f:
            lines = f.readlines()
            # erase content before writing again
            f.truncate(0)
            f.seek(0)
            for line in lines:
                line = line.strip()
                if "=" in line:
                    option_kv = line.split("=", 1)
                    option_kv = list(map(str.strip, option_kv))
                    f.write("%s%s%s\n" % (option_kv[0], "=", option_kv[1]))
                else:
                    f.write(line + "\n")

else:
    import configparser as cfg_parser

    def save_section_to_file(file_path, config, section, updates):
        """Updates a specific 'section' in a 'config' and write to disk.

        :param file_path: Absolute path to the file to be updated.
        :param config: configparser object created from the file.
        :param section: section name to be updated.
        :param updates: dict with options to update in section.
        """
        config[section].update(updates)
        with open(file_path, 'w') as f:
            config.write(f, space_around_delimiters=False)

__metaclass__ = type


def validated_file_path(file_path):
    if os.path.isfile(file_path) and os.access(file_path, os.W_OK):
        return True
    return False


def source_env_file(source_file, update=True):
    """Source a file and get all environment variables in a dict format."""
    p_open = subprocess.Popen(". %s; env" % source_file,
                              stdout=subprocess.PIPE,
                              shell=True)
    data = p_open.communicate()[0].decode('ascii')

    env_dict = dict(
        line.split("=", 1) for line in data.splitlines()
        if len(line.split("=", 1)) > 1)
    if update:
        os.environ.update(env_dict)
    return env_dict


class TripleOYumConfig:
    """
    This class is a base class for updating yum configuration files in
    ini format. The class validates the if the configuration files exists and
    if it has the the permissions needed. A list of updatable options may be
    provided to the class constructor.
    """

    @classmethod
    def load_logging(cls):
        """
        This is a class method since we call it from the CLI entrypoint
        before any object is created. Default is to add logging.INFO level
        logging.
        """
        logger = logging.getLogger()
        # Only add logger once to avoid duplicated streams in tests
        if not logger.handlers:
            stdout_handlers = [
                _handler
                for _handler in logger.handlers
                if (hasattr(_handler, 'stream') and 'stdout'
                    in _handler.stream.name)
            ]
            if not stdout_handlers:
                formatter = logging.Formatter(
                    (
                        "%(asctime)s - tripleo-yum-config - %(levelname)s - "
                        "%(message)s"
                    )
                )
                handler = logging.StreamHandler(sys.stdout)
                handler.setFormatter(formatter)
                logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    def __init__(self, valid_options=None, dir_path=None, file_extension=None,
                 environment_file=None):
        """
        Creates a TripleOYumConfig object that holds configuration file
        information.

        :param valid_options: A list of options that can be updated on this
            file.
        :param dir_path: The directory path that this class can use to search
            for configuration files to be updated.
        :param: file_extension: File extension to filter configuration files
            in the search directory.
        :param environment_file: File to be read before updating environment
            variables.
        """
        self.dir_path = dir_path
        self.file_extension = file_extension
        self.valid_options = valid_options
        self.env_file = environment_file

        # Sanity checks
        if dir_path:
            if not os.path.isdir(dir_path):
                msg = ('The configuration dir "{0}" was not found in the '
                       'provided path.').format(dir_path)
                raise TripleOYumConfigNotFound(error_msg=msg)

        if self.env_file:
            source_env_file(os.path.expanduser(self.env_file), update=True)

    def _read_config_file(self, file_path, section=None):
        """Reads a configuration file.

        :param section: The name of the section that will be update. Only used
            to fail earlier if the section is not found.
        :return: a config parser object and the full file path.
        """
        config = cfg_parser.ConfigParser()
        file_paths = [file_path]
        if self.dir_path:
            # if dir_path is configured, we can search for filename there
            file_paths.append(os.path.join(self.dir_path, file_path))

        valid_file_path = None
        for file in file_paths:
            if validated_file_path(file):
                valid_file_path = file
                break
        if not valid_file_path:
            msg = ('The configuration file "{0}" was '
                   'not found.'.format(file_path))
            raise TripleOYumConfigNotFound(error_msg=msg)

        try:
            config.read(valid_file_path)
        except cfg_parser.Error:
            msg = 'Unable to parse configuration file {0}.'.format(
                valid_file_path)
            raise TripleOYumConfigFileParseError(error_msg=msg)

        if section and section not in config.sections():
            msg = ('The provided section "{0}" was not found in the '
                   'configuration file {1}.').format(
                section, valid_file_path)
            raise TripleOYumConfigInvalidSection(error_msg=msg)

        return config, valid_file_path

    def _get_config_files(self, section):
        """Gets all configuration file paths for a given section.

        This method will search for a 'section' name in all files inside the
        configuration directory. All files with 'section' will be returned.

        :param section: Section to be found inside configuration files.
        :return: A list of config file paths.
        """
        # Search for a configuration file that has the provided section
        config_files_path = []
        if section and self.dir_path:
            for file in os.listdir(self.dir_path):
                # Skip files that don't match the file extension or are not
                # writable
                if self.file_extension and not file.endswith(
                        self.file_extension):
                    continue
                if not os.access(os.path.join(self.dir_path, file), os.W_OK):
                    continue

                tmp_config = cfg_parser.ConfigParser()
                try:
                    tmp_config.read(os.path.join(self.dir_path, file))
                except cfg_parser.Error:
                    continue
                if section in tmp_config.sections():
                    config_files_path.append(os.path.join(self.dir_path, file))

        return config_files_path

    def update_section(self, section, set_dict, file_path=None):
        """Updates a set of options of a section.

        If a file path is not provided by the caller, this function will search
        for the section in all files located in the working directory and
        update each one of them.

        :param section: Name of the section on the configuration file that will
            be updated.
        :param set_dict: Dict with all options and values to be updated in the
            configuration file section.
        :param file_path: Path to the configuration file to be updated.
        """
        if self.valid_options:
            if not all(key in self.valid_options for key in set_dict.keys()):
                msg = 'One or more provided options are not valid.'
                raise TripleOYumConfigInvalidOption(error_msg=msg)

        files = [file_path] if file_path else self._get_config_files(section)
        if not files:
            msg = ('No configuration files were found for the provided '
                   'section {0}'.format(section))
            raise TripleOYumConfigNotFound(error_msg=msg)

        for k, v in set_dict.items():
            set_dict[k] = os.path.expandvars(v)
        for file in files:
            config, file = self._read_config_file(file, section=section)
            # Update configuration file with dict updates
            save_section_to_file(file, config, section, set_dict)

        logging.info("Section '%s' was successfully "
                     "updated.", section)

    def add_section(self, section, add_dict, file_path):
        """ Adds a new section with options in a provided config file.

        :param section: Section name to be added to the config file.
        :param add_dict: Dict with all options and values to be added into the
            new section.
        :param file_path: Path to the configuration file to be updated.
        """
        if self.valid_options:
            if not all(key in self.valid_options for key in add_dict.keys()):
                msg = 'One or more provided options are not valid.'
                raise TripleOYumConfigInvalidOption(error_msg=msg)

        # This section shouldn't exist in the provided file
        config, file_path = self._read_config_file(file_path=file_path)
        if section in config.sections():
            msg = ("Section '%s' already exists in the configuration "
                   "file.", section)
            raise TripleOYumConfigInvalidSection(error_msg=msg)

        for k, v in add_dict.items():
            add_dict[k] = os.path.expandvars(v)
        # Add new section
        config.add_section(section)
        # Update configuration file with dict updates
        save_section_to_file(file_path, config, section, add_dict)

        logging.info("Section '%s' was successfully "
                     "added.", section)

    def update_all_sections(self, set_dict, file_path):
        """Updates all section of a given configuration file.

        :param set_dict: Dict with all options and values to be updated in
            the configuration file.
        :param file_path: Path to the configuration file to be updated.
        """
        if self.valid_options:
            if not all(key in self.valid_options for key in set_dict.keys()):
                msg = 'One or more provided options are not valid.'
                raise TripleOYumConfigInvalidOption(error_msg=msg)

        config, file_path = self._read_config_file(file_path)
        for section in config.sections():
            save_section_to_file(file_path, config, section, set_dict)

        logging.info("All sections for '%s' were successfully "
                     "updated.", file_path)


class TripleOYumRepoConfig(TripleOYumConfig):
    """Manages yum repo configuration files."""

    def __init__(self, dir_path=None, environment_file=None):
        conf_dir_path = dir_path or YUM_REPO_DIR

        super(TripleOYumRepoConfig, self).__init__(
            valid_options=YUM_REPO_SUPPORTED_OPTIONS,
            dir_path=conf_dir_path,
            file_extension=YUM_REPO_FILE_EXTENSION,
            environment_file=environment_file)

    def update_section(
            self, section, set_dict=None, file_path=None, enabled=None):
        update_dict = set_dict or {}
        if enabled is not None:
            update_dict['enabled'] = '1' if enabled else '0'
        if update_dict:
            super(TripleOYumRepoConfig, self).update_section(
                section, update_dict, file_path=file_path)

    def add_section(self, section, add_dict, file_path, enabled=None):
        update_dict = add_dict or {}
        if enabled is not None:
            update_dict['enabled'] = '1' if enabled else '0'
        super(TripleOYumRepoConfig, self).add_section(
            section, update_dict, file_path)

    def add_or_update_section(self, section, set_dict=None, file_path=None,
                              enabled=None, create_if_not_exists=True):
        try:
            self.update_section(
                section, set_dict=set_dict, file_path=file_path,
                enabled=enabled)
        except TripleOYumConfigNotFound:
            if not create_if_not_exists or file_path is None:
                # there is nothing to do, we can't create a new config file
                raise
            # Create a new file if it does not exists
            with open(file_path, 'w+'):
                pass
            # When creating a new repo file, make sure that it has a name
            if 'name' not in set_dict.keys():
                set_dict['name'] = section
            self.add_section(section, set_dict, file_path, enabled=enabled)


class TripleOYumGlobalConfig(TripleOYumConfig):
    """Manages yum global configuration file."""

    def __init__(self, file_path=None, environment_file=None):
        self.conf_file_path = file_path or YUM_GLOBAL_CONFIG_FILE_PATH
        logging.info("Using '%s' as yum global configuration "
                     "file.", self.conf_file_path)
        if file_path is not None:
            # validate user provided file path
            validated_file_path(file_path)
        else:
            # If there is no default 'yum.conf' configuration file, we need to
            # create it. If the user specify another conf file that doesn't
            # exists, the operation will fail.
            if not os.path.isfile(self.conf_file_path):
                config = cfg_parser.ConfigParser()
                config.read(self.conf_file_path)
                config.add_section('main')
                with open(self.conf_file_path, 'w+') as file:
                    config.write(file)

        super(TripleOYumGlobalConfig, self).__init__(
            environment_file=environment_file)

    def update_section(self, section, set_dict, file_path=None):
        super(TripleOYumGlobalConfig, self).update_section(
            section, set_dict, file_path=(file_path or self.conf_file_path))

    def add_section(self, section, set_dict, file_path=None):
        add_file_path = file_path or self.conf_file_path
        super(TripleOYumGlobalConfig, self).add_section(
            section, set_dict, add_file_path)
