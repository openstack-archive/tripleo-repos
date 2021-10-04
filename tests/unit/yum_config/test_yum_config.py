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
import subprocess
from unittest import mock

from . import fakes
from . import test_main
import tripleo_repos.yum_config.constants as const
import tripleo_repos.yum_config.exceptions as exc
import tripleo_repos.yum_config.yum_config as yum_cfg


@ddt.ddt
class TestTripleOYumConfig(test_main.TestTripleoYumConfigBase):
    """Tests for TripleYumConfig class and its methods."""

    def _create_yum_config_obj(self, dir_path=None, valid_options=None,
                               file_extension=None):
        self.mock_object(os.path, 'isfile')
        self.mock_object(os, 'access')
        self.mock_object(os.path, 'isdir')
        return yum_cfg.TripleOYumConfig(dir_path=dir_path,
                                        valid_options=valid_options,
                                        file_extension=file_extension)

    def test_tripleo_yum_config_invalid_dir_path(self):
        self.mock_object(os.path, 'isdir',
                         mock.Mock(return_value=False))

        self.assertRaises(exc.TripleOYumConfigNotFound,
                          yum_cfg.TripleOYumConfig,
                          dir_path='fake_dir_path')

    def test_read_config_file_path(self):
        yum_config = self._create_yum_config_obj()

        parser_mock = mock.Mock()
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(return_value=parser_mock))
        read_mock = self.mock_object(parser_mock, 'read')
        self.mock_object(parser_mock, 'sections',
                         mock.Mock(return_value=fakes.FAKE_SECTIONS))

        config_parser, file_path = yum_config._read_config_file(
            fakes.FAKE_FILE_PATH,
            section=fakes.FAKE_SECTION1
        )

        self.assertEqual(parser_mock, config_parser)
        self.assertEqual(fakes.FAKE_FILE_PATH, file_path)
        read_mock.assert_called_once_with(fakes.FAKE_FILE_PATH)

    def test_read_config_file_path_parse_error(self):
        yum_config = self._create_yum_config_obj()

        parser_mock = mock.Mock()
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(return_value=parser_mock))
        read_mock = self.mock_object(parser_mock, 'read',
                                     mock.Mock(side_effect=configparser.Error))

        self.assertRaises(exc.TripleOYumConfigFileParseError,
                          yum_config._read_config_file,
                          fakes.FAKE_FILE_PATH,
                          section=fakes.FAKE_SECTION1)

        read_mock.assert_called_once_with(fakes.FAKE_FILE_PATH)

    def test_read_config_file_path_invalid_section(self):
        yum_config = self._create_yum_config_obj()

        parser_mock = mock.Mock()
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(return_value=parser_mock))
        read_mock = self.mock_object(parser_mock, 'read')
        self.mock_object(parser_mock, 'sections',
                         mock.Mock(return_value=fakes.FAKE_SECTIONS))

        self.assertRaises(exc.TripleOYumConfigInvalidSection,
                          yum_config._read_config_file,
                          fakes.FAKE_FILE_PATH,
                          section='invalid_section')

        read_mock.assert_called_once_with(fakes.FAKE_FILE_PATH)

    def test_get_config_files(self):
        yum_config = self._create_yum_config_obj(
            dir_path=fakes.FAKE_DIR_PATH,
            file_extension='.conf')
        parser_mocks = []
        for i in range(3):
            parser_mock = mock.Mock()
            parser_mocks.append(parser_mock)
            self.mock_object(parser_mock, 'read')

        self.mock_object(parser_mocks[0], 'sections',
                         mock.Mock(return_value=[]))
        # second file inside dir will have the expected sections
        self.mock_object(parser_mocks[1], 'sections',
                         mock.Mock(return_value=fakes.FAKE_SECTIONS))
        self.mock_object(parser_mocks[2], 'sections',
                         mock.Mock(return_value=[]))
        self.mock_object(os, 'listdir',
                         mock.Mock(return_value=fakes.FAKE_DIR_FILES))
        self.mock_object(os, 'access', mock.Mock(return_value=True))
        self.mock_object(configparser, 'ConfigParser',
                         mock.Mock(side_effect=parser_mocks))

        result = yum_config._get_config_files(fakes.FAKE_SECTION1)
        expected_dir_path = [os.path.join(fakes.FAKE_DIR_PATH,
                                          fakes.FAKE_DIR_FILES[1])]

        self.assertEqual(expected_dir_path, result)

    @mock.patch('builtins.open')
    def test_update_section(self, open):
        yum_config = self._create_yum_config_obj(
            valid_options=fakes.FAKE_SUPP_OPTIONS)
        config_parser = fakes.FakeConfigParser({fakes.FAKE_SECTION1: {}})

        mock_read_config = self.mock_object(
            yum_config, '_read_config_file',
            mock.Mock(return_value=(config_parser, fakes.FAKE_FILE_PATH)))

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}

        yum_config.update_section(fakes.FAKE_SECTION1, updates,
                                  file_path=fakes.FAKE_FILE_PATH)

        mock_read_config.assert_called_once_with(fakes.FAKE_FILE_PATH,
                                                 section=fakes.FAKE_SECTION1)

    def test_update_section_invalid_options(self):
        yum_config = self._create_yum_config_obj(
            valid_options=fakes.FAKE_SUPP_OPTIONS)

        updates = {'invalid_option': 'new_fake_value'}

        self.assertRaises(exc.TripleOYumConfigInvalidOption,
                          yum_config.update_section,
                          fakes.FAKE_SECTION1,
                          updates,
                          file_path=fakes.FAKE_FILE_PATH)

    def test_update_section_file_not_found(self):
        yum_config = self._create_yum_config_obj(
            valid_options=fakes.FAKE_SUPP_OPTIONS)
        mock_get_configs = self.mock_object(
            yum_config, '_get_config_files',
            mock.Mock(return_value=[]))

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}

        self.assertRaises(exc.TripleOYumConfigNotFound,
                          yum_config.update_section,
                          fakes.FAKE_SECTION1,
                          updates)
        mock_get_configs.assert_called_once_with(fakes.FAKE_SECTION1)

    @mock.patch('builtins.open')
    def test_add_section(self, open):
        yum_config = self._create_yum_config_obj(
            valid_options=fakes.FAKE_SUPP_OPTIONS)
        config_parser = fakes.FakeConfigParser({fakes.FAKE_SECTION1: {}})

        mock_read_config = self.mock_object(
            yum_config, '_read_config_file',
            mock.Mock(return_value=(config_parser, fakes.FAKE_FILE_PATH)))

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}

        yum_config.add_section(fakes.FAKE_SECTION2, updates,
                               file_path=fakes.FAKE_FILE_PATH)

        mock_read_config.assert_called_once_with(
            file_path=fakes.FAKE_FILE_PATH)

    @mock.patch('builtins.open')
    def test_add_section_already_exists(self, open):
        yum_config = self._create_yum_config_obj(
            valid_options=fakes.FAKE_SUPP_OPTIONS)
        config_parser = fakes.FakeConfigParser({fakes.FAKE_SECTION1: {}})

        mock_read_config = self.mock_object(
            yum_config, '_read_config_file',
            mock.Mock(return_value=(config_parser, fakes.FAKE_FILE_PATH)))

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}

        self.assertRaises(exc.TripleOYumConfigInvalidSection,
                          yum_config.add_section,
                          fakes.FAKE_SECTION1, updates,
                          file_path=fakes.FAKE_FILE_PATH)

        mock_read_config.assert_called_once_with(
            file_path=fakes.FAKE_FILE_PATH)

    @mock.patch('builtins.open')
    def test_add_update_all_sections(self, open):
        yum_config = self._create_yum_config_obj(
            valid_options=fakes.FAKE_SUPP_OPTIONS)
        config_parser = fakes.FakeConfigParser({fakes.FAKE_SECTION1: {}})

        mock_read_config = self.mock_object(
            yum_config, '_read_config_file',
            mock.Mock(return_value=(config_parser, fakes.FAKE_FILE_PATH)))

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}

        yum_config.update_all_sections(updates, fakes.FAKE_FILE_PATH)

        mock_read_config.assert_called_once_with(fakes.FAKE_FILE_PATH)

    def test_source_env_file(self):
        p_open_mock = mock.Mock()
        mock_open = self.mock_object(subprocess, 'Popen',
                                     mock.Mock(return_value=p_open_mock))
        data_mock = mock.Mock()
        self.mock_object(data_mock, 'decode',
                         mock.Mock(return_value=fakes.FAKE_ENV_OUTPUT))
        self.mock_object(p_open_mock, 'communicate',
                         mock.Mock(return_value=[data_mock]))
        env_update_mock = self.mock_object(os.environ, 'update')

        yum_cfg.source_env_file('fake_source_file', update=True)

        exp_env_dict = dict(
            line.split("=", 1) for line in fakes.FAKE_ENV_OUTPUT.splitlines()
            if len(line.split("=", 1)) > 1)

        mock_open.assert_called_once_with(". fake_source_file; env",
                                          stdout=subprocess.PIPE,
                                          shell=True)
        env_update_mock.assert_called_once_with(exp_env_dict)


@ddt.ddt
class TestTripleOYumRepoConfig(test_main.TestTripleoYumConfigBase):
    """Tests for TripleOYumRepoConfig class and its methods."""

    def setUp(self):
        super(TestTripleOYumRepoConfig, self).setUp()
        self.config_obj = yum_cfg.TripleOYumRepoConfig(
            dir_path='/tmp'
        )

    @ddt.data(True, False, None)
    def test_yum_repo_config_update_section(self, enable):
        self.mock_object(os.path, 'isfile')
        self.mock_object(os, 'access')
        self.mock_object(os.path, 'isdir')

        mock_update = self.mock_object(yum_cfg.TripleOYumConfig,
                                       'update_section')

        updates = {fakes.FAKE_OPTION1: 'new_fake_value'}
        expected_updates = copy.copy(updates)
        if enable is not None:
            expected_updates['enabled'] = '1' if enable else '0'

        self.config_obj.update_section(
            fakes.FAKE_SECTION1, set_dict=updates,
            file_path=fakes.FAKE_FILE_PATH, enabled=enable)

        mock_update.assert_called_once_with(fakes.FAKE_SECTION1,
                                            expected_updates,
                                            file_path=fakes.FAKE_FILE_PATH)

    @mock.patch('builtins.open')
    def test_add_or_update_section(self, open):
        mock_update = self.mock_object(
            self.config_obj, 'update_section',
            mock.Mock(side_effect=exc.TripleOYumConfigNotFound(
                error_msg='error')))
        mock_add_section = self.mock_object(self.config_obj, 'add_section')

        self.config_obj.add_or_update_section(
            fakes.FAKE_SECTION1,
            set_dict=fakes.FAKE_SET_DICT,
            file_path=fakes.FAKE_FILE_PATH,
            enabled=True,
            create_if_not_exists=True)

        mock_update.assert_called_once_with(fakes.FAKE_SECTION1,
                                            set_dict=fakes.FAKE_SET_DICT,
                                            file_path=fakes.FAKE_FILE_PATH,
                                            enabled=True)
        fake_set_dict = copy.deepcopy(fakes.FAKE_SET_DICT)
        fake_set_dict['name'] = fakes.FAKE_SECTION1
        mock_add_section.assert_called_once_with(
            fakes.FAKE_SECTION1,
            fake_set_dict,
            fakes.FAKE_FILE_PATH,
            enabled=True)

    @ddt.data((fakes.FAKE_FILE_PATH, False), (None, True))
    @ddt.unpack
    def test_add_or_update_section_file_not_found(self, fake_path,
                                                  create_if_not_exists):
        mock_update = self.mock_object(
            self.config_obj, 'update_section',
            mock.Mock(side_effect=exc.TripleOYumConfigNotFound(
                error_msg='error')))

        self.assertRaises(
            exc.TripleOYumConfigNotFound,
            self.config_obj.add_or_update_section,
            fakes.FAKE_SECTION1,
            set_dict=fakes.FAKE_SET_DICT,
            file_path=fake_path,
            enabled=True,
            create_if_not_exists=create_if_not_exists)

        mock_update.assert_called_once_with(fakes.FAKE_SECTION1,
                                            set_dict=fakes.FAKE_SET_DICT,
                                            file_path=fake_path,
                                            enabled=True)

    @ddt.data(None, False, True)
    def test_add_section(self, enabled):
        mock_add = self.mock_object(yum_cfg.TripleOYumConfig, 'add_section')

        self.config_obj.add_section(
            fakes.FAKE_SECTION1, fakes.FAKE_SET_DICT,
            fakes.FAKE_FILE_PATH, enabled=enabled)

        updated_dict = copy.deepcopy(fakes.FAKE_SET_DICT)
        if enabled is not None:
            updated_dict['enabled'] = '1' if enabled else '0'
        mock_add.assert_called_once_with(fakes.FAKE_SECTION1, updated_dict,
                                         fakes.FAKE_FILE_PATH)


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
