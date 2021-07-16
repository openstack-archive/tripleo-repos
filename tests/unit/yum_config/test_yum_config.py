#   Copyright 2021 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import configparser
import copy
import ddt
import os
from unittest import mock

from . import fakes
from . import test_main
import tripleo_repos.yum_config.constants as const
import tripleo_repos.yum_config.exceptions as exc
import tripleo_repos.yum_config.yum_config as yum_cfg


@ddt.ddt
class TestTripleOYumConfig(test_main.TestTripleoYumConfigBase):
    """Tests for TripleYumConfig class and its methods."""

    def _create_yum_config_obj(self, file_path=None, dir_path=None,
                               valid_options=None, file_extension=None):
        self.mock_object(os.path, 'isfile')
        self.mock_object(os, 'access')
        self.mock_object(os.path, 'isdir')
        return yum_cfg.TripleOYumConfig(file_path=file_path, dir_path=dir_path,
                                        valid_options=valid_options,
                                        file_extension=file_extension)

    @ddt.data(
        {'file_path': None, 'dir_path': None, 'is_file_ret': None,
         'access_ret': None, 'is_dir_ret': None,
         'exception': exc.TripleOYumConfigNotFound},

        {'file_path': 'fake_path', 'dir_path': None, 'is_file_ret': False,
         'access_ret': None, 'is_dir_ret': None,
         'exception': exc.TripleOYumConfigNotFound},

        {'file_path': 'fake_path', 'dir_path': None, 'is_file_ret': True,
         'access_ret': False, 'is_dir_ret': None,
         'exception': exc.TripleOYumConfigPermissionDenied},

        {'file_path': None, 'dir_path': 'fake_dir', 'is_file_ret': None,
         'access_ret': None, 'is_dir_ret': False,
         'exception': exc.TripleOYumConfigNotFound},
    )
    @ddt.unpack
    def test_tripleo_yum_config_invalid_parameters(
            self, file_path, dir_path, is_file_ret, access_ret, is_dir_ret,
            exception):
        self.mock_object(os.path, 'isfile',
                         mock.Mock(return_value=is_file_ret))
        self.mock_object(os, 'access',
                         mock.Mock(return_value=access_ret))
        self.mock_object(os.path, 'isdir',
                         mock.Mock(return_value=is_dir_ret))

        self.assertRaises(exception,
                          yum_cfg.TripleOYumConfig,
                          file_path=file_path,
                          dir_path=dir_path)

    def test_read_config_file_path(self):
        yum_config = self._create_yum_config_obj(
            file_path=fakes.FAKE_FILE_PATH)

        parser_mock = mock.Mock()
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(return_value=parser_mock))
        read_mock = self.mock_object(parser_mock, 'read')
        self.mock_object(parser_mock, 'sections',
                         mock.Mock(return_value=fakes.FAKE_SECTIONS))

        config_parser, file_path = yum_config._read_config_file(
            fakes.FAKE_SECTION1
        )

        self.assertEqual(parser_mock, config_parser)
        self.assertEqual(fakes.FAKE_FILE_PATH, file_path)
        read_mock.assert_called_once_with(fakes.FAKE_FILE_PATH)

    def test_read_config_file_path_parse_error(self):
        yum_config = self._create_yum_config_obj(
            file_path=fakes.FAKE_FILE_PATH)

        parser_mock = mock.Mock()
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(return_value=parser_mock))
        read_mock = self.mock_object(parser_mock, 'read',
                                     mock.Mock(side_effect=configparser.Error))

        self.assertRaises(exc.TripleOYumConfigFileParseError,
                          yum_config._read_config_file,
                          fakes.FAKE_SECTION1)

        read_mock.assert_called_once_with(fakes.FAKE_FILE_PATH)

    def test_read_config_file_path_invalid_section(self):
        yum_config = self._create_yum_config_obj(
            file_path=fakes.FAKE_FILE_PATH)

        parser_mock = mock.Mock()
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(return_value=parser_mock))
        read_mock = self.mock_object(parser_mock, 'read')
        self.mock_object(parser_mock, 'sections',
                         mock.Mock(return_value=fakes.FAKE_SECTIONS))

        self.assertRaises(exc.TripleOYumConfigInvalidSection,
                          yum_config._read_config_file,
                          'invalid_section')

        read_mock.assert_called_once_with(fakes.FAKE_FILE_PATH)

    def test_read_config_file_dir(self):
        yum_config = self._create_yum_config_obj(
            dir_path=fakes.FAKE_DIR_PATH,
            file_extension='.conf')
        parser_mocks = []
        for i in range(3):
            parser_mock = mock.Mock()
            parser_mocks.append(parser_mock)
            self.mock_object(parser_mock, 'read')

        self.mock_object(parser_mocks[1], 'sections',
                         mock.Mock(return_value=[]))
        # second file inside dir will have the expected sections
        self.mock_object(parser_mocks[2], 'sections',
                         mock.Mock(return_value=fakes.FAKE_SECTIONS))
        self.mock_object(os, 'listdir',
                         mock.Mock(return_value=fakes.FAKE_DIR_FILES))
        self.mock_object(os, 'access', mock.Mock(return_value=True))
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(side_effect=parser_mocks))

        config_parser, file_path = yum_config._read_config_file(
            fakes.FAKE_SECTION1)
        expected_dir_path = os.path.join(fakes.FAKE_DIR_PATH,
                                         fakes.FAKE_DIR_FILES[1])

        self.assertEqual(parser_mocks[0], config_parser)
        self.assertEqual(expected_dir_path, file_path)

    def test_read_config_file_dir_section_not_found(self):
        yum_config = self._create_yum_config_obj(
            dir_path=fakes.FAKE_DIR_PATH,
            file_extension='.conf')
        parser_mock = mock.Mock()
        self.mock_object(parser_mock, 'read')
        self.mock_object(parser_mock, 'sections',
                         mock.Mock(return_value=[]))
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(return_value=parser_mock))

        self.mock_object(os, 'listdir',
                         mock.Mock(return_value=fakes.FAKE_DIR_FILES))
        self.mock_object(os, 'access', mock.Mock(return_value=True))

        config_parser, file_path = yum_config._read_config_file(
            fakes.FAKE_SECTION1)

        self.assertEqual(parser_mock, config_parser)
        self.assertIsNone(file_path)

    @mock.patch('builtins.open')
    def test_update_section(self, open):
        yum_config = self._create_yum_config_obj(
            file_path=fakes.FAKE_FILE_PATH,
            valid_options=fakes.FAKE_SUPP_OPTIONS)
        config_parser = fakes.FakeConfigParser({fakes.FAKE_SECTION1: {}})

        mock_read_config = self.mock_object(
            yum_config, '_read_config_file',
            mock.Mock(return_value=(config_parser, fakes.FAKE_FILE_PATH)))

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}

        yum_config.update_section(fakes.FAKE_SECTION1, updates)

        mock_read_config.assert_called_once_with(fakes.FAKE_SECTION1)

    def test_update_section_invalid_options(self):
        yum_config = self._create_yum_config_obj(
            file_path=fakes.FAKE_FILE_PATH,
            valid_options=fakes.FAKE_SUPP_OPTIONS)

        updates = {'invalid_option': 'new_fake_value'}

        self.assertRaises(exc.TripleOYumConfigInvalidOption,
                          yum_config.update_section,
                          fakes.FAKE_SECTION1,
                          updates)

    def test_update_section_file_not_found(self):
        yum_config = self._create_yum_config_obj(
            file_path=fakes.FAKE_FILE_PATH,
            valid_options=fakes.FAKE_SUPP_OPTIONS)
        mock_read_config = self.mock_object(
            yum_config, '_read_config_file',
            mock.Mock(return_value=(mock.Mock(), None)))

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}

        self.assertRaises(exc.TripleOYumConfigNotFound,
                          yum_config.update_section,
                          fakes.FAKE_SECTION1,
                          updates)

        mock_read_config.assert_called_once_with(fakes.FAKE_SECTION1)


@ddt.ddt
class TestTripleOYumRepoConfig(test_main.TestTripleoYumConfigBase):
    """Tests for TripleOYumRepoConfig class and its methods."""

    @ddt.data(True, False, None)
    def test_yum_repo_config_update_section(self, enable):
        self.mock_object(os.path, 'isfile')
        self.mock_object(os, 'access')
        self.mock_object(os.path, 'isdir')
        cfg_obj = yum_cfg.TripleOYumRepoConfig(
            file_path=fakes.FAKE_FILE_PATH)

        mock_update = self.mock_object(yum_cfg.TripleOYumConfig,
                                       'update_section')

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}
        expected_updates = copy.copy(updates)
        if enable is not None:
            expected_updates['enabled'] = '1' if enable else '0'

        cfg_obj.update_section(fakes.FAKE_SECTION1, updates, enable=enable)

        mock_update.assert_called_once_with(fakes.FAKE_SECTION1,
                                            expected_updates)


@ddt.ddt
class TestTripleOYumGlobalConfig(test_main.TestTripleoYumConfigBase):
    """Tests for TripleOYumGlobalConfig class and its methods."""

    @mock.patch('builtins.open')
    def test_create_yum_global_config_create_yum_conf(self, open):
        self.mock_object(os, 'access')
        self.mock_object(os.path, 'isdir')
        self.mock_object(os.path, 'isfile',
                         mock.Mock(side_effect=[False, True]))

        fake_cfg_parser = mock.Mock()
        mock_read = self.mock_object(fake_cfg_parser, 'read')
        mock_add = self.mock_object(fake_cfg_parser, 'add_section')
        mock_write = self.mock_object(fake_cfg_parser, 'write')
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(return_value=fake_cfg_parser))

        cfg_obj = yum_cfg.TripleOYumGlobalConfig()

        self.assertIsNotNone(cfg_obj)
        mock_read.assert_called_once_with(const.YUM_GLOBAL_CONFIG_FILE_PATH)
        mock_add.assert_called_once_with('main')
        mock_write.assert_called_once()
