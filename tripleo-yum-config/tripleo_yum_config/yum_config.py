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

import configparser
import logging
import os
import sys

import tripleo_yum_config.constants as const
import tripleo_yum_config.exceptions as exc


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

    def __init__(self, valid_options=None, file_path=None, dir_path=None,
                 file_extension=None):
        """
        Creates a TripleOYumConfig object that holds configuration file
        information.

        :param valid_options: A list of options that can be updated on this
            file.
        :param file_path: The file path to configuration file to be updated.
        :param dir_path: The directory path that this class can use to search
            for configuration files to be updated.
        :param: file_extension: File extension to filter configuration files
            in the search directory.
        """
        self.config_file_path = file_path
        self.dir_path = dir_path
        self.file_extension = file_extension
        self.valid_options = valid_options

        # Sanity checks
        if not (file_path or dir_path):
            msg = ('A configuration file path or a directory path must be '
                   'provided.')
            raise exc.TripleOYumConfigNotFound(error_msg=msg)

        if file_path:
            if not os.path.isfile(file_path):
                msg = ('The configuration file "{}" was not found in the '
                       'provided path.').format(file_path)
                raise exc.TripleOYumConfigNotFound(error_msg=msg)
            if not os.access(file_path, os.W_OK):
                msg = ('The configuration file {} is not '
                       'writable.'.format(file_path))
                raise exc.TripleOYumConfigPermissionDenied(error_msg=msg)

        if dir_path:
            if not os.path.isdir(dir_path):
                msg = ('The configuration dir "{}" was not found in the '
                       'provided path.').format(dir_path)
                raise exc.TripleOYumConfigNotFound(error_msg=msg)

    def _read_config_file(self, section):
        """Read the configuration file associate with this object.

        If no configuration file is provided, this method will search for
        'section' name in all files inside the configuration directory. The
        first occurrence of 'section' will be returned, and a warning will be
        logged if more than one configuration file has the same 'section' set.

        :param section: The name of the section to be updated.
        :return: a config parser object and the file path.
        """
        config = configparser.ConfigParser()
        # A) A configuration file path was provided.
        if self.config_file_path:
            try:
                config.read(self.config_file_path)
            except configparser.Error:
                msg = 'Unable to parse configuration file {}.'.format(
                    self.config_file_path)
                raise exc.TripleOYumConfigFileParseError(error_msg=msg)

            if section not in config.sections():
                msg = ('The provided section "{}" was not found in the '
                       'configuration file {}.').format(
                    section, self.config_file_path)
                raise exc.TripleOYumConfigInvalidSection(error_msg=msg)

            return config, self.config_file_path

        # B) Search for a configuration file that has the provided section
        section_found = False
        config_file_path = None
        for file in os.listdir(self.dir_path):
            # Skip files that don't match the file extension or are not
            # writable
            if self.file_extension and not file.endswith(
                    self.file_extension):
                continue
            if not os.access(os.path.join(self.dir_path, file), os.W_OK):
                continue

            tmp_config = configparser.ConfigParser()
            try:
                tmp_config.read(os.path.join(self.dir_path, file))
            except configparser.Error:
                continue
            if section in tmp_config.sections():
                if section_found:
                    logging.warning('Section "{}" is listed more than once in '
                                    'configuration files.'.format(section))
                else:
                    # Read the first occurrence of 'section'
                    config_file_path = os.path.join(self.dir_path, file)
                    config.read(config_file_path)
                    section_found = True

        return config, config_file_path

    def update_section(self, section, set_dict):
        """Updates a set of options for a specified section.

        :param section: Name of the section on the configuration file that will
            be updated.
        :param set_dict: Dict with all options and values to be updated in the
            configuration file section.
        """
        if self.valid_options:
            if not all(key in self.valid_options for key in set_dict.keys()):
                msg = 'One or more provided options are not valid.'
                raise exc.TripleOYumConfigInvalidOption(error_msg=msg)

        config, config_file_path = self._read_config_file(section)
        if not (config and config_file_path):
            msg = ('The provided section "{}" was not found within any '
                   'configuration file.').format(section)
            raise exc.TripleOYumConfigNotFound(error_msg=msg)

        # Update configuration file with dict updates
        config[section].update(set_dict)

        with open(config_file_path, 'w') as file:
            config.write(file)

        logging.info("Section '{}' was successfully updated.".format(section))


class TripleOYumRepoConfig(TripleOYumConfig):
    """Manages yum repo configuration files."""

    def __init__(self, file_path=None, dir_path=None):
        if file_path:
            logging.info(
                "Using '{}' as yum repo configuration file.".format(file_path))
        conf_dir_path = dir_path or const.YUM_REPO_DIR

        super(TripleOYumRepoConfig, self).__init__(
            valid_options=const.YUM_REPO_SUPPORTED_OPTIONS,
            file_path=file_path,
            dir_path=conf_dir_path,
            file_extension=const.YUM_REPO_FILE_EXTENSION)

    def update_section(self, section, set_dict, enable=None):
        if enable is not None:
            set_dict['enabled'] = '1' if enable else '0'

        super(TripleOYumRepoConfig, self).update_section(section, set_dict)


class TripleOYumGlobalConfig(TripleOYumConfig):
    """Manages yum global configuration file."""

    def __init__(self, file_path=None):
        conf_file_path = file_path or const.YUM_GLOBAL_CONFIG_FILE_PATH
        logging.info("Using '{}' as yum global configuration "
                     "file.".format(conf_file_path))
        if file_path is None:
            # If there is no default 'yum.conf' configuration file, we need to
            # create it. If the user specify another conf file that doesn't
            # exists, the operation will fail.
            if not os.path.isfile(conf_file_path):
                config = configparser.ConfigParser()
                config.read(conf_file_path)
                config.add_section('main')
                with open(conf_file_path, '+w') as file:
                    config.write(file)

        super(TripleOYumGlobalConfig, self).__init__(file_path=conf_file_path)
